from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    task_generation_interval = fields.Integer(
        "Rate Of Shift Generation", default=1, required=True
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    task_generation_interval = fields.Integer(
        "Rate Of Shift Generation",
        required=True,
        related="company_id.task_generation_interval",
        readonly=False,
    )
