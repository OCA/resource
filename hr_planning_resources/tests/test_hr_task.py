from .common import TestHrPlanningCommon


class TestHrTask(TestHrPlanningCommon):
    def test_00_hr_task_type_task(self):
        # Create a new hr.task
        hr_task_instance = self.create_hr_task()
        self.assertEqual(hr_task_instance.name, "")
        self.assertEqual(hr_task_instance.employee_id, False)
        self.assertEqual(hr_task_instance.project_id, False)
        self.assertEqual(hr_task_instance.type, "task")
        self.assertEqual(hr_task_instance.task, self.task)
        self.assertEqual(hr_task_instance.date_start, False)
        self.assertEqual(hr_task_instance.date_end, False)
        self.assertEqual(hr_task_instance.planned_hours, 0.0)
        self.assertEqual(hr_task_instance.allocated_hours, 0.0)
        self.assertEqual(hr_task_instance.allocated_percentage, 100.0)
        self.assertEqual(hr_task_instance.working_days_count, 0.0)
        self.assertEqual(hr_task_instance.duration, 0.0)

    def test_01_hr_task_type_project(self):
        # Create a new hr.task
        hr_task_project = self.create_hr_task("project")
        self.assertEqual(hr_task_project.name, "Project")
        self.assertEqual(hr_task_project.employee_id, self.john_doe_employee)
        self.assertEqual(hr_task_project.project_id, self.project)
        self.assertEqual(hr_task_project.task_id, False)
        self.assertEqual(hr_task_project.ticket_id, False)
        self.assertEqual(hr_task_project.date_start, "2024-09-01")
        self.assertEqual(hr_task_project.date_end, "2024-10-31")

    def test_02_hr_task_type_ticket(self):
        # Create a new hr.task
        hr_task_ticket = self.create_hr_task("ticket")
        self.assertEqual(hr_task_ticket.name, "Task")
        self.assertEqual(hr_task_ticket.employee_id, self.john_doe_employee)
        self.assertEqual(hr_task_ticket.project_id, False)
        self.assertEqual(hr_task_ticket.task_id, False)
        self.assertEqual(hr_task_ticket.ticket_id, self.ticket)
        self.assertEqual(hr_task_ticket.date_start, "2024-09-01")
        self.assertEqual(hr_task_ticket.date_end, "2024-10-31")
