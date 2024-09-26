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
                "user_id": self.john_doe_user.id,
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
                "user_id": self.env.ref("base.user_admin").id,
                "user_ids": [(4, self.john_doe_user.id)],
                "date_start": "2024-09-01",
                "date_end": "2022-10-31",
            }
        )

        # create a new task
        self.task = self.env["hr.task"].create(
            {
                "name": "Task",
                "employee_id": self.john_doe_employee.id,
                "project_id": self.project.id,
                "date_start": "2024-09-01",
                "date_end": "2024-10-31",
            }
        )

        # create a new ticket
        self.ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Ticket",
                "user_id": self.john_doe_user.id,
                "user_ids": [(4, self.john_doe_user.id)],
                "date_start": "2024-09-01",
                "date_end": "2022-10-31",
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
                "date_start": "2024-09-01",
                "date_end": "2024-10-31",
            }
        )
