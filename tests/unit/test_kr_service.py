import unittest
from unittest.mock import MagicMock, patch, call
import re # For verifying appended KR reference in objective's description

from app.services.kr_service import KRService
from app.models import KRCreateRequest, KRResponse # Removed GitlabConfig
from app.config import Settings # Import Settings to create test_settings instance
from gitlab.v4.objects import ProjectIssue

class TestKRService(unittest.TestCase):

    def setUp(self):
        self.mock_gitlab_service_instance = MagicMock()

        self.gitlab_service_patcher = patch('app.services.kr_service.gitlab_service', self.mock_gitlab_service_instance)
        self.mock_gitlab_service_patched = self.gitlab_service_patcher.start()

        # Instantiate Settings with string values for labels, mimicking .env loading
        # The Settings class itself will parse these strings into lists.
        self.test_settings = Settings(
            gitlab_api_url="https://fakegitlab.com",
            gitlab_access_token="faketoken",
            gitlab_project_id="fakeproject",
            # Pass raw strings for fields that have @field_validator(mode='before')
            # Pydantic-settings maps GITLAB_OBJECTIVE_LABELS (env var) to gitlab_objective_labels (field)
            # So, we provide the string to the field directly for the validator to process.
            gitlab_objective_labels="Objective",
            gitlab_kr_labels="KRLabelName"
        )
        # Patch 'settings' instance in app.config where it's defined and globally used.
        self.settings_patcher = patch('app.config.settings', self.test_settings)
        self.mock_settings_patched = self.settings_patcher.start()

        self.kr_service = KRService() # KRService will now use the patched app.config.settings

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
        # Use the service's own formatter for expected description
        # Need to create a dummy KRCreateRequest that _format_kr_description would expect
        temp_kr_data_for_formatting = KRCreateRequest(objective_iid=10,kr_number=1,title="New KR Title",description="KR details here",meta_prevista=100.0,responsaveis=["User One", "User Two"])
        mock_created_kr.description = self.kr_service._format_kr_description(temp_kr_data_for_formatting)
        mock_created_kr.web_url = "https://fakegitlab.com/fakeproject/issues/101"

        self.mock_gitlab_service_patched.get_issue.return_value = mock_parent_objective
        self.mock_gitlab_service_patched.create_issue.return_value = mock_created_kr

        kr_data = KRCreateRequest(
            objective_iid=10,
            kr_number=1,
            title="New KR Title",
            description="KR details here",
            meta_prevista=100.0,
            meta_realizada=0.0,
            responsaveis=["User One", "User Two"]
        )

        response = self.kr_service.create_kr(kr_data)

        self.mock_gitlab_service_patched.get_issue.assert_any_call(kr_data.objective_iid)
        self.assertEqual(self.mock_gitlab_service_patched.get_issue.call_count, 2)

        expected_kr_title_on_create = "OBJ1 - KR1: New KR Title"
        expected_kr_description_on_create = self.kr_service._format_kr_description(kr_data)

        # self.test_settings.gitlab_kr_labels should now be a list, e.g., ["KRLabelName"]
        # after parsing by the Settings model.
        self.mock_gitlab_service_patched.create_issue.assert_called_once_with(
            title=expected_kr_title_on_create,
            description=expected_kr_description_on_create,
            labels=self.test_settings.gitlab_kr_labels
        )

        self.mock_gitlab_service_patched.link_issues.assert_called_once_with(
            source_issue_iid=mock_created_kr.iid,
            target_issue_iid=mock_parent_objective.iid
        )

        self.mock_gitlab_service_patched.update_issue.assert_called_once()
        args_update, kwargs_update = self.mock_gitlab_service_patched.update_issue.call_args
        self.assertEqual(kwargs_update['issue_iid'], mock_parent_objective.iid)

        updated_obj_description = kwargs_update['description']
        expected_kr_ref_line = f"- [ ] **{expected_kr_title_on_create}** ~\"{self.kr_service.kr_reference_label}\""

        original_part_before_kr_section = "Initial objective description.\n\n"
        kr_section_header = "### Resultados Chave"
        original_krs_in_section = "- [ ] Some existing KR"

        expected_obj_desc_updated = original_part_before_kr_section + kr_section_header + "\n" + \
                                    expected_kr_ref_line + "\n" + \
                                    original_krs_in_section

        self.assertEqual(updated_obj_description.strip(), expected_obj_desc_updated.strip())

        self.assertIsInstance(response, KRResponse)
        self.assertEqual(response.id, mock_created_kr.iid)
        self.assertEqual(response.title, mock_created_kr.title)
        self.assertEqual(response.objective_iid, mock_parent_objective.iid)

    def test_create_kr_parent_objective_title_parsing_fallback(self):
        mock_parent_objective_bad_title = MagicMock(spec=ProjectIssue)
        mock_parent_objective_bad_title.iid = 20
        mock_parent_objective_bad_title.title = "Objective Without Standard Prefix"
        mock_parent_objective_bad_title.description = "Desc"

        expected_kr_title_fallback = f"OBJ{mock_parent_objective_bad_title.iid} - KR2: Fallback KR"

        mock_created_kr_fallback = MagicMock(spec=ProjectIssue)
        mock_created_kr_fallback.iid = 102
        mock_created_kr_fallback.title = expected_kr_title_fallback
        # For description consistency, create a dummy KRCreateRequest
        temp_kr_data_for_fallback_formatting = KRCreateRequest(
            objective_iid=20, kr_number=2, title="Fallback KR", description="d",
            meta_prevista=1.0, responsaveis=[]
        )
        mock_created_kr_fallback.description = self.kr_service._format_kr_description(temp_kr_data_for_fallback_formatting)
        mock_created_kr_fallback.web_url = "http://..."

        self.mock_gitlab_service_patched.get_issue.return_value = mock_parent_objective_bad_title
        self.mock_gitlab_service_patched.create_issue.return_value = mock_created_kr_fallback

        kr_data = KRCreateRequest(
            objective_iid=20, kr_number=2, title="Fallback KR", description="d",
            meta_prevista=1.0, responsaveis=[]
        )

        response = self.kr_service.create_kr(kr_data)

        args_create, kwargs_create = self.mock_gitlab_service_patched.create_issue.call_args
        self.assertEqual(kwargs_create['title'], expected_kr_title_fallback)

        args_update, kwargs_update = self.mock_gitlab_service_patched.update_issue.call_args
        updated_obj_desc = kwargs_update['description']

        expected_kr_ref_line_fallback = f"- [ ] **{expected_kr_title_fallback}** ~\"{self.kr_service.kr_reference_label}\""
        expected_full_obj_desc = mock_parent_objective_bad_title.description + \
                                 "\n\n### Resultados Chave\n" + \
                                 expected_kr_ref_line_fallback + "\n"
        self.assertEqual(updated_obj_desc.strip(), expected_full_obj_desc.strip())

        self.assertEqual(response.title, expected_kr_title_fallback)

if __name__ == '__main__':
    unittest.main()
