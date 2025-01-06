from odoo import api, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "hr.task.mixin"]

    def _compute_hr_task_count(self):
        for record in self:
            task_count = self.env["hr.task"].search_count([("task_id", "=", record.id)])
            record.hr_task_count = task_count

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("default_user_id", False):
            vals_list[0]["user_ids"] = [(4, self.env.context["default_user_id"])]
        return super().create(vals_list)
