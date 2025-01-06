from odoo import api, models


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _inherit = ["helpdesk.ticket", "hr.task.mixin"]

    def _compute_hr_task_count(self):
        for record in self:
            ticket_count = self.env["hr.task"].search_count(
                [("ticket_id", "=", record.id)]
            )
            record.hr_task_count = ticket_count

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("default_user_id", False):
            for vals in vals_list:
                vals["user_id"] = self.env.context["default_user_id"]
        return super().create(vals_list)
