# Copyright 2026 Daniel Reis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_resource_location = fields.Boolean(
        string="Resource Location",
        index=True,
        help="Mark this partner as a site where resources operate. "
        "Shared by apps such as Resource Reservation and Resource "
        "Planning; its address and timezone are used by "
        "location-aware features.",
    )
    sequence = fields.Integer(
        default=10,
        help="Ordering for location dashboards and configuration lists.",
    )
