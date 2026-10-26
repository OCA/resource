# Copyright 2026 Daniel Reis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ResourceTag(models.Model):
    """Free-form labels on resources — certifications, regions,
    equipment classes and other classifications beyond roles."""

    _name = "resource.tag"
    _description = "Resource Tag"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    color = fields.Integer()
    resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="resource_tag_resource_rel",
        column1="tag_id",
        column2="resource_id",
        string="Resources",
    )
    resource_count = fields.Integer(compute="_compute_resource_count")

    @api.depends("resource_ids")
    def _compute_resource_count(self):
        for tag in self:
            tag.resource_count = len(tag.resource_ids)

    def action_view_resources(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "resource.action_resource_resource_tree"
        )
        action["domain"] = [("tag_ids", "in", self.ids)]
        action["context"] = {"default_tag_ids": [fields.Command.set(self.ids)]}
        return action
