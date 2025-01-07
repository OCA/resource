from collections import defaultdict
from datetime import timedelta
from functools import lru_cache
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
    def _get_leaves(self, date_from, date_to, employee_ids):
        calendar_leaves = self._get_calendar_leaves(date_from, date_to, employee_ids)
        leaves = self._group_leaves_by_employee(calendar_leaves, employee_ids)
        hr_leaves = self._get_hr_leaves(date_from, date_to, employee_ids)
        for leave in hr_leaves:
            leaves[leave.employee_id.id].append(leave)
        return leaves

    def _get_calendar_leaves(self, date_from, date_to, employee_ids):
        return self.env["resource.calendar.leaves"].search(
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

    def _group_leaves_by_employee(self, calendar_leaves, employee_ids):
        leaves = defaultdict(list)
        for leave in calendar_leaves:
            for employee in employee_ids:
                if self._is_leave_relevant_to_employee(leave, employee):
                    leaves[employee.id].append(leave)
        return leaves

    def _is_leave_relevant_to_employee(self, leave, employee):
        return (
            (not leave.company_id or leave.company_id == employee.company_id)
            and (not leave.resource_id or leave.resource_id == employee.resource_id)
            and (
                not leave.calendar_id
                or leave.calendar_id == employee.resource_calendar_id
            )
        )

    def _get_hr_leaves(self, date_from, date_to, employee_ids):
        return self.env["hr.leave"].search(
            [
                ("employee_id", "in", employee_ids.ids),
                ("state", "in", ["confirm", "validate1"]),
                ("date_from", "<=", date_to),
                ("date_to", ">=", date_from),
            ],
            order="date_from",
        )

    def _get_leave_message_warning(self, leaves, employee, date_from, date_to):
        @lru_cache(None)
        def localize(date):
            return (
                utc.localize(date)
                .astimezone(timezone(self.env.user.tz or "UTC"))
                .replace(tzinfo=None)
            )

        def format_period_leave(period, prefix):
            dfrom = period["from"]
            dto = period["to"]
            if period.get("show_hours", False):
                return _(
                    "{prefix} from the {dfrom_date} at {dfrom_time} to "
                    "the {dto_date} at {dto_time}"
                ).format(
                    prefix=prefix,
                    dfrom_date=format_date(self.env, localize(dfrom)),
                    dfrom_time=format_time(self.env, localize(dfrom)),
                    dto_date=format_date(self.env, localize(dto)),
                    dto_time=format_time(self.env, localize(dto)),
                )
            else:
                return _("{prefix} from the {dfrom} to the {dto}").format(
                    prefix=prefix,
                    dfrom=format_date(self.env, localize(dfrom)),
                    dto=format_date(self.env, localize(dto)),
                )

        warning = ""
        periods = self._group_leaves(leaves, employee, date_from, date_to)
        periods_by_states = [
            list(b) for _, b in groupby(periods, key=lambda x: x["is_validated"])
        ]

        for periods in periods_by_states:
            period_leaves = ""
            for period in periods:
                prefix = ""
                if period != periods[0]:
                    prefix = _(" and") if period == periods[-1] else ","
                period_leaves += format_period_leave(period, prefix)

            time_off_type = (
                _("is on time off")
                if periods[0].get("is_validated")
                else _("has requested time off")
            )
            warning += _("{employee} {time_off_type}{period_leaves}. \n").format(
                employee=employee.name,
                time_off_type=time_off_type,
                period_leaves=period_leaves,
            )
        return warning

    def _group_leaves(self, leaves, employee_id, date_from, date_to):
        work_times = self._get_work_times(employee_id, date_from, date_to)
        periods = []

        for leave in leaves:
            if self._is_leave_outside_range(leave, date_from, date_to):
                continue

            number_of_days, is_validated = self._get_leave_details(leave)
            if not periods or self._has_working_hours(
                periods[-1]["from"], leave.date_to, work_times
            ):
                periods.append(
                    {
                        "is_validated": is_validated,
                        "from": leave.date_from,
                        "to": leave.date_to,
                        "show_hours": number_of_days <= 1,
                    }
                )
            else:
                self._update_existing_period(
                    periods[-1], leave, is_validated, number_of_days
                )

        return periods

    def _get_work_times(self, employee_id, date_from, date_to):
        return {
            wk[0]: wk[1]
            for wk in employee_id.list_work_time_per_day(date_from, date_to)
        }

    def _is_leave_outside_range(self, leave, date_from, date_to):
        return leave.date_from > date_to or leave.date_to < date_from

    def _get_leave_details(self, leave):
        if isinstance(leave, self.pool["hr.leave"]):
            return leave.number_of_days, False
        else:
            dt_delta = leave.date_to - leave.date_from
            number_of_days = dt_delta.days + (dt_delta.seconds / 3600) / 24
            return number_of_days, True

    def _has_working_hours(self, start_dt, end_dt, work_times):
        diff_days = (end_dt - start_dt).days
        all_dates = [
            start_dt.date() + timedelta(days=delta) for delta in range(diff_days + 1)
        ]
        return any(d in work_times for d in all_dates)

    def _update_existing_period(self, period, leave, is_validated, number_of_days):
        period["is_validated"] = is_validated
        if period["to"] < leave.date_to:
            period["to"] = leave.date_to
        period["show_hours"] = period.get("show_hours") or number_of_days <= 1
