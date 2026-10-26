{
    "name": "Resource Location",
    "summary": "Resource locations and resource presence lines — shared "
    "location concept for reservations and service planning",
    "version": "19.0.1.0.0",
    "development_status": "Alpha",
    "category": "Services",
    "website": "https://github.com/OCA/resource",
    "author": "Daniel Reis, Odoo Community Association (OCA)",
    "maintainers": ["dreispt"],
    "license": "LGPL-3",
    "installable": True,
    "depends": ["resource"],
    "data": [
        "security/ir.model.access.csv",
        "views/resource_resource_views.xml",
        "views/res_partner_views.xml",
    ],
    "demo": ["demo/resource_location_demo.xml"],
}
