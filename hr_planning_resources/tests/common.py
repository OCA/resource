from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestHrPlanningCommon(common.TransactionCase):
    def setUp(self):
        super().setUp()

        # create a new user
        self.john_doe_user = self.env["res.users"].create(
            {
                "name": "John Doe",
                "login": "test_user",
                "email": "test_user@example.com",
                "password": "test_password",
                "company_id": self.env.ref("base.main_company").id,
            }
        )
        # create a new department
        self.department = self.env["hr.department"].create(
            {
                "name": "Department",
            }
        )
        # create a new employee
        self.john_doe_employee = self.env["hr.employee"].create(
            {
                "name": "John Doe",
                "user_id": self.john_doe_user.id,
                "department_id": self.department.id,
            }
        )

        # create a new project
        self.project = self.env["project.project"].create(
            {
                "name": "Project",
                "user_id": self.john_doe_user.id,
                "date_start": fields.Date.today(),
            }
        )

        # create a new task
        self.task = self.env["project.task"].create(
            {
                "name": "Task",
                "user_ids": [Command.link(self.john_doe_user.id)],
                "project_id": self.project.id,
                "date_assign": fields.Datetime.now(),
                "date_deadline": fields.Datetime.now() + relativedelta(days=1),
            }
        )

        # Create a new helpdesk.team
        self.helpdesk_team = self.env["helpdesk.ticket.team"].create(
            {
                "name": "Team",
                "user_ids": [Command.link(self.john_doe_user.id)],
            }
        )

        # create a new ticket
        self.ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Ticket",
                "user_id": self.john_doe_user.id,
                "team_id": self.helpdesk_team.id,
                "description": "Ticket description",
            }
        )

    def create_hr_task(self, ttype="task"):
        # Create a new hr.taskk
        name = "Task"
        if ttype == "project":
            name = "Project"
        elif ttype == "ticket":
            name = "Ticket"

        return self.env["hr.task"].create(
            {
                "name": name,
                "employee_id": self.john_doe_employee.id,
                "project_id": (self.project.id if ttype == "project" else False),
                "task_id": self.task.id if ttype == "task" else False,
                "ticket_id": self.ticket.id if ttype == "ticket" else False,
                "type": ttype,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now() + relativedelta(days=1),
            }
        )
