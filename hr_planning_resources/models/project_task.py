from odoo import api, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "hr.task.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("default_user_id", False):
            vals_list[0]["user_ids"] = [(4, self.env.context["default_user_id"])]
        return super().create(vals_list)

    def action_create_hr_task(self):
        res = super().action_create_hr_task()

        res.update(
            {
                "context": {
                    **res.get("context", {}),
                    "default_user_ids": self.user_ids.ids,
                    "default_start_date": self.date_assign,
                    "default_end_date": self.date_end,
                }
            }
        )
        return res
