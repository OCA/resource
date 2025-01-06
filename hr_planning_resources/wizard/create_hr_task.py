from odoo import _, fields, models
from odoo.exceptions import UserError


class CreateHrTask(models.TransientModel):
    _name = "create.hr.task"
    _description = "Create HR Task"

    user_id = fields.Many2one(
        "res.users", string="Users", default=lambda self: self.env.user
    )
    date_start = fields.Datetime(string="Start Date", required=True)
    date_end = fields.Datetime(string="End Date", required=True)

    def _get_type(self, res_model):
        """Returns the type based on the resource model."""
        type_map = {
            "project.task": "task",
            "project.project": "project",
            "helpdesk.ticket": "ticket",
        }
        return type_map.get(res_model, False)

    def action_confirm(self):
        # Retrieve context parameters
        res_model = self.env.context.get("default_res_model")
        res_id = self.env.context.get("default_res_id")

        # Input validation with descriptive error messages
        if not res_model:
            raise UserError(_("No default resource model specified."))
        if not res_id:
            raise UserError(_("No active record id provided."))
        if not self.user_id.employee_id:
            raise UserError(
                _("The selected user does not have an associated employee.")
            )

        # Determine the record type
        record_type = self._get_type(res_model)
        if not record_type:
            raise UserError(_("Unsupported resource model: %s") % res_model)

        # Fetch the active record
        record = self.env[res_model].browse(res_id)
        if not record.exists():
            raise UserError(_("The record does not exist."))

        # Retrieve or create hr.task records
        hr_task_sudo = self.env["hr.task"].sudo()
        task_values = {
            "type": record_type,
            "employee_id": self.user_id.employee_id.id,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "task_id": res_id if record_type == "task" else False,
            "project_id": res_id if record_type == "project" else False,
            "ticket_id": res_id if record_type == "ticket" else False,
        }
        hr_task = hr_task_sudo.create(task_values)

        message = _(
            f"{hr_task.name} task created between {hr_task.date_start} and {hr_task.date_end}."
        )

        # Return notification message
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("HR Task Created"),
                "message": message,
                "sticky": True,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
