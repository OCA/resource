{
    "name": "Resource Roles and Tags",
    "summary": "Roles and tags describing what generic resources can do.",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "license": "LGPL-3",
    "author": "Daniel Reis, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/resource",
    "depends": ["resource"],
    "data": [
        "security/ir.model.access.csv",
        "views/resource_role_views.xml",
        "views/resource_tag_views.xml",
        "views/resource_resource_views.xml",
    ],
    "demo": ["demo/resource_role_demo.xml"],
    "application": False,
    "installable": True,
}
