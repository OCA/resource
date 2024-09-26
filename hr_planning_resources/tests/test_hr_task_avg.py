from . import common


class TestHrTaskAvg(common.HrPlanningResourcesCommon):
    def setUp(self):
        super().setUp()

        # create a new hr.task
        self.hr_task = self.create_hr_task()

    def test_hr_task_avg(self):
        self.hr_task.write({"allocated_hours": 100.0})
        self.assertEqual(self.hr_task.allocated_percentage, 100.0)
        self.hr_task.write({"allocated_hours": 50.0})
        self.assertEqual(self.hr_task.allocated_percentage, 50.0)
