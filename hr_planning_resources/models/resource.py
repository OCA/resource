from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    flexible_hours = fields.Boolean()
