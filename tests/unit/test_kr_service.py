import unittest
from unittest.mock import MagicMock, patch, call
import re # For verifying appended KR reference in objective's description

from app.services.kr_service import KRService
from app.models import KRCreateRequest, KRResponse, KRUpdateRequest # Added KRUpdateRequest
from app.config import Settings # Import Settings to create test_settings instance
from gitlab.v4.objects import ProjectIssue
from gitlab.exceptions import GitlabGetError # Added for test_update_kr_not_found

class TestKRService(unittest.TestCase):

    def setUp(self):
        # Crie um mock explícito para cada método usado
        self.mock_gitlab_service_instance = MagicMock(spec=[
            "get_issue",
            "create_issue",
            "link_issues",
            "update_issue"
        ])
        # Patch o gitlab_service no local correto
        gitlab_service_patcher = patch('app.services.kr_service.gitlab_service', self.mock_gitlab_service_instance)
        self.gitlab_service_patcher = gitlab_service_patcher
        self.mock_gitlab_service_patched = gitlab_service_patcher.start()

        self.test_settings = Settings(
            gitlab_api_url="https://fakegitlab.com",
            gitlab_access_token="faketoken",
            gitlab_project_id="fakeproject",
            gitlab_objective_labels=["2025", "OKR SUTI", "OKR::Objetivo", "OKR::Q2"],
            gitlab_kr_labels=["2025", "OKR SUTI", "OKR::Resultado Chave", "OKR::Q2"]
        )
        # Patch 'settings' instance em app.config
        settings_patcher = patch('app.config.settings', self.test_settings)
        self.settings_patcher = settings_patcher
        self.mock_settings_patched = settings_patcher.start()

        self.kr_service = KRService()
        # Injete explicitamente o mock na instância do serviço
        self.kr_service.gitlab_service = self.mock_gitlab_service_instance

        # Limpe o mock para garantir que não há chamadas anteriores
        self.mock_gitlab_service_instance.reset_mock()

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
        temp_kr_data_for_formatting = KRCreateRequest(
            objective_iid=10,
            kr_number=1,
            title="New KR Title",
            description="KR details here",
            meta_prevista=100.0,
            responsaveis=["User One", "User Two"],
            team_label="TeamX",
            product_label="ProductY"
        )
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
            responsaveis=["User One", "User Two"],
            team_label="TeamX",
            product_label="ProductY"
        )

        response = self.kr_service.create_kr(kr_data)

        self.mock_gitlab_service_patched.get_issue.assert_any_call(kr_data.objective_iid)
        self.assertEqual(self.mock_gitlab_service_patched.get_issue.call_count, 2)

        expected_kr_title_on_create = "OBJ1 - KR1: New KR Title"
        expected_kr_description_on_create = self.kr_service._format_kr_description(kr_data)

        # Monte o valor esperado de labels conforme a lógica do serviço
        expected_labels = self.test_settings.gitlab_kr_labels + [kr_data.team_label, kr_data.product_label]

        # Verifique a chamada ignorando a ordem dos labels
        self.mock_gitlab_service_patched.create_issue.assert_called_once()
        args, kwargs = self.mock_gitlab_service_patched.create_issue.call_args
        self.assertEqual(kwargs['title'], expected_kr_title_on_create)
        self.assertEqual(kwargs['description'], expected_kr_description_on_create)
        self.assertCountEqual(kwargs['labels'], expected_labels)

        self.mock_gitlab_service_patched.link_issues.assert_called_once_with(
            source_issue_iid=mock_created_kr.iid,
            target_issue_iid=mock_parent_objective.iid
        )

        self.mock_gitlab_service_patched.update_issue.assert_called_once()
        args_update, kwargs_update = self.mock_gitlab_service_patched.update_issue.call_args
        self.assertEqual(kwargs_update['issue_iid'], mock_parent_objective.iid)

        updated_obj_description = kwargs_update['description']
        # Corrija o formato esperado para refletir o real (dois pontos e título dentro do negrito)
        expected_kr_ref_line = f"- [ ] **OBJ1 - KR1**: New KR Title ~\"{self.kr_service.kr_reference_label}\""

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
            objective_iid=20,
            kr_number=2,
            title="Fallback KR",
            description="d",
            meta_prevista=1.0,
            responsaveis=[],
            team_label="TeamX",
            product_label="ProductY"
        )
        mock_created_kr_fallback.description = self.kr_service._format_kr_description(temp_kr_data_for_fallback_formatting)
        mock_created_kr_fallback.web_url = "http://..."

        self.mock_gitlab_service_patched.get_issue.return_value = mock_parent_objective_bad_title
        self.mock_gitlab_service_patched.create_issue.return_value = mock_created_kr_fallback

        kr_data = KRCreateRequest(
            objective_iid=20,
            kr_number=2,
            title="Fallback KR",
            description="d",
            meta_prevista=1.0,
            responsaveis=[],
            team_label="TeamX",
            product_label="ProductY"
        )

        response = self.kr_service.create_kr(kr_data)

        args_create, kwargs_create = self.mock_gitlab_service_patched.create_issue.call_args
        self.assertEqual(kwargs_create['title'], expected_kr_title_fallback)

        args_update, kwargs_update = self.mock_gitlab_service_patched.update_issue.call_args
        updated_obj_desc = kwargs_update['description']

        expected_kr_ref_line_fallback = f"- [ ] **OBJ20 - KR2**: Fallback KR ~\"{self.kr_service.kr_reference_label}\""
        expected_full_obj_desc = mock_parent_objective_bad_title.description + \
                                 "\n\n### Resultados Chave\n" + \
                                 expected_kr_ref_line_fallback + "\n"
        self.assertEqual(updated_obj_desc.strip(), expected_full_obj_desc.strip())

        self.assertEqual(response.title, expected_kr_title_fallback)

    def test_update_kr_all_fields_success(self):
        NL = '\n'
        kr_iid = 123
        original_description_text = "Original detailed description."
        original_meta_prevista = 50.0
        original_meta_realizada = 10.0
        original_responsaveis = ["User Alpha", "User Beta"]
        activities_table_content = (
            "| Projetos/Ações/Atividades | Partes interessadas | Prazo Previsto | Prazo Realizado | % Previsto | % Realizado |\n"
            "|---------------------------|----------------------|----------------|-----------------|------------|-------------|\n"
            "| Action 1                  | Stakeholder A        | Q1/2024        |                 | 100        | 0           |"
        )

        mock_current_issue = MagicMock(spec=ProjectIssue)
        mock_current_issue.iid = kr_iid
        mock_current_issue.title = "OBJ1 - KR1: Test KR"
        mock_current_issue.web_url = f"https://fakegitlab.com/fakeproject/issues/{kr_iid}"
        # Construct original description using the service's formatting logic for consistency
        mock_current_issue.description = (
            f"### Descrição{NL}{NL}> {original_description_text.replace(NL, NL + '> ')}{NL}{NL}"
            f"**Meta prevista**: {original_meta_prevista}%  {NL}"
            f"**Meta realizada**: {original_meta_realizada}%  {NL}"
            f"**Responsável(eis)**: {', '.join(original_responsaveis)}  {NL}{NL}"
            f"{activities_table_content}"
        )

        self.mock_gitlab_service_patched.get_issue.return_value = mock_current_issue

        # Mock the return value of update_issue to be the same issue object,
        # but its description will be checked via call_args
        self.mock_gitlab_service_patched.update_issue.return_value = mock_current_issue

        update_payload = KRUpdateRequest(
            description="Updated detailed description.",
            meta_prevista=75.0,
            meta_realizada=25.0,
            responsaveis=["User Gamma", "User Delta"]
        )

        response = self.kr_service.update_kr(kr_iid, update_payload)

        self.mock_gitlab_service_patched.get_issue.assert_called_once_with(kr_iid)

        args, kwargs = self.mock_gitlab_service_patched.update_issue.call_args
        self.assertEqual(kwargs['issue_iid'], kr_iid)

        expected_updated_description = (
            f"### Descrição{NL}{NL}> {update_payload.description.replace(NL, NL + '> ')}{NL}{NL}"
            f"**Meta prevista**: {update_payload.meta_prevista}%  {NL}"
            f"**Meta realizada**: {update_payload.meta_realizada}%  {NL}"
            f"**Responsável(eis)**: {', '.join(update_payload.responsaveis)}  {NL}{NL}"
            f"{activities_table_content}"
        )
        # Normalize newlines for comparison if needed, though direct string compare should work if consistent
        self.assertEqual(kwargs['description'].replace('\r\n', NL), expected_updated_description.replace('\r\n', NL))

        self.assertIsInstance(response, KRResponse)
        self.assertEqual(response.id, kr_iid)
        # The title and web_url are from mock_current_issue, description from update_issue call
        self.assertEqual(response.description, kwargs['description'])

    def test_update_kr_partial_meta_realizada_success(self):
        NL = '\n'
        kr_iid = 124
        original_description_text = "Another KR description."
        original_meta_prevista = 90.0
        original_meta_realizada = 40.0
        original_responsaveis = ["Team Lead"]
        activities_table_content = (
            "| Projetos/Ações/Atividades | Partes interessadas | Prazo Previsto | Prazo Realizado | % Previsto | % Realizado |\n"
            "|---------------------------|----------------------|----------------|-----------------|------------|-------------|"
        ) # Empty table

        mock_current_issue = MagicMock(spec=ProjectIssue)
        mock_current_issue.iid = kr_iid
        mock_current_issue.title = "OBJ2 - KR1: Partial Update KR"
        mock_current_issue.web_url = f"https://fakegitlab.com/fakeproject/issues/{kr_iid}"
        mock_current_issue.description = (
            f"### Descrição{NL}{NL}> {original_description_text}{NL}{NL}"
            f"**Meta prevista**: {original_meta_prevista}%  {NL}"
            f"**Meta realizada**: {original_meta_realizada}%  {NL}"
            f"**Responsável(eis)**: {', '.join(original_responsaveis)}  {NL}{NL}"
            f"{activities_table_content}"
        )

        self.mock_gitlab_service_patched.get_issue.return_value = mock_current_issue
        self.mock_gitlab_service_patched.update_issue.return_value = mock_current_issue

        update_payload = KRUpdateRequest(meta_realizada=55.5) # Only updating this

        response = self.kr_service.update_kr(kr_iid, update_payload)
        self.mock_gitlab_service_patched.get_issue.assert_called_once_with(kr_iid)

        args, kwargs = self.mock_gitlab_service_patched.update_issue.call_args
        self.assertEqual(kwargs['issue_iid'], kr_iid)

        expected_updated_description = (
            f"### Descrição{NL}{NL}> {original_description_text}{NL}{NL}" # Description preserved
            f"**Meta prevista**: {original_meta_prevista}%  {NL}" # Preserved
            f"**Meta realizada**: {update_payload.meta_realizada}%  {NL}" # Updated
            f"**Responsável(eis)**: {', '.join(original_responsaveis)}  {NL}{NL}" # Preserved
            f"{activities_table_content}" # Preserved
        )
        self.assertEqual(kwargs['description'].replace('\r\n', NL), expected_updated_description.replace('\r\n', NL))
        self.assertEqual(response.description, kwargs['description'])

    def test_update_kr_not_found(self):
        kr_iid = 404
        # Ensure GitlabGetError is imported for this: from gitlab.exceptions import GitlabGetError
        # If not already, add `from gitlab.exceptions import GitlabGetError` to test file imports
        # from gitlab.exceptions import GitlabGetError # Local import for clarity or ensure it's at top
        self.mock_gitlab_service_patched.get_issue.side_effect = GitlabGetError

        update_payload = KRUpdateRequest(description="Doesn't matter")

        with self.assertRaisesRegex(ValueError, f"KR with IID {kr_iid} not found."):
            self.kr_service.update_kr(kr_iid, update_payload)
        self.mock_gitlab_service_patched.get_issue.assert_called_once_with(kr_iid)
        self.mock_gitlab_service_patched.update_issue.assert_not_called()

    def test_update_kr_empty_description_and_responsaveis(self):
        NL = '\n'
        kr_iid = 125
        original_description_text = "KR with content."
        original_meta_prevista = 100.0
        original_meta_realizada = 50.0
        original_responsaveis = ["Initial Person"]
        activities_table_content = (
            "| Projetos/Ações/Atividades | Partes interessadas | Prazo Previsto | Prazo Realizado | % Previsto | % Realizado |\n"
            "|---------------------------|----------------------|----------------|-----------------|------------|-------------|"
        )

        mock_current_issue = MagicMock(spec=ProjectIssue)
        mock_current_issue.iid = kr_iid
        mock_current_issue.title = "OBJ3 - KR1: Empty Fields Test"
        mock_current_issue.web_url = f"https://fakegitlab.com/fakeproject/issues/{kr_iid}"
        mock_current_issue.description = (
            f"### Descrição{NL}{NL}> {original_description_text}{NL}{NL}"
            f"**Meta prevista**: {original_meta_prevista}%  {NL}"
            f"**Meta realizada**: {original_meta_realizada}%  {NL}"
            f"**Responsável(eis)**: {', '.join(original_responsaveis)}  {NL}{NL}"
            f"{activities_table_content}"
        )

        self.mock_gitlab_service_patched.get_issue.return_value = mock_current_issue
        self.mock_gitlab_service_patched.update_issue.return_value = mock_current_issue

        update_payload = KRUpdateRequest(description="", responsaveis=[])

        response = self.kr_service.update_kr(kr_iid, update_payload)

        args, kwargs = self.mock_gitlab_service_patched.update_issue.call_args
        expected_updated_description = (
            f"### Descrição{NL}{NL}> (Descrição não fornecida){NL}{NL}" # Updated description
            f"**Meta prevista**: {original_meta_prevista}%  {NL}"   # Preserved
            f"**Meta realizada**: {original_meta_realizada}%  {NL}" # Preserved
            f"**Responsável(eis)**: N/A  {NL}{NL}"                   # Updated responsaveis
            f"{activities_table_content}"                           # Preserved
        )
        self.assertEqual(kwargs['description'].replace('\r\n', NL), expected_updated_description.replace('\r\n', NL))
        self.assertEqual(response.description, kwargs['description'])

    # Remember to reset mocks for each test if not done in setUp for every call
    # The current setUp does reset_mock on the main instance.
    # For get_issue, update_issue per-test, ensure they are reset or configured freshly.
    # The provided setUp calls self.mock_gitlab_service_instance.reset_mock() which should be fine.
    # If side_effect or return_value is set on a method, it should be cleared or reset if subsequent tests
    # using the same mock method expect different behavior. MagicMock typically resets these.
    # For specific mock methods like get_issue, if you set side_effect in one test,
    # ensure it's reset (e.g. `self.mock_gitlab_service_patched.get_issue.side_effect = None`) or
    # re-assigned in other tests if they also use it.
    # The current structure of creating a new mock_current_issue and setting return_value per test is good.

if __name__ == '__main__':
    unittest.main()
