import unittest
from unittest.mock import MagicMock, patch, call
import re # For verifying appended KR reference in objective's description

from app.services.kr_service import KRService
from app.models import KRCreateRequest, KRResponse, GitlabConfig
from app.config import Settings
from gitlab.v4.objects import ProjectIssue

class TestKRService(unittest.TestCase):

    def setUp(self):
        self.mock_gitlab_service_instance = MagicMock()

        self.gitlab_service_patcher = patch('app.services.kr_service.gitlab_service', self.mock_gitlab_service_instance)
        self.mock_gitlab_service_patched = self.gitlab_service_patcher.start()

        self.test_settings = Settings(
            gitlab_api_url="https://fakegitlab.com",
            gitlab_access_token="faketoken",
            gitlab_project_id="fakeproject",
            gitlab_objective_labels=["Objective"],
            gitlab_kr_labels=["KRLabelName"] # Test with names
        )
        self.settings_patcher = patch('app.services.kr_service.settings', self.test_settings)
        self.mock_settings_patched = self.settings_patcher.start()

        self.kr_service = KRService()

        self.mock_gitlab_service_patched.reset_mock()

    def tearDown(self):
        self.gitlab_service_patcher.stop()
        self.settings_patcher.stop()

    def test_create_kr_full_logic(self):
        # --- Mocking Parent Objective ---
        mock_parent_objective = MagicMock(spec=ProjectIssue)
        mock_parent_objective.iid = 10
        mock_parent_objective.title = "OBJ1: Parent Objective Title"
        # Initial description of the parent objective
        mock_parent_objective.description = "Initial objective description.\n\n### Resultados Chave\n- [ ] Some existing KR"

        # --- Mocking Created KR Issue ---
        mock_created_kr = MagicMock(spec=ProjectIssue)
        mock_created_kr.iid = 101
        # Title below is what gitlab_service.create_issue would get after formatting by KRService
        mock_created_kr.title = "OBJ1 - KR1: New KR Title"
        # Description below is what gitlab_service.create_issue would get after formatting by KRService
        # This must match EXACTLY what _format_kr_description in KRService produces
        mock_created_kr.description = (
            "### Descrição\n\n"
            "> KR details here\n\n"  # Assuming input "KR details here"
            "**Meta prevista**: 100.0%  \n"
            "**Meta realizada**: 0.0%  \n"
            "**Responsável(eis)**: User One, User Two  \n\n"
            "| Projetos/Ações/Atividades | Partes interessadas | Prazo Previsto | Prazo Realizado | % Previsto | % Realizado |\n"
            "|---------------------------|----------------------|----------------|-----------------|------------|-------------|\n"
            "|                           |                      |                |                 |            |             |"
        )
        mock_created_kr.web_url = "https://fakegitlab.com/fakeproject/issues/101"

        # Configure mocks for gitlab_service calls
        # get_issue is called twice by create_kr: once in _get_objective_prefix, once before updating description
        self.mock_gitlab_service_patched.get_issue.return_value = mock_parent_objective
        self.mock_gitlab_service_patched.create_issue.return_value = mock_created_kr
        # update_issue and link_issues don't need specific return values for this test logic

        # --- Input KR Data ---
        kr_data = KRCreateRequest(
            objective_iid=10,
            kr_number=1,
            title="New KR Title",
            description="KR details here", # This will be quoted by the service
            meta_prevista=100.0,
            meta_realizada=0.0,
            responsaveis=["User One", "User Two"]
        )

        # --- Call the method under test ---
        response = self.kr_service.create_kr(kr_data)

        # --- Assertions ---
        # 1. Assert get_issue (for parent objective) was called.
        # Called first by _get_objective_prefix, then by create_kr before update.
        self.mock_gitlab_service_patched.get_issue.assert_any_call(kr_data.objective_iid)
        self.assertEqual(self.mock_gitlab_service_patched.get_issue.call_count, 2)


        # 2. Assert create_issue (for new KR) was called with correct parameters
        # The title is formatted by KRService based on objective prefix and KR data
        expected_kr_title_on_create = "OBJ1 - KR1: New KR Title"
        # The description is formatted by KRService's _format_kr_description
        expected_kr_description_on_create = self.kr_service._format_kr_description(kr_data) # Use service's own formatter for expected

        self.mock_gitlab_service_patched.create_issue.assert_called_once_with(
            title=expected_kr_title_on_create,
            description=expected_kr_description_on_create,
            labels=self.test_settings.gitlab_kr_labels # Names from settings
        )

        # 3. Assert link_issues was called correctly (KR links to Objective)
        self.mock_gitlab_service_patched.link_issues.assert_called_once_with(
            source_issue_iid=mock_created_kr.iid, # KR is source
            target_issue_iid=mock_parent_objective.iid # Objective is target
        )

        # 4. Assert update_issue (for parent objective's description) was called
        self.mock_gitlab_service_patched.update_issue.assert_called_once()
        args_update, kwargs_update = self.mock_gitlab_service_patched.update_issue.call_args
        self.assertEqual(kwargs_update['issue_iid'], mock_parent_objective.iid)

        updated_obj_description = kwargs_update['description']

        # Construct the expected KR reference line using the KR title that was sent to create_issue
        # and the hardcoded reference label from the service.
        expected_kr_ref_line = f"- [ ] **{expected_kr_title_on_create}** ~\"{self.kr_service.kr_reference_label}\""

        # Check if the original description part is preserved and the new KR is appended correctly
        # under "### Resultados Chave"
        original_part_before_kr_section = "Initial objective description.\n\n"
        kr_section_header = "### Resultados Chave"
        original_krs_in_section = "- [ ] Some existing KR" # from mock_parent_objective.description

        # Expected structure:
        # original_part_before_kr_section + kr_section_header + "\n" + new_kr_ref_line + "\n" + original_krs_in_section (if any, and logic handles it)
        # The service logic is: parts[0] + "### Resultados Chave\n" + kr_reference_line + "\n" + parts[1].strip()
        # So it should be:
        expected_obj_desc_updated = original_part_before_kr_section + kr_section_header + "\n" + \
                                    expected_kr_ref_line + "\n" + \
                                    original_krs_in_section # This assumes original_krs_in_section is what parts[1].strip() would be

        self.assertEqual(updated_obj_description.strip(), expected_obj_desc_updated.strip())


        # 5. Assert response object
        self.assertIsInstance(response, KRResponse)
        self.assertEqual(response.id, mock_created_kr.iid)
        # The title in response should be the one from the created KR issue object
        self.assertEqual(response.title, mock_created_kr.title)
        self.assertEqual(response.objective_iid, mock_parent_objective.iid)

    def test_create_kr_parent_objective_title_parsing_fallback(self):
        mock_parent_objective_bad_title = MagicMock(spec=ProjectIssue)
        mock_parent_objective_bad_title.iid = 20
        mock_parent_objective_bad_title.title = "Objective Without Standard Prefix"
        mock_parent_objective_bad_title.description = "Desc" # No KR section

        # Expected KR title using fallback: OBJ<objective_iid> - KR<kr_number>: <title>
        expected_kr_title_fallback = f"OBJ{mock_parent_objective_bad_title.iid} - KR2: Fallback KR"

        mock_created_kr_fallback = MagicMock(spec=ProjectIssue)
        mock_created_kr_fallback.iid = 102
        mock_created_kr_fallback.title = expected_kr_title_fallback # This title is set on the mock returned by create_issue
        mock_created_kr_fallback.description = "..." # Formatted by _format_kr_description
        mock_created_kr_fallback.web_url = "http://..."

        self.mock_gitlab_service_patched.get_issue.return_value = mock_parent_objective_bad_title
        self.mock_gitlab_service_patched.create_issue.return_value = mock_created_kr_fallback

        kr_data = KRCreateRequest(
            objective_iid=20,
            kr_number=2,
            title="Fallback KR",
            description="d",
            meta_prevista=1.0,
            responsaveis=[]
        )

        response = self.kr_service.create_kr(kr_data)

        # Check that the KR title passed to create_issue used the fallback prefix
        args_create, kwargs_create = self.mock_gitlab_service_patched.create_issue.call_args
        self.assertEqual(kwargs_create['title'], expected_kr_title_fallback)

        # Check that the objective description update also used the fallback prefix for the KR entry
        args_update, kwargs_update = self.mock_gitlab_service_patched.update_issue.call_args
        updated_obj_desc = kwargs_update['description']

        expected_kr_ref_line_fallback = f"- [ ] **{expected_kr_title_fallback}** ~\"{self.kr_service.kr_reference_label}\""
        # Since original description "Desc" does not have "### Resultados Chave"
        # The service appends: "\n\n### Resultados Chave\n" + kr_reference_line + "\n"
        expected_full_obj_desc = mock_parent_objective_bad_title.description + \
                                 "\n\n### Resultados Chave\n" + \
                                 expected_kr_ref_line_fallback + "\n"
        self.assertEqual(updated_obj_desc.strip(), expected_full_obj_desc.strip())

        # The response title should be what was on the mock_created_kr_fallback
        self.assertEqual(response.title, expected_kr_title_fallback)


if __name__ == '__main__':
    unittest.main()
