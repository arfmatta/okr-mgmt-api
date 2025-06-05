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
        self.test_settings = Settings(
            gitlab_api_url="https://fakegitlab.com",
            gitlab_access_token="faketoken",
            gitlab_project_id="fakeproject",
            gitlab_objective_labels=["2025", "OKR SUTI", "OKR::Objetivo", "OKR::Q2"],
            gitlab_kr_labels=["2025", "OKR SUTI", "OKR::Resultado Chave", "OKR::Q2"]
        )
        self.settings_patcher = patch('app.config.settings', self.test_settings)
        self.mock_settings_patched = self.settings_patcher.start()
        self.objective_service = ObjectiveService()
        # Injete explicitamente o mock na instância do serviço
        self.objective_service.gitlab_service = self.mock_gitlab_service_instance
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
            description="Test Description",
            team_label="TeamX",
            product_label="ProductY"
        )

        response = self.objective_service.create_objective(objective_data)

        expected_title = "OBJ1: TEST OBJECTIVE UPPERCASE"
        expected_description = "###  Descrição:\n\n> Test Description\n\n### Resultados Chave"
        # Monte o valor esperado de labels conforme a lógica do serviço
        expected_labels = self.test_settings.gitlab_objective_labels + [objective_data.team_label, objective_data.product_label]

        # Verifique a chamada ignorando a ordem dos labels
        self.mock_gitlab_service_instance_patched.create_issue.assert_called_once()
        args, kwargs = self.mock_gitlab_service_instance_patched.create_issue.call_args
        self.assertEqual(kwargs['title'], expected_title)
        self.assertEqual(kwargs['description'], expected_description)
        self.assertCountEqual(kwargs['labels'], expected_labels)

        self.assertIsInstance(response, ObjectiveResponse)
        self.assertEqual(response.id, mock_created_issue.iid)
        self.assertEqual(response.title, mock_created_issue.title)
        self.assertEqual(response.description, mock_created_issue.description)
        self.assertEqual(str(response.web_url), str(mock_created_issue.web_url))

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
            description="desc",
            team_label="TeamX",
            product_label="ProductY"
        )
        self.objective_service.create_objective(objective_data)

        args, kwargs = self.mock_gitlab_service_instance_patched.create_issue.call_args
        # The 'title' kwarg passed to the mock should be the fully formatted one.
        self.assertEqual(kwargs['title'], "OBJ2: ANOTHER TEST LOWERCASE")

if __name__ == '__main__':
    unittest.main()
