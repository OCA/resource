from odoo import api, models


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _inherit = ["helpdesk.ticket", "hr.task.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("default_user_id", False):
            for vals in vals_list:
                vals["user_id"] = self.env.context["default_user_id"]
        return super().create(vals_list)

    def action_create_hr_task(self):
        res = super().action_create_hr_task()

        res.update(
            {
                "context": {
                    **res.get("context", {}),
                    "default_user_ids": [self.user_id.id],
                }
            }
        )
        return res
