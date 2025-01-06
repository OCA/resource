from odoo import api, models


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "hr.task.mixin"]

    def _compute_hr_task_count(self):
        for record in self:
            project_count = self.env["hr.task"].search_count(
                [("project_id", "=", record.id)]
            )
            record.hr_task_count = project_count

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("default_user_id", False):
            vals_list[0]["user_id"] = [(4, self.env.context["default_user_id"])]
        return super().create(vals_list)
