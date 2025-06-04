import unittest
from unittest.mock import MagicMock, patch
from app.services.activity_service import ActivityService
from app.models import Activity
from gitlab.v4.objects import ProjectIssue # For mocking

class TestActivityService(unittest.TestCase):

    def setUp(self):
        self.mock_gitlab_service_instance = MagicMock()

        # Patch the 'gitlab_service' instance within 'app.services.activity_service'
        self.gitlab_service_patcher = patch('app.services.activity_service.gitlab_service', self.mock_gitlab_service_instance)
        self.mock_gitlab_service_instance_patched = self.gitlab_service_patcher.start()

        self.activity_service = ActivityService()

        self.mock_gitlab_service_instance_patched.reset_mock()

    def tearDown(self):
        self.gitlab_service_patcher.stop()

    def test_serialize_activity_to_table_row(self):
        activity = Activity(
            project_action_activity="Develop feature X",
            stakeholders="Team Alpha",
            deadline_planned="Q1/2024",
            deadline_achieved="Q1/2024",
            progress_planned_percent=100.0,
            progress_achieved_percent=100.0
        )
        expected_row = "| Develop feature X | Team Alpha | Q1/2024 | Q1/2024 | 100.0% | 100.0% |"
        # The service method is private-like, but for testing its core logic, we call it directly.
        # If it were truly private and complex, we'd test it through the public method.
        self.assertEqual(self.activity_service._serialize_activity_to_table_row(activity), expected_row)

        activity_empty_achieved = Activity(
            project_action_activity="Plan phase 2",
            stakeholders="Product Owner",
            deadline_planned="Q2/2024",
            deadline_achieved=None, # Test None case
            progress_planned_percent=50.0,
            progress_achieved_percent=0.0
        )
        expected_row_empty_achieved = "| Plan phase 2 | Product Owner | Q2/2024 |  | 50.0% | 0.0% |"
        self.assertEqual(self.activity_service._serialize_activity_to_table_row(activity_empty_achieved), expected_row_empty_achieved)

    def test_add_activities_to_kr_description_new_activities(self):
        kr_iid = 1
        mock_kr_issue = MagicMock(spec=ProjectIssue)
        mock_kr_issue.description = "### KR Details\nSome existing content." # Initial description

        self.mock_gitlab_service_instance_patched.get_issue.return_value = mock_kr_issue
        # update_issue doesn't need a specific return value for this test, just verification of call.

        activities_to_add = [
            Activity(project_action_activity="Activity 1", stakeholders="User A", deadline_planned=" Сегодня ", deadline_achieved=None, progress_planned_percent=100.0, progress_achieved_percent=50.0),
            Activity(project_action_activity="Activity 2", stakeholders="User B", deadline_planned=" Завтра ", deadline_achieved=None, progress_planned_percent=100.0, progress_achieved_percent=0.0)
        ]

        expected_row1 = "| Activity 1 | User A |  Сегодня  |  | 100.0% | 50.0% |"
        expected_row2 = "| Activity 2 | User B |  Завтра  |  | 100.0% | 0.0% |"

        # Call the method under test
        updated_description = self.activity_service.add_activities_to_kr_description(kr_iid, activities_to_add)

        self.mock_gitlab_service_instance_patched.get_issue.assert_called_once_with(kr_iid)

        expected_final_description = mock_kr_issue.description.rstrip() + "\n" + expected_row1 + "\n" + expected_row2

        self.mock_gitlab_service_instance_patched.update_issue.assert_called_once_with(
            issue_iid=kr_iid,
            description=expected_final_description
        )
        self.assertEqual(updated_description, expected_final_description)

    def test_add_activities_to_kr_description_empty_initial_description(self):
        kr_iid = 2
        mock_kr_issue = MagicMock(spec=ProjectIssue)
        mock_kr_issue.description = "" # Empty initial description

        self.mock_gitlab_service_instance_patched.get_issue.return_value = mock_kr_issue

        activities_to_add = [
            Activity(project_action_activity="Only Activity", stakeholders="User C", deadline_planned="Q4", deadline_achieved=None, progress_planned_percent=100.0, progress_achieved_percent=10.0)
        ]
        expected_row = "| Only Activity | User C | Q4 |  | 100.0% | 10.0% |"

        updated_description = self.activity_service.add_activities_to_kr_description(kr_iid, activities_to_add)

        # If initial description is empty, new rows are added directly.
        # The service's current logic: updated_description = new_rows_string
        expected_final_description = expected_row

        self.mock_gitlab_service_instance_patched.update_issue.assert_called_once_with(
            issue_iid=kr_iid,
            description=expected_final_description
        )
        self.assertEqual(updated_description, expected_final_description)


if __name__ == '__main__':
    unittest.main()
