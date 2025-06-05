import unittest
from unittest.mock import MagicMock, patch
from app.services.objective_service import ObjectiveService
from app.models import ObjectiveCreateRequest, ObjectiveResponse
# Removed GitlabConfig as it's not used by the service directly in tests
from app.config import Settings # Import Settings to create test_settings instance
from gitlab.v4.objects import ProjectIssue

class TestObjectiveService(unittest.TestCase):

    def setUp(self):
        self.mock_gitlab_service_instance = MagicMock()

        self.gitlab_service_patcher = patch('app.services.objective_service.gitlab_service', self.mock_gitlab_service_instance)
        self.mock_gitlab_service_instance_patched = self.gitlab_service_patcher.start()

        # Instantiate Settings with string values for the fields that have validators,
        # mimicking how these values would be loaded from .env before parsing.
        self.test_settings = Settings(
            gitlab_api_url="https://fakegitlab.com",
            gitlab_access_token="faketoken",
            gitlab_project_id="fakeproject",
            # Pass the raw comma-separated string to the actual field name
            # The @field_validator in Settings will parse this.
            gitlab_objective_labels="ObjectiveName,AnotherLabel",
            gitlab_kr_labels="KRName"
        )
        # Patch 'settings' in app.config where it's defined and globally used.
        self.settings_patcher = patch('app.config.settings', self.test_settings)
        self.mock_settings_patched = self.settings_patcher.start()

        self.objective_service = ObjectiveService() # ObjectiveService will use the patched app.config.settings

        self.mock_gitlab_service_instance_patched.reset_mock()

    def tearDown(self):
        self.gitlab_service_patcher.stop()
        self.settings_patcher.stop()

    def test_create_objective_formatting_and_service_call(self):
        mock_created_issue = MagicMock(spec=ProjectIssue)
        mock_created_issue.iid = 123
        mock_created_issue.title = "OBJ1: TEST OBJECTIVE UPPERCASE"
        mock_created_issue.description = "###  Descrição:\n\n> Test Description\n\n### Resultados Chave"
        mock_created_issue.web_url = "https://fakegitlab.com/fakeproject/issues/123"

        self.mock_gitlab_service_instance_patched.create_issue.return_value = mock_created_issue

        objective_data = ObjectiveCreateRequest(
            obj_number=1,
            title="Test Objective Uppercase",
            description="Test Description"
        )

        response = self.objective_service.create_objective(objective_data)

        expected_title = "OBJ1: TEST OBJECTIVE UPPERCASE"
        expected_description = "###  Descrição:\n\n> Test Description\n\n### Resultados Chave"

        # ObjectiveService uses self.test_settings (which is the patched global settings).
        # The labels in self.test_settings will be the *parsed list* due to Settings model's own validation.
        self.mock_gitlab_service_instance_patched.create_issue.assert_called_once_with(
            title=expected_title,
            description=expected_description,
            labels=self.test_settings.gitlab_objective_labels # This should be ["ObjectiveName", "AnotherLabel"]
        )

        self.assertIsInstance(response, ObjectiveResponse)
        self.assertEqual(response.id, mock_created_issue.iid)
        self.assertEqual(response.title, mock_created_issue.title)
        self.assertEqual(response.description, mock_created_issue.description)
        self.assertEqual(response.web_url, mock_created_issue.web_url)

    def test_create_objective_title_is_upper_cased(self):
        mock_created_issue = MagicMock(spec=ProjectIssue)
        mock_created_issue.iid = 124
        # This title is what create_issue would be called with by the service
        mock_created_issue.title = "OBJ2: ANOTHER TEST LOWERCASE"
        mock_created_issue.description = "..."
        mock_created_issue.web_url = "http://..."
        self.mock_gitlab_service_instance_patched.create_issue.return_value = mock_created_issue

        objective_data = ObjectiveCreateRequest(
            obj_number=2,
            title="another test lowercase",
            description="desc"
        )
        self.objective_service.create_objective(objective_data)

        args, kwargs = self.mock_gitlab_service_instance_patched.create_issue.call_args
        # The 'title' kwarg passed to the mock should be the fully formatted one.
        self.assertEqual(kwargs['title'], "OBJ2: ANOTHER TEST LOWERCASE")

if __name__ == '__main__':
    unittest.main()
