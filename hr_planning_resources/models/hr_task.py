from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

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

    allocated_hours = fields.Float(
        "Allocated Time",
        compute="_compute_allocated_hours",
        store=True,
        readonly=False,
    )

    project_id = fields.Many2one("project.project", string="Project")
    filtered_project_id = fields.Many2one("project.project")
    task_id = fields.Many2one("project.task", string="Task")
    ticket_id = fields.Many2one("helpdesk.ticket", string="Ticket")

    leave_warning = fields.Char(compute="_compute_leave_warning")

    # Recurrency
    recurrency_id = fields.Many2one("hr.task.recurrency", string="Recurrency")
    repeat = fields.Boolean(
        compute="_compute_repeat", inverse="_inverse_repeat", copy=True
    )
    repeat_interval = fields.Integer(
        "Repeat every",
        default=1,
        compute="_compute_repeat_task_interval",
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
        compute="_compute_repeat_task_unit",
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
        compute="_compute_repeat_task_until",
        inverse="_inverse_repeat",
        copy=True,
    )
    repeat_number = fields.Integer(
        "Repetitions",
        default=1,
        compute="_compute_repeat_task_number",
        inverse="_inverse_repeat",
        copy=True,
    )

    is_recompute_forced = fields.Boolean(default=False, string="Recompute Forced?")

    @api.onchange("filtered_project_id")
    def _onchange_filtered_project_id(self):
        res = {"domain": {"task_id": []}}
        if self.filtered_project_id:
            res["domain"].update(
                {"task_id": [("project_id", "=", self.filtered_project_id.id)]}
            )
        return res

    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if "date_start" in fields_list:
            date_start = (
                fields.Datetime.from_string(res.get("date_start"))
                or self._default_date_start()
            )
            date_end = (
                fields.Datetime.from_string(res.get("date_end"))
                or self._default_date_end()
            )

            start = pytz.utc.localize(date_start)
            end = pytz.utc.localize(date_end)
            opening_hours = self._company_task_working_hours(start, end)
            res["date_start"] = (
                opening_hours[0].astimezone(pytz.utc).replace(tzinfo=None)
            )

            if "date_end" in fields_list:
                res["date_end"] = (
                    opening_hours[1].astimezone(pytz.utc).replace(tzinfo=None)
                )

        return res

    def _company_task_working_hours(self, start, end):
        company = self.company_id or self.env.company
        work_interval = company.resource_calendar_id._work_intervals_batch(start, end)[
            False
        ]
        intervals = [
            (date_start, date_stop) for date_start, date_stop, _ in work_interval
        ]
        date_start, date_end = (start, end)
        if intervals:
            if (date_end - date_start).days == 0:
                date_start = intervals[0][0]
                date_end = [
                    stop for _, stop in intervals if stop.date() == date_start.date()
                ][-1]
            else:
                date_start = intervals[0][0]
                date_end = intervals[-1][1]

        return (date_start, date_end)

    @api.depends("recurrency_id")
    def _compute_repeat(self):
        for task in self:
            task.repeat = bool(task.recurrency_id)

    @api.depends("recurrency_id.repeat_interval")
    def _compute_repeat_task_interval(self):
        recurrency_tasks = self.filtered("recurrency_id")
        for task in recurrency_tasks:
            task.repeat_interval = task.recurrency_id.repeat_interval
        (self - recurrency_tasks).update(self.default_get(["repeat_interval"]))

    @api.depends("recurrency_id.repeat_until", "repeat", "repeat_type")
    def _compute_repeat_task_until(self):
        for task in self:
            repeat_until = False
            if task.repeat and task.repeat_type == "until":
                if task.recurrency_id and task.recurrency_id.repeat_until:
                    repeat_until = task.recurrency_id.repeat_until
                elif task.date_start:
                    repeat_until = task.date_start + relativedelta(weeks=1)
            task.repeat_until = repeat_until

    @api.depends("recurrency_id.repeat_number", "repeat_type")
    def _compute_repeat_task_number(self):
        recurrency_tasks = self.filtered("recurrency_id")
        for task in recurrency_tasks:
            task.repeat_number = task.recurrency_id.repeat_number
        (self - recurrency_tasks).update(self.default_get(["repeat_number"]))

    @api.depends("recurrency_id.repeat_unit")
    def _compute_repeat_task_unit(self):
        non_recurrent_tasks = self.filtered(lambda task: not task.recurrency_id)
        recurrent_tasks = self - non_recurrent_tasks

        for task in recurrent_tasks:
            task.repeat_unit = task.recurrency_id.repeat_unit

        non_recurrent_tasks.update(self.default_get(["repeat_unit"]))

    @api.depends("recurrency_id.repeat_type")
    def _compute_repeat_type(self):
        recurrency_tasks = self.filtered("recurrency_id")
        for task in recurrency_tasks:
            task.repeat_type = task.recurrency_id.repeat_type
        (self - recurrency_tasks).update(self.default_get(["repeat_type"]))

    def _inverse_repeat(self):
        for task in self:
            if task.repeat and not task.recurrency_id.id:  # create the recurrence
                repeat_until = False
                repeat_number = 0
                if task.repeat_type == "until":
                    repeat_until = fields.Datetime.to_datetime(task.repeat_until)
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
                task.recurrency_id.unlink()

    @api.depends("date_start", "date_end", "employee_id")
    def _compute_leave_warning(self):
        assigned_tasks = self.filtered(lambda s: s.employee_id and s.date_start)
        unassigned_tasks = self - assigned_tasks
        unassigned_tasks.update(
            {
                "leave_warning": False,
            }
        )

        if not assigned_tasks:
            return

        min_date = min(assigned_tasks.mapped("date_start"))
        date_from = max(min_date, fields.Datetime.today())
        date_to = max(assigned_tasks.mapped("date_end"))
        employee_ids = assigned_tasks.mapped("employee_id")

        leaves = self.env["hr.leave"]._get_leaves(
            date_from=date_from,
            date_to=date_to,
            employee_ids=employee_ids,
        )

        for task in assigned_tasks:
            task_leaves = leaves.get(task.employee_id.id)
            if task_leaves:
                warning = self.env["hr.leave"]._get_leave_message_warning(
                    leaves=task_leaves,
                    employee=task.employee_id,
                    date_from=task.date_start,
                    date_to=task.date_end,
                )
                task.leave_warning = warning
            else:
                task.leave_warning = False

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
        "is_recompute_forced",
    )
    def _compute_allocated_hours(self):
        """
        Compute working hours considering:
        - Employee's work schedule (unless is_recompute_forced is True)
        - Approved time off (vacations, leaves)
        - Public holidays
        """
        for record in self:
            if not (record.date_start and record.date_end and record.employee_id):
                record.allocated_hours = 0.0
                continue

            if record.is_recompute_forced:
                total_seconds = (record.date_end - record.date_start).total_seconds()
                record.allocated_hours = round(total_seconds / 3600.0, 2)
                continue

            # Normal calculation for non-forced records
            calendar = (
                record.employee_id.resource_calendar_id
                or record.env.company.resource_calendar_id
            )
            if not calendar:
                record.allocated_hours = 0.0
                continue

            # Get base working hours without considering leaves
            work_days_data = record.employee_id._get_work_days_data_batch(
                record.date_start, record.date_end
            )[record.employee_id.id]
            base_hours = work_days_data["hours"]

            # Get leaves (including vacations)
            domain = [
                ("employee_id", "=", record.employee_id.id),
                ("state", "=", "validate"),
                ("date_from", "<=", record.date_end),
                ("date_to", ">=", record.date_start),
            ]
            leaves = record.env["hr.leave"].search(domain)

            # Calculate leave hours
            leave_hours = 0
            for leave in leaves:
                # Get overlapping period
                leave_start = max(leave.date_from, record.date_start)
                leave_end = min(leave.date_to, record.date_end)

                # Calculate leave hours for the overlapping period
                leave_days_data = record.employee_id._get_work_days_data_batch(
                    leave_start, leave_end
                )[record.employee_id.id]
                leave_hours += leave_days_data["hours"]

            # Subtract leave hours from base hours
            record.allocated_hours = max(0, base_hours - leave_hours)

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
