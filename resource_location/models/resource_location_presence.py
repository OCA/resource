# Copyright 2026 Daniel Reis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.intervals import Intervals


class ResourceLocationLine(models.Model):
    """Schedule-based presence of a resource at a location.

    The resource is present at ``location_id`` during the work
    intervals of ``calendar_id``. An empty calendar means the resource
    is permanently at that location. The first line (by sequence)
    covering a given instant wins.
    """

    _name = "resource.location.presence"
    _description = "Resource Location Presence"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        required=True,
        index=True,
        ondelete="cascade",
    )
    location_id = fields.Many2one(
        comodel_name="res.partner",
        string="Location",
        required=True,
        domain="[('is_resource_location', '=', True)]",
    )
    calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Presence Schedule",
        help="The resource is at this location during this calendar's "
        "work intervals. Empty: always at this location.",
    )
    date_start = fields.Date(
        string="Start date",
        help="Optional first day this presence pattern applies.",
    )
    date_end = fields.Date(
        string="End date",
        help="Optional last day (inclusive) this presence pattern applies.",
    )
    name = fields.Char(compute="_compute_name", store=True)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for line in self:
            if line.date_start and line.date_end and line.date_start > line.date_end:
                raise ValidationError(
                    self.env._("The start date must not be after the end date.")
                )

    @api.depends("location_id", "calendar_id")
    def _compute_name(self):
        for line in self:
            line.name = (
                f"{line.location_id.display_name} @ {line.calendar_id.name or 'always'}"
            )

    def _get_presence_intervals(self, start_dt, end_dt, calendar_map=None):
        """Intervals where this line puts its resource at the location.

        The query window clamped to the line's dates, intersected with
        the line's calendar (or the full window when no calendar).
        ``calendar_map`` is ``{calendar: {resource_id: Intervals}}``
        as precomputed by `get_locations_on_period`.
        """
        win_start, win_end = self._get_window(start_dt, end_dt)
        if win_start >= win_end:
            return Intervals([])
        resource = self.resource_id
        if self.calendar_id:
            if calendar_map is None:
                calendar_map = {
                    self.calendar_id: self.calendar_id._attendance_intervals_batch(
                        start_dt, end_dt, resource
                    )
                }
            intervals = calendar_map[self.calendar_id].get(resource.id, Intervals([]))
        else:
            intervals = Intervals([(start_dt, end_dt, resource)])
        return intervals & Intervals([(win_start, win_end, resource)])

    def _get_window(self, start_dt, end_dt):
        """The line's dated window intersected with the query range."""
        day_start = lambda d: datetime.combine(  # noqa: E731
            d, time.min, tzinfo=start_dt.tzinfo
        )
        win_start = (
            max(start_dt, day_start(self.date_start)) if self.date_start else start_dt
        )
        win_end = (
            min(end_dt, day_start(self.date_end) + timedelta(days=1))
            if self.date_end
            else end_dt
        )
        return win_start, win_end
