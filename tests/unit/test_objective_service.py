import unittest
from unittest.mock import MagicMock, patch
from app.services.objective_service import ObjectiveService
from app.models import ObjectiveCreateRequest, ObjectiveResponse, GitlabConfig
from app.config import Settings # To override settings for testing
from gitlab.v4.objects import ProjectIssue # For mocking return value of gitlab_service

# Store original settings to restore them later if necessary, though for unit tests
# it's often better to inject/mock config directly if the service uses it.
# However, our services instantiate gitlab_service which itself uses global settings.
# So, we might need to patch settings or the gitlab_service instance within ObjectiveService.

class TestObjectiveService(unittest.TestCase):

    def setUp(self):
        # Create a mock for the global gitlab_service instance used by ObjectiveService
        self.mock_gitlab_service_instance = MagicMock()

        # Patch the 'gitlab_service' instance within the 'app.services.objective_service' module
        # This is where ObjectiveService looks for it.
        self.gitlab_service_patcher = patch('app.services.objective_service.gitlab_service', self.mock_gitlab_service_instance)
        self.mock_gitlab_service_instance_patched = self.gitlab_service_patcher.start()

        # Also, ObjectiveService uses global 'settings' for labels.
        # We can patch 'settings' or ensure the service uses a passed-in config.
        # For this test, let's patch the settings used by the service.
        self.test_settings = Settings(
            gitlab_api_url="https://fakegitlab.com",
            gitlab_access_token="faketoken",
            gitlab_project_id="fakeproject",
            gitlab_objective_labels=["ObjectiveName", "AnotherLabel"], # Test with names
            gitlab_kr_labels=["KRName"]
        )
        self.settings_patcher = patch('app.services.objective_service.settings', self.test_settings)
        self.mock_settings_patched = self.settings_patcher.start()

        # Now, when ObjectiveService is instantiated, it will use the patched gitlab_service and settings
        self.objective_service = ObjectiveService()

        # Reset the mock for each test to ensure clean state for call counts etc.
        self.mock_gitlab_service_instance_patched.reset_mock()


    def tearDown(self):
        self.gitlab_service_patcher.stop()
        self.settings_patcher.stop()

    def test_create_objective_formatting_and_service_call(self):
        # Prepare mock return value for gitlab_service.create_issue
        mock_created_issue = MagicMock(spec=ProjectIssue)
        mock_created_issue.iid = 123
        mock_created_issue.title = "OBJ1: TEST OBJECTIVE UPPERCASE" # Expected title
        mock_created_issue.description = "###  Descrição:\n\n> Test Description\n\n### Resultados Chave" # Expected desc
        mock_created_issue.web_url = "https://fakegitlab.com/fakeproject/issues/123"

        self.mock_gitlab_service_instance_patched.create_issue.return_value = mock_created_issue

        # Input data for creating an objective
        objective_data = ObjectiveCreateRequest(
            obj_number=1,
            title="Test Objective Uppercase", # Service should uppercase this
            description="Test Description"
        )

        # Call the method to test
        response = self.objective_service.create_objective(objective_data)

        # Assertions
        expected_title = "OBJ1: TEST OBJECTIVE UPPERCASE"
        expected_description = "###  Descrição:\n\n> Test Description\n\n### Resultados Chave"

        self.mock_gitlab_service_instance_patched.create_issue.assert_called_once_with(
            title=expected_title,
            description=expected_description,
            labels=self.test_settings.gitlab_objective_labels # Uses names from patched settings
        )

        self.assertIsInstance(response, ObjectiveResponse)
        self.assertEqual(response.id, mock_created_issue.iid)
        self.assertEqual(response.title, mock_created_issue.title)
        # Note: The mock_created_issue.description is already the formatted one.
        # The service's _map_issue_to_objective_response uses issue.description directly.
        self.assertEqual(response.description, mock_created_issue.description)
        self.assertEqual(response.web_url, mock_created_issue.web_url)

    def test_create_objective_title_is_upper_cased(self):
        # Test specifically that the title part from input is uppercased
        mock_created_issue = MagicMock(spec=ProjectIssue)
        mock_created_issue.iid = 124
        mock_created_issue.title = "OBJ2: ANOTHER TEST LOWERCASE" # What create_issue would get
        mock_created_issue.description = "..."
        mock_created_issue.web_url = "http://..."
        self.mock_gitlab_service_instance_patched.create_issue.return_value = mock_created_issue

        objective_data = ObjectiveCreateRequest(
            obj_number=2,
            title="another test lowercase", # Input with lowercase
            description="desc"
        )
        self.objective_service.create_objective(objective_data)

        args, kwargs = self.mock_gitlab_service_instance_patched.create_issue.call_args
        self.assertEqual(kwargs['title'], "OBJ2: ANOTHER TEST LOWERCASE")


if __name__ == '__main__':
    unittest.main()
