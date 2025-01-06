from odoo import _, fields, models


class HrTaskMixin(models.AbstractModel):
    _name = "hr.task.mixin"
    _description = "HR Task Mixin"

    hr_task_count = fields.Integer(
        compute="_compute_hr_task_count", string="HR Task Count"
    )

    def _compute_hr_task_count(self):
        """
        Compute the number of HR tasks related to this record.
        Should be implemented by concrete models that inherit this mixin.
        """
        raise NotImplementedError(
            _("The method _compute_hr_task_count must be implemented in the subclass.")
        )

    def action_view_hr_task(self):
        self.ensure_one()

        # Determine the domain based on the model type
        domain_map = {
            "project.project": [("project_id", "=", self.id)],
            "helpdesk.ticket": [("ticket_id", "=", self.id)],
        }
        domain = domain_map.get(self._name, [("task_id", "=", self.id)])

        # Prepare and return the action to view the HR tasks
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.task",
            "view_mode": "tree,form",
            "views": [[False, "tree"], [False, "form"]],
            "context": dict(self.env.context),
            "domain": domain,
        }

    def action_create_hr_task(self):
        self.ensure_one()

        # Fetch the form view for creating HR tasks
        view_id = self.env.ref("hr_planning_resources.create_hr_task_view_form").id

        # Update context with default resource model and default resource ID
        ctx = dict(
            self.env.context,
            default_res_model=self._name,
            default_res_id=self.id,
        )

        # Return the action to open the create HR task form
        return {
            "type": "ir.actions.act_window",
            "res_model": "create.hr.task",
            "view_mode": "form",
            "views": [[view_id, "form"]],
            "context": ctx,
            "target": "new",
        }
