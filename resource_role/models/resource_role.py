# Copyright 2026 Daniel Reis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ResourceServiceRole(models.Model):
    """Planning role, such as technician, supervisor, operator or driver.

    Roles describe the function a resource is expected to fulfil. They
    are not HR job positions.
    """

    _name = "resource.role"
    _description = "Resource Role"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    color = fields.Integer()
    description = fields.Text()
    resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="resource_role_resource_rel",
        column1="role_id",
        column2="resource_id",
        string="Resources",
        help="Resources declared as able to fulfil this role.",
    )
    resource_count = fields.Integer(compute="_compute_resource_count")

    @api.depends("resource_ids")
    def _compute_resource_count(self):
        for role in self:
            role.resource_count = len(role.resource_ids)

    def action_view_resources(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "resource.action_resource_resource_tree"
        )
        action["domain"] = [("role_ids", "in", self.ids)]
        action["context"] = {"default_role_ids": [fields.Command.set(self.ids)]}
        return action
