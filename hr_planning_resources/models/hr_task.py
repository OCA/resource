from collections import defaultdict
from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

from odoo.addons.resource.models.resource import Intervals, sum_intervals
from odoo.addons.resource.models.resource_mixin import timezone_datetime

TASK_TYPES = [
    ("task", _("Task")),
    ("project", _("Project")),
    ("ticket", _("Ticket")),
]


class HrTask(models.Model):
    _name = "hr.task"
    _description = "HR Planning Resource"
    _inherit = ["mail.thread.cc", "mail.activity.mixin"]
    _sql_constraints = [
        (
            "date_check",
            "CHECK (date_start <= date_end)",
            "Error: End date must be greater than start date!",
        ),
    ]
    _order = "date_start desc, id desc"

    def _default_date_start(self):
        return datetime.combine(fields.Date.context_today(self), time.min)

    def _default_date_end(self):
        return datetime.combine(fields.Date.context_today(self), time.max)

    def _get_default_employee(self):
        return self.env["hr.employee"].search([("user_id", "=", self.env.uid)], limit=1)

    name = fields.Char(compute="_compute_name", store=True)
    title = fields.Char(compute="_compute_title", store=True)
    type = fields.Selection(selection=TASK_TYPES, required=True, tracking=True)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        tracking=True,
        default=lambda self: self._get_default_employee(),
    )
    resource_id = fields.Many2one(
        "resource.resource", related="employee_id.resource_id"
    )
    user_id = fields.Many2one("res.users", related="employee_id.user_id")
    department_id = fields.Many2one(
        "hr.department",
        related="employee_id.department_id",
    )
    employee_parent_id = fields.Many2one(related="employee_id.parent_id", store=True)
    member_of_department = fields.Boolean(related="employee_id.member_of_department")
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.user.company_id.id,
        required=True,
    )
    state = fields.Selection(
        [
            ("planified", "Planified"),
            ("in_progress", "In Progress"),
            ("finished", "Finished"),
            ("cancel", "Cancelled"),
        ],
        default="planified",
        tracking=True,
    )
    date_start = fields.Datetime(
        string="Start Date",
        required=True,
        tracking=True,
    )

    date_end = fields.Datetime(string="End Date", required=True, tracking=True)
    planned_hours = fields.Float(
        string="Duration",
        compute="_compute_planned_hours",
        store=True,
        tracking=True,
    )

    allocated_hours = fields.Float(
        "Allocated Time",
        compute="_compute_allocated_hours",
        store=True,
        readonly=False,
    )
    allocated_percentage = fields.Float(
        "Allocated Time %",
        default=100,
        compute="_compute_allocated_percentage",
        store=True,
        readonly=False,
        group_operator="avg",
    )
    working_days_count = fields.Float(
        "Working Days", compute="_compute_working_days_count", store=True
    )
    duration = fields.Float(compute="_compute_task_duration")

    project_id = fields.Many2one("project.project", string="Project")
    filtered_project_id = fields.Many2one("project.project")
    task_id = fields.Many2one("project.task", string="Task")
    ticket_id = fields.Many2one("helpdesk.ticket", string="Ticket")

    leave_warning = fields.Char(compute="_compute_leave_warning")
    is_absent = fields.Boolean(
        "Employees on Time Off",
        compute="_compute_leave_warning",
        search="_search_is_absent",
        compute_sudo=True,
        readonly=True,
    )

    # Recurrency
    recurrency_id = fields.Many2one("hr.task.recurrency", string="Recurrency")
    repeat = fields.Boolean(
        compute="_compute_repeat", inverse="_inverse_repeat", copy=True
    )
    repeat_interval = fields.Integer(
        "Repeat every",
        default=1,
        compute="_compute_repeat_interval",
        inverse="_inverse_repeat",
        copy=True,
    )
    repeat_unit = fields.Selection(
        [
            ("day", "Days"),
            ("week", "Weeks"),
            ("month", "Months"),
            ("year", "Years"),
        ],
        default="week",
        compute="_compute_repeat_unit",
        inverse="_inverse_repeat",
        required=True,
    )
    repeat_type = fields.Selection(
        [
            ("forever", "Forever"),
            ("until", "Until"),
            ("x_times", "Number of Repetitions"),
        ],
        default="forever",
        compute="_compute_repeat_type",
        inverse="_inverse_repeat",
        copy=True,
    )
    repeat_until = fields.Date(
        compute="_compute_repeat_until",
        inverse="_inverse_repeat",
        copy=True,
    )
    repeat_number = fields.Integer(
        "Repetitions",
        default=1,
        compute="_compute_repeat_number",
        inverse="_inverse_repeat",
        copy=True,
    )
    confirm_delete = fields.Boolean(
        "Confirm tasks Deletion", compute="_compute_confirm_delete"
    )

    @api.onchange("filtered_project_id")
    def _onchange_filtered_project_id(self):
        res = {"domain": {"task_id": []}}
        if self.filtered_project_id:
            res["domain"].update(
                {"task_id": [("project_id", "=", self.filtered_project_id.id)]}
            )
        return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if "date_start" in fields_list:
            date_start = (
                fields.Datetime.from_string(res.get("date_start"))
                if res.get("date_start")
                else self._default_date_start()
            )
            date_end = (
                fields.Datetime.from_string(res.get("date_end"))
                if res.get("date_end")
                else self._default_date_end()
            )
            start = pytz.utc.localize(date_start)
            end = pytz.utc.localize(date_end) if date_end else self._default_date_end()
            opening_hours = self._company_working_hours(start, end)
            res["date_start"] = (
                opening_hours[0].astimezone(pytz.utc).replace(tzinfo=None)
            )

            if "date_end" in fields_list:
                res["date_end"] = (
                    opening_hours[1].astimezone(pytz.utc).replace(tzinfo=None)
                )

        return res

    def _company_working_hours(self, start, end):
        company = self.company_id or self.env.company
        work_interval = company.resource_calendar_id._work_intervals_batch(start, end)[
            False
        ]
        intervals = [
            (date_start, date_stop)
            for date_start, date_stop, attendance in work_interval
        ]
        date_start, date_end = (start, end)
        if intervals and (date_end - date_start).days == 0:
            date_start = intervals[0][0]
            date_end = [
                stop for start, stop in intervals if stop.date() == date_start.date()
            ][-1]
        elif intervals and (date_end - date_start).days >= 0:
            date_start = intervals[0][0]
            date_end = intervals[-1][1]

        return (date_start, date_end)

    def _calculate_task_duration(self):
        self.ensure_one()
        period = self.date_end - self.date_start
        task_duration = period.total_seconds() / 3600
        max_duration = (
            period.days + (1 if period.seconds else 0)
        ) * self.company_id.resource_calendar_id.hours_per_day
        if not max_duration or max_duration >= task_duration:
            return task_duration
        return max_duration

    def _get_working_hours_over_period(
        self, start_utc, end_utc, work_intervals, calendar_intervals
    ):
        start = max(start_utc, pytz.utc.localize(self.date_start))
        end = min(end_utc, pytz.utc.localize(self.date_end))
        task_interval = Intervals(
            [(start, end, self.env["resource.calendar.attendance"])]
        )
        working_intervals = (
            work_intervals[self.resource_id.id]
            if self.resource_id
            else calendar_intervals[self.company_id.resource_calendar_id.id]
        )
        return sum_intervals(task_interval & working_intervals)

    @api.depends(
        "date_start",
        "date_end",
        "employee_id.resource_calendar_id",
        "allocated_hours",
    )
    def _compute_allocated_percentage(self):
        allocated_hours_field = self._fields["allocated_hours"]
        tasks = self.filtered(
            lambda task: not self.env.is_to_compute(allocated_hours_field, task)
            and task.date_start
            and task.date_end
            and task.date_start != task.date_end
        )
        if not tasks:
            return
        for task in tasks:
            task.allocated_percentage = (
                100 * task.allocated_hours / task._calculate_task_duration()
            )

    @api.depends(
        "date_start",
        "date_end",
        "resource_id.calendar_id",
        "company_id.resource_calendar_id",
        "allocated_percentage",
    )
    def _compute_allocated_hours(self):
        percentage_field = self._fields["allocated_percentage"]
        self.env.remove_to_compute(percentage_field, self)
        planning_tasks = self.filtered(lambda s: not s.company_id and not s.resource_id)
        tasks_with_calendar = self - planning_tasks
        for task in planning_tasks:
            ratio = task.allocated_percentage / 100.0
            task.allocated_hours = task._calculate_task_duration() * ratio
        if tasks_with_calendar:
            unplanned_tasks_with_calendar = tasks_with_calendar.filtered_domain(
                [
                    "|",
                    ("date_start", "=", False),
                    ("date_end", "=", False),
                ]
            )
            for task in unplanned_tasks_with_calendar:
                task.allocated_hours = 0.0
            planned_tasks_with_calendar = (
                tasks_with_calendar - unplanned_tasks_with_calendar
            )
            if not planned_tasks_with_calendar:
                return
            start_utc = pytz.utc.localize(
                min(planned_tasks_with_calendar.mapped("date_start"))
            )
            end_utc = pytz.utc.localize(
                max(planned_tasks_with_calendar.mapped("date_end"))
            )
            (
                resource_work_intervals,
                calendar_work_intervals,
            ) = tasks_with_calendar.resource_id._get_valid_work_intervals(
                start_utc,
                end_utc,
                calendars=tasks_with_calendar.company_id.resource_calendar_id,
            )
            for task in planned_tasks_with_calendar:
                task.allocated_hours = task._get_duration_over_period(
                    pytz.utc.localize(task.date_start),
                    pytz.utc.localize(task.date_end),
                    resource_work_intervals,
                    calendar_work_intervals,
                    has_allocated_hours=False,
                )

    def _get_duration_over_period(
        self,
        start_utc,
        stop_utc,
        work_intervals,
        calendar_intervals,
        has_allocated_hours=True,
    ):
        assert start_utc.tzinfo and stop_utc.tzinfo
        self.ensure_one()
        start, stop = start_utc.replace(tzinfo=None), stop_utc.replace(tzinfo=None)
        if has_allocated_hours and self.date_start >= start and self.date_end <= stop:
            return self.allocated_hours

        ratio = self.allocated_percentage / 100.0
        working_hours = self._get_working_hours_over_period(
            start_utc, stop_utc, work_intervals, calendar_intervals
        )
        return working_hours * ratio

    @api.depends("date_start", "date_end", "resource_id")
    def _compute_working_days_count(self):
        tasks_per_calendar = defaultdict(set)
        planned_dates_per_calendar_id = defaultdict(
            lambda: (datetime.max, datetime.min)
        )
        for task in self:
            if not task.employee_id or not task.date_start or not task.date_end:
                task.working_days_count = 0
                continue
            tasks_per_calendar[task.resource_id.calendar_id].add(task.id)
            datetime_begin, datetime_end = planned_dates_per_calendar_id[
                task.resource_id.calendar_id.id
            ]
            datetime_begin = min(datetime_begin, task.date_start)
            datetime_end = max(datetime_end, task.date_end)
            planned_dates_per_calendar_id[task.resource_id.calendar_id.id] = (
                datetime_begin,
                datetime_end,
            )
        for calendar, task_ids in tasks_per_calendar.items():
            tasks = self.env["hr.task"].browse(list(task_ids))
            if not calendar:
                tasks.working_days_count = 0
                continue
            datetime_begin, datetime_end = planned_dates_per_calendar_id[calendar.id]
            datetime_begin = timezone_datetime(datetime_begin)
            datetime_end = timezone_datetime(datetime_end)
            resources = tasks.resource_id
            day_total = calendar._get_resources_day_total(
                datetime_begin, datetime_end, resources
            )
            intervals = calendar._work_intervals_batch(
                datetime_begin, datetime_end, resources
            )
            for task in tasks:
                task.working_days_count = calendar._get_days_data(
                    intervals[task.resource_id.id]
                    & Intervals(
                        [
                            (
                                timezone_datetime(task.date_start),
                                timezone_datetime(task.date_end),
                                self.env["resource.calendar.attendance"],
                            )
                        ]
                    ),
                    day_total[task.resource_id.id],
                )["days"]

    @api.depends("date_start", "date_end")
    def _compute_task_duration(self):
        for task in self:
            if not self.date_start or not self.date_end:
                task.duration = 0.0
            else:
                task.duration = (task.date_end - task.date_start).total_seconds() / 3600

    @api.depends("repeat_until", "repeat_number")
    def _compute_confirm_delete(self):
        for task in self:
            if task.recurrency_id and task.repeat_until and task.repeat_number:
                recurrence_end_dt = (
                    task.repeat_until
                    or task.recurrency_id._get_recurrence_last_datetime()
                )
                task.confirm_delete = (
                    fields.Date.to_date(recurrence_end_dt) > task.repeat_until
                )
            else:
                task.confirm_delete = False

    @api.depends("recurrency_id")
    def _compute_repeat(self):
        for task in self:
            if task.recurrency_id:
                task.repeat = True
            else:
                task.repeat = False

    @api.depends("recurrency_id.repeat_interval")
    def _compute_repeat_interval(self):
        recurrency_tasks = self.filtered("recurrency_id")
        for task in recurrency_tasks:
            if task.recurrency_id:
                task.repeat_interval = task.recurrency_id.repeat_interval
        (self - recurrency_tasks).update(self.default_get(["repeat_interval"]))

    @api.depends("recurrency_id.repeat_until", "repeat", "repeat_type")
    def _compute_repeat_until(self):
        for task in self:
            repeat_until = False
            if task.repeat and task.repeat_type == "until":
                if task.recurrency_id and task.recurrency_id.repeat_until:
                    repeat_until = task.recurrency_id.repeat_until
                elif task.date_start:
                    repeat_until = task.date_start + relativedelta(weeks=1)
            task.repeat_until = repeat_until

    @api.depends("recurrency_id.repeat_number", "repeat_type")
    def _compute_repeat_number(self):
        recurrency_tasks = self.filtered("recurrency_id")
        for task in recurrency_tasks:
            task.repeat_number = task.recurrency_id.repeat_number
        (self - recurrency_tasks).update(self.default_get(["repeat_number"]))

    @api.depends("recurrency_id.repeat_unit")
    def _compute_repeat_unit(self):
        non_recurrent_tasks = self.env["hr.task"]
        for task in self:
            if task.recurrency_id:
                task.repeat_unit = task.recurrency_id.repeat_unit
            else:
                non_recurrent_tasks += task
        non_recurrent_tasks.update(self.default_get(["repeat_unit"]))

    @api.depends("recurrency_id.repeat_type")
    def _compute_repeat_type(self):
        recurrency_tasks = self.filtered("recurrency_id")
        for task in recurrency_tasks:
            if task.recurrency_id:
                task.repeat_type = task.recurrency_id.repeat_type
        (self - recurrency_tasks).update(self.default_get(["repeat_type"]))

    def _inverse_repeat(self):
        for task in self:
            if task.repeat and not task.recurrency_id.id:  # create the recurrence
                repeat_until = False
                repeat_number = 0
                if task.repeat_type == "until":
                    repeat_until = datetime.combine(
                        fields.Date.to_date(task.repeat_until),
                        datetime.max.time(),
                    )
                    repeat_until = (
                        repeat_until.replace(
                            tzinfo=pytz.timezone(
                                task.company_id.resource_calendar_id.tz or "UTC"
                            )
                        )
                        .astimezone(pytz.utc)
                        .replace(tzinfo=None)
                    )
                if task.repeat_type == "x_times":
                    repeat_number = task.repeat_number
                recurrency_values = {
                    "repeat_interval": task.repeat_interval,
                    "repeat_unit": task.repeat_unit,
                    "repeat_until": repeat_until,
                    "repeat_number": repeat_number,
                    "repeat_type": task.repeat_type,
                    "company_id": task.company_id.id,
                }
                recurrence = self.env["hr.task.recurrency"].create(recurrency_values)
                task.recurrency_id = recurrence
                task.recurrency_id._repeat_task()
            elif not task.repeat and task.recurrency_id.id:
                task.recurrency_id._delete_task(task.date_end)
                task.recurrency_id.unlink()  # will set recurrency_id to NULL

    @api.depends("date_start", "date_end", "employee_id")
    def _compute_overlap_task_count(self):
        for rec in self:
            rec.overlap_task_count = self.search_count(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("date_start", "<", rec.date_end),
                    ("date_end", ">", rec.date_start),
                ]
            )

    @api.depends("date_start", "date_end", "employee_id")
    def _compute_leave_warning(self):
        assigned_tasks = self.filtered(lambda s: s.employee_id and s.date_start)
        (self - assigned_tasks).leave_warning = False
        (self - assigned_tasks).is_absent = False

        if not assigned_tasks:
            return

        min_date = min(assigned_tasks.mapped("date_start"))
        date_from = (
            min_date if min_date > fields.Datetime.today() else fields.Datetime.today()
        )
        leaves = self.env["hr.leave"]._get_leave_interval(
            date_from=date_from,
            date_to=max(assigned_tasks.mapped("date_end")),
            employee_ids=assigned_tasks.mapped("employee_id"),
        )

        for task in assigned_tasks:
            warning = False
            task_leaves = leaves.get(task.employee_id.id)
            if task_leaves:
                warning = self.env["hr.leave"]._get_leave_warning(
                    leaves=task_leaves,
                    employee=task.employee_id,
                    date_from=task.date_start,
                    date_to=task.date_end,
                )
            task.leave_warning = warning
            task.is_absent = bool(warning)

    def _compute_title(self):
        for record in self:
            if record.name:
                record.title = record.name
            else:
                record.title = ""

    @api.depends("type", "task_id", "project_id", "ticket_id")
    def _compute_name(self):
        for record in self:
            if record.type == "task":
                record.name = record.task_id.name
            elif record.type == "project":
                record.name = record.project_id.name
            elif record.type == "ticket":
                record.name = record.ticket_id.name
            else:
                record.name = ""

    @api.depends(
        "date_start",
        "date_end",
        "employee_id",
        "employee_id.resource_calendar_id",
    )
    def _compute_planned_hours(self):
        for record in self:
            if record.date_start and record.date_end and record.employee_id:
                work_days_data = record.employee_id._get_work_days_data_batch(
                    record.date_start, record.date_end
                )[record.employee_id.id]
                record.planned_hours = work_days_data["hours"]
            else:
                record.planned_hours = 0.0

    def _get_tz(self):
        return (
            self.env.user.tz
            or self.employee_id.tz
            or self.employee_id.tz
            or self._context.get("tz")
            or self.company_id.resource_calendar_id.tz
            or "UTC"
        )

    def _add_delta_with_dst(self, start, delta):
        try:
            tz = pytz.timezone(self._get_tz())
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
        start = start.replace(tzinfo=pytz.utc).astimezone(tz).replace(tzinfo=None)
        result = start + delta
        return tz.localize(result).astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _search_is_absent(self, operator, value):
        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise NotImplementedError(_("Operation not supported"))

        today = fields.Datetime.today()
        tasks = self.search(
            [
                ("employee_id", "!=", False),
                (
                    "date_end",
                    ">",
                    today,
                ),
            ]
        )
        if not tasks:
            return []

        min_date = min(tasks.mapped("date_start"))
        date_from = max(min_date, today)
        mapped_leaves = self.env["hr.leave"]._get_leave_interval(
            date_from=date_from,
            date_to=max(tasks.mapped("date_end")),
            employee_ids=tasks.mapped("employee_id"),
        )

        task_ids = []
        for task in tasks.filtered(lambda s: s.employee_id.id in mapped_leaves):
            leaves = mapped_leaves[task.employee_id.id]
            period = self.env["hr.leave"]._group_leaves(
                leaves, task.employee_id, task.date_start, task.date_end
            )
            if period:
                task_ids.append(task.id)
        if operator == "!=":
            value = not value
        return [("id", "in" if value else "not in", task_ids)]

    @api.onchange("type")
    def _onchange_type(self):
        if self.type == "task":
            self.write({"project_id": False, "ticket_id": False})
        elif self.type == "project":
            self.write({"task_id": False, "ticket_id": False})
        elif self.type == "ticket":
            self.write({"project_id": False, "task_id": False})

    def write(self, values):
        result = super().write(values)
        if any(
            key
            in (
                "repeat",
                "repeat_unit",
                "repeat_type",
                "repeat_until",
                "repeat_interval",
                "repeat_number",
            )
            for key in values
        ):
            for task in self:
                if task.recurrency_id and values.get("repeat") is None:
                    repeat_type = (
                        values.get("repeat_type") or task.recurrency_id.repeat_type
                    )
                    repeat_until = (
                        values.get("repeat_until") or task.recurrency_id.repeat_until
                    )
                    repeat_number = values.get("repeat_number", 0) or task.repeat_number
                    if repeat_type == "until":
                        repeat_until = datetime.combine(
                            fields.Date.to_date(repeat_until),
                            datetime.max.time(),
                        )
                        repeat_until = (
                            repeat_until.replace(
                                tzinfo=pytz.timezone(
                                    task.company_id.resource_calendar_id.tz or "UTC"
                                )
                            )
                            .astimezone(pytz.utc)
                            .replace(tzinfo=None)
                        )
                    recurrency_values = {
                        "repeat_interval": values.get("repeat_interval")
                        or task.recurrency_id.repeat_interval,
                        "repeat_unit": values.get("repeat_unit")
                        or task.recurrency_id.repeat_unit,
                        "repeat_until": (
                            repeat_until if repeat_type == "until" else False
                        ),
                        "repeat_number": repeat_number,
                        "repeat_type": repeat_type,
                        "company_id": task.company_id.id,
                    }
                    task.recurrency_id.write(recurrency_values)
                    if task.repeat_type == "x_times":
                        recurrency_values[
                            "repeat_until"
                        ] = task.recurrency_id._get_recurrence_last_datetime()
                    date_end = (
                        task.date_end
                        if values.get("repeat_unit")
                        else recurrency_values.get("repeat_until")
                    )
                    task.recurrency_id._delete_task(date_end)
                    task.recurrency_id._repeat_task()
        return result

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def action_planified(self):
        self.write({"state": "planified"})
        return True

    def action_in_progress(self):
        self.write({"state": "in_progress"})
        return True

    def action_finished(self):
        self.write({"state": "finished"})
        return True

    def cron_update_task_state(self):
        self.search(
            [
                ("date_end", "<", fields.Datetime.now()),
                ("state", "=", "in_progress"),
            ]
        ).write({"state": "finished"})

        self.search(
            [
                ("date_start", "<=", fields.Datetime.now()),
                ("state", "=", "planified"),
            ]
        ).write({"state": "in_progress"})
