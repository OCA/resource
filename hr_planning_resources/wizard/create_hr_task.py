from odoo import fields, models


class CreateHrTask(models.TransientModel):
    _name = "create.hr.task"
    _description = "Create HR Task"

    res_model = fields.Char(string="Model", required=True)
    active_id = fields.Integer(string="ID", required=True)
    user_ids = fields.Many2many("res.users", string="Users", required=True)
    date_start = fields.Datetime(string="Start Date", required=True)
    date_end = fields.Datetime(string="End Date", required=True)

    def _get_type(self, res_model):
        if res_model == "project.task":
            return "task"
        elif res_model == "project.project":
            return "project"
        elif res_model == "helpdesk.ticket":
            return "ticket"
        else:
            return ""

    def action_confirm(self):
        users = self.env.context.get("default_user_ids", [])
        res_model = self.env.context.get("default_res_model", "project.task")
        active_id = self.env.context.get("active_id", False)

        date_start = (
            self.env.context.get("default_start_date", False) or fields.Datetime.now()
        )
        date_end = (
            self.env.context.get("default_end_date", False) or fields.Datetime.now()
        )

        record_type = self._get_type(res_model)
        employee_ids = self.env["res.users"].browse(users).mapped("employee_id")
        record_id = self.env[res_model].browse(active_id)
        hr_task_sudo = self.env["hr.task"].sudo()

        hr_tasks = self.env["hr.task"].search(
            [
                ("name", "=", record_id.name),
                ("employee_id", "in", employee_ids.ids),
            ]
        )

        employee_ids = employee_ids - hr_tasks.mapped("employee_id")
        for employee_id in employee_ids:
            hr_task_sudo.create(
                {
                    "type": record_type,
                    "employee_id": employee_id.id,
                    "date_start": date_start,
                    "date_end": date_end,
                    "task_id": (active_id if record_type == "task" else False),
                    "project_id": (active_id if record_type == "project" else False),
                    "ticket_id": (active_id if record_type == "ticket" else False),
                }
            )
