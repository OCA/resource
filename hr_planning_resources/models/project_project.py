from odoo import api, models


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "hr.task.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("default_user_id", False):
            vals_list[0]["user_id"] = [(4, self.env.context["default_user_id"])]
        return super().create(vals_list)

    def action_create_hr_task(self):
        res = super().action_create_hr_task()

        res.update(
            {
                "context": {
                    **res.get("context", {}),
                    "default_user_ids": [self.user_id.id],
                    "default_start_date": self.date_start,
                    "default_end_date": self.date,
                }
            }
        )
        return res
