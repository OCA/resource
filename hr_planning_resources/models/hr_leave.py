from collections import defaultdict
from datetime import timedelta
from itertools import groupby

from pytz import timezone, utc

from odoo import _, api, models
from odoo.tools.misc import get_lang


def format_time(env, time):
    return time.strftime(get_lang(env).time_format)


def format_date(env, date):
    return date.strftime(get_lang(env).date_format)


class HrLeave(models.Model):
    _inherit = "hr.leave"

    @api.model
    def _get_leave_interval(self, date_from, date_to, employee_ids):
        # Validated hr.leave create a resource.calendar.leaves
        calendar_leaves = self.env["resource.calendar.leaves"].search(
            [
                ("time_type", "=", "leave"),
                "|",
                ("company_id", "in", employee_ids.mapped("company_id").ids),
                ("company_id", "=", False),
                "|",
                ("resource_id", "in", employee_ids.mapped("resource_id").ids),
                ("resource_id", "=", False),
                ("date_from", "<=", date_to),
                ("date_to", ">=", date_from),
            ],
            order="date_from",
        )

        leaves = defaultdict(list)
        for leave in calendar_leaves:
            for employee in employee_ids:
                if (
                    (not leave.company_id or leave.company_id == employee.company_id)
                    and (
                        not leave.resource_id
                        or leave.resource_id == employee.resource_id
                    )
                    and (
                        not leave.calendar_id
                        or leave.calendar_id == employee.resource_calendar_id
                    )
                ):
                    leaves[employee.id].append(leave)

        # Get non-validated time off
        leaves_query = self.env["hr.leave"].search(
            [
                ("employee_id", "in", employee_ids.ids),
                ("state", "in", ["confirm", "validate1"]),
                ("date_from", "<=", date_to),
                ("date_to", ">=", date_from),
            ],
            order="date_from",
        )
        for leave in leaves_query:
            leaves[leave.employee_id.id].append(leave)
        return leaves

    def _get_leave_warning(self, leaves, employee, date_from, date_to):
        loc_cache = {}

        def localize(date):
            if date not in loc_cache:
                loc_cache[date] = (
                    utc.localize(date)
                    .astimezone(timezone(self.env.user.tz or "UTC"))
                    .replace(tzinfo=None)
                )
            return loc_cache.get(date)

        warning = ""
        periods = self._group_leaves(leaves, employee, date_from, date_to)
        periods_by_states = [
            list(b) for a, b in groupby(periods, key=lambda x: x["is_validated"])
        ]

        for periods in periods_by_states:
            period_leaves = ""
            for period in periods:
                dfrom = period["from"]
                dto = period["to"]
                prefix = ""
                if period != periods[0]:
                    if period == periods[-1]:
                        prefix = _(" and")
                    else:
                        prefix = ","

                if period.get("show_hours", False):
                    period_leaves += _(
                        "%(prefix)s from the %(dfrom_date)s at %(dfrom)s to the %(dto_date)s at %(dto)s",
                        prefix=prefix,
                        dfrom_date=format_date(self.env, localize(dfrom)),
                        dfrom=format_time(self.env, localize(dfrom)),
                        dto_date=format_date(self.env, localize(dto)),
                        dto=format_time(self.env, localize(dto)),
                    )
                else:
                    period_leaves += _(
                        "%(prefix)s from the %(dfrom)s to the %(dto)s",
                        prefix=prefix,
                        dfrom=format_date(self.env, localize(dfrom)),
                        dto=format_date(self.env, localize(dto)),
                    )

            time_off_type = (
                _("is on time off")
                if periods[0].get("is_validated")
                else _("has requested time off")
            )
            warning += _(
                "%(employee)s %(time_off_type)s%(period_leaves)s. \n",
                employee=employee.name,
                period_leaves=period_leaves,
                time_off_type=time_off_type,
            )
        return warning

    def _group_leaves(self, leaves, employee_id, date_from, date_to):
        """
        Returns all the leaves happening between `planned_date_begin` and `planned_date_end`
        """
        work_times = {
            wk[0]: wk[1]
            for wk in employee_id.list_work_time_per_day(date_from, date_to)
        }

        def has_working_hours(start_dt, end_dt):
            """
            Returns `True` if there are any working days between `start_dt` and `end_dt`.
            """
            diff_days = (end_dt - start_dt).days
            all_dates = [
                start_dt.date() + timedelta(days=delta)
                for delta in range(diff_days + 1)
            ]
            return any(d in work_times for d in all_dates)

        periods = []
        for leave in leaves:
            if leave.date_from > date_to or leave.date_to < date_from:
                continue

            # Can handle both hr.leave and resource.calendar.leaves
            number_of_days = 0
            is_validated = True
            if isinstance(leave, self.pool["hr.leave"]):
                number_of_days = leave.number_of_days
                is_validated = False
            else:
                dt_delta = leave.date_to - leave.date_from
                number_of_days = dt_delta.days + ((dt_delta.seconds / 3600) / 24)

            if not periods or has_working_hours(periods[-1]["from"], leave.date_to):
                periods.append(
                    {
                        "is_validated": is_validated,
                        "from": leave.date_from,
                        "to": leave.date_to,
                        "show_hours": number_of_days <= 1,
                    }
                )
            else:
                periods[-1]["is_validated"] = is_validated
                if periods[-1]["to"] < leave.date_to:
                    periods[-1]["to"] = leave.date_to
                periods[-1]["show_hours"] = (
                    periods[-1].get("show_hours") or number_of_days <= 1
                )
        return periods
