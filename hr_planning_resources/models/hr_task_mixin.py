from odoo import models


class HrTaskMixin(models.AbstractModel):
    _name = "hr.task.mixin"

    def action_create_hr_task(self):
        self.ensure_one()
        view_id = self.env.ref("hr_planning_resources.create_hr_task_view_form")
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_res_model": self._name,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "create.hr.task",
            "view_mode": "form",
            "views": [[view_id.id, "form"]],
            "res_id": self.id,
            "context": ctx,
            "target": "new",
        }
