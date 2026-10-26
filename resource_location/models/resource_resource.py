# Copyright 2026 Daniel Reis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models
from odoo.tools.intervals import Intervals


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    presence_ids = fields.One2many(
        comodel_name="resource.location.presence",
        inverse_name="resource_id",
        string="Location presence",
        help="When and where this resource is present. "
        "Empty: available at any location.",
    )

    def get_locations_on_period(self, start_dt, end_dt):
        """Where each resource is present in the period.

        Returns ``{resource_id: {location_id: Intervals}}`` — one
        entry per resource, N location intervals each. The first
        presence record (by sequence) covering an instant wins; a
        resource without records gets an empty map meaning "present
        at any location".
        """
        # One attendance computation per calendar, for all resources —
        # not per presence line.
        calendar_map = {
            calendar: calendar._attendance_intervals_batch(start_dt, end_dt, self)
            for calendar in self.presence_ids.calendar_id
        }
        result = {}
        for resource in self:
            result[resource.id] = {}
            remaining = Intervals([(start_dt, end_dt, resource)])
            for line in resource.presence_ids:
                if not remaining:
                    break
                covered = remaining & line._get_presence_intervals(
                    start_dt, end_dt, calendar_map
                )
                if covered:
                    by_location = result[resource.id]
                    key = line.location_id.id
                    by_location[key] = by_location.get(key, Intervals([])) | covered
                    remaining = remaining - covered
        return result
