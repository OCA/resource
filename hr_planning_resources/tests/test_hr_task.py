from .common import TestHrPlanningCommon


class TestHrTask(TestHrPlanningCommon):
    def test_00_hr_task_type_task(self):
        # Create a new hr.task
        hr_task_instance = self.create_hr_task()
        self.assertEqual(hr_task_instance.name, "Task")
        self.assertEqual(hr_task_instance.employee_id, self.john_doe_employee)
        self.assertEqual(hr_task_instance.ticket_id.id, False)
        self.assertEqual(hr_task_instance.project_id.id, False)
        self.assertEqual(hr_task_instance.type, "task")
        self.assertEqual(hr_task_instance.task_id, self.task)

    def test_01_hr_task_type_project(self):
        # Create a new hr.task
        hr_task_project = self.create_hr_task("project")
        self.assertEqual(hr_task_project.name, "Project")
        self.assertEqual(hr_task_project.employee_id, self.john_doe_employee)
        self.assertEqual(hr_task_project.project_id, self.project)
        self.assertEqual(hr_task_project.ticket_id.id, False)
        self.assertEqual(hr_task_project.task_id.id, False)

    def test_02_hr_task_type_ticket(self):
        # Create a new hr.task
        hr_task_ticket = self.create_hr_task("ticket")
        self.assertEqual(hr_task_ticket.name, "Ticket")
        self.assertEqual(hr_task_ticket.employee_id, self.john_doe_employee)
        self.assertEqual(hr_task_ticket.ticket_id, self.ticket)
        self.assertEqual(hr_task_ticket.project_id.id, False)
        self.assertEqual(hr_task_ticket.task_id.id, False)
