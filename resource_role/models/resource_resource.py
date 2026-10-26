# Copyright 2026 Daniel Reis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    role_ids = fields.Many2many(
        comodel_name="resource.role",
        relation="resource_role_resource_rel",
        column1="resource_id",
        column2="role_id",
        string="Roles",
        help="The functions this resource can fulfil.",
    )
    tag_ids = fields.Many2many(
        comodel_name="resource.tag",
        relation="resource_tag_resource_rel",
        column1="resource_id",
        column2="tag_id",
        string="Tags",
        help="Labels classifying this resource.",
    )
