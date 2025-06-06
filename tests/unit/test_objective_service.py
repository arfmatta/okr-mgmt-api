import unittest
from unittest.mock import MagicMock, patch, call
from app.services.objective_service import ObjectiveService
from app.models import ObjectiveCreateRequest, ObjectiveResponse, KRDetailResponse
# Removed GitlabConfig as it's not used by the service directly in tests
from app.config import Settings # Import Settings to create test_settings instance
from gitlab.v4.objects import ProjectIssue
from gitlab.exceptions import GitlabGetError


class TestObjectiveService(unittest.TestCase):

    @staticmethod
    def _create_mock_gl_issue(iid: int, title: str, description: str, labels: list[str], web_url: str, links_list: list = None):
        issue = MagicMock(spec=ProjectIssue)
        issue.iid = iid
        issue.title = title
        issue.description = description
        issue.labels = labels
        issue.web_url = web_url
        if links_list is not None:
            issue.links = MagicMock()
            issue.links.list.return_value = links_list
        return issue

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

    # --- Tests for get_krs_for_objective ---

    def test_get_krs_successful_retrieval_and_parsing(self):
        objective_id = 1
        objective_web_url = f"http://fakegitlab.com/obj/{objective_id}"

        # KR Candidates
        kr_1_iid = 101
        kr_1_title = "OBJ1 - KR1: Fully Implement Feature X"
        kr_1_desc = (
            "### Descrição\n\n"
            "> This is KR1. It's super important.\n"
            "> It has multiple lines.\n\n"
            "**Prioridade**: Alta\n"
            "**Meta prevista**: 100%\n"
            "**Meta realizada**: 75%\n"
            "**Responsável(eis)**: user1, user2\n"
            "**Iniciativa associada**: INIC-A"
        )
        kr_1_labels = ["OKR::Resultado Chave", "TEAM::Phoenix", "PRODUCT::SkyRos"]
        mock_kr_1 = self._create_mock_gl_issue(iid=kr_1_iid, title=kr_1_title, description=kr_1_desc, labels=kr_1_labels, web_url=f"http://fakegitlab.com/kr/{kr_1_iid}")

        kr_2_iid = 102
        kr_2_title = "OBJ1 - KR2: Launch Beta Program" # Missing optional data in description
        kr_2_desc = (
            "### Descrição\n\n"
            "> KR2 Description.\n\n"
            "**Meta prevista**: 100%\n"
            # Meta realizada missing
            # Responsaveis missing
        )
        kr_2_labels = ["OKR::Resultado Chave", "TEAM::Omega"] # Product missing
        mock_kr_2 = self._create_mock_gl_issue(iid=kr_2_iid, title=kr_2_title, description=kr_2_desc, labels=kr_2_labels, web_url=f"http://fakegitlab.com/kr/{kr_2_iid}")

        non_kr_issue_iid = 103
        mock_non_kr_issue = self._create_mock_gl_issue(iid=non_kr_issue_iid, title="Just a normal issue", description="Not a KR", labels=["Bug"], web_url=f"http://fakegitlab.com/issue/{non_kr_issue_iid}")

        kr_3_iid = 104 # Malformed title and description
        kr_3_title = "Malformed KR title"
        kr_3_desc = (
            "No standard KR formatting here."
        )
        kr_3_labels = ["OKR::Resultado Chave", "TEAM::Gamma"]
        mock_kr_3 = self._create_mock_gl_issue(iid=kr_3_iid, title=kr_3_title, description=kr_3_desc, labels=kr_3_labels, web_url=f"http://fakegitlab.com/kr/{kr_3_iid}")


        # Mock Objective and its links
        # The ProjectIssueLink objects returned by objective_issue.links.list() are actually ProjectIssue instances.
        # So, the items in links_list should be these KR "candidate" issue mocks directly.
        mock_objective_issue = self._create_mock_gl_issue(
            iid=objective_id, title="Objective 1", description="Objective Desc", labels=["OKR::Objetivo"], web_url=objective_web_url,
            links_list=[mock_kr_1, mock_kr_2, mock_non_kr_issue, mock_kr_3] # These are "ProjectIssue" like objects
        )

        # Setup side_effect for gitlab_service.get_issue
        # It needs to return the objective first, then the KRs when called with their respective IIDs
        def get_issue_side_effect(issue_iid):
            if issue_iid == objective_id:
                return mock_objective_issue
            elif issue_iid == kr_1_iid:
                return mock_kr_1
            elif issue_iid == kr_2_iid:
                return mock_kr_2
            elif issue_iid == non_kr_issue_iid: # Should not be fetched again if not KR
                return mock_non_kr_issue
            elif issue_iid == kr_3_iid:
                return mock_kr_3
            self.fail(f"gitlab_service.get_issue called with unexpected iid: {issue_iid}")

        self.mock_gitlab_service_instance_patched.get_issue.side_effect = get_issue_side_effect

        # Call the method
        krs_response = self.objective_service.get_krs_for_objective(objective_id)

        # Assertions
        self.assertEqual(len(krs_response), 3) # kr_1, kr_2, kr_3 (non_kr_issue filtered out)

        # KR1 Asserts (Full data)
        kr1_res = next(kr for kr in krs_response if kr.id == kr_1_iid)
        self.assertEqual(kr1_res.id, kr_1_iid)
        self.assertEqual(str(kr1_res.web_url), f"http://fakegitlab.com/kr/{kr_1_iid}")
        self.assertEqual(kr1_res.objective_iid, objective_id)
        self.assertEqual(kr1_res.kr_number, 1)
        self.assertEqual(kr1_res.title, "Fully Implement Feature X")
        self.assertEqual(kr1_res.description, "This is KR1. It's super important.\nIt has multiple lines.")
        self.assertEqual(kr1_res.meta_prevista, 100)
        self.assertEqual(kr1_res.meta_realizada, 75)
        self.assertEqual(kr1_res.team_label, "Phoenix")
        self.assertEqual(kr1_res.product_label, "SkyRos")
        self.assertListEqual(kr1_res.responsaveis, ["user1", "user2"])

        # KR2 Asserts (Missing optional data)
        kr2_res = next(kr for kr in krs_response if kr.id == kr_2_iid)
        self.assertEqual(kr2_res.id, kr_2_iid)
        self.assertEqual(str(kr2_res.web_url), f"http://fakegitlab.com/kr/{kr_2_iid}")
        self.assertEqual(kr2_res.objective_iid, objective_id)
        self.assertEqual(kr2_res.kr_number, 2)
        self.assertEqual(kr2_res.title, "Launch Beta Program")
        self.assertEqual(kr2_res.description, "KR2 Description.")
        self.assertEqual(kr2_res.meta_prevista, 100)
        self.assertEqual(kr2_res.meta_realizada, 0) # Default
        self.assertEqual(kr2_res.team_label, "Omega")
        self.assertEqual(kr2_res.product_label, "N/A") # Default
        self.assertListEqual(kr2_res.responsaveis, []) # Default

        # KR3 Asserts (Malformed title/description)
        kr3_res = next(kr for kr in krs_response if kr.id == kr_3_iid)
        self.assertEqual(kr3_res.id, kr_3_iid)
        self.assertEqual(str(kr3_res.web_url), f"http://fakegitlab.com/kr/{kr_3_iid}")
        self.assertEqual(kr3_res.objective_iid, objective_id)
        self.assertEqual(kr3_res.kr_number, 0) # Default from malformed title
        self.assertEqual(kr3_res.title, "Malformed KR title") # Full title as fallback
        self.assertEqual(kr3_res.description, "N/A") # Default from malformed description
        self.assertEqual(kr3_res.meta_prevista, 0) # Default
        self.assertEqual(kr3_res.meta_realizada, 0) # Default
        self.assertEqual(kr3_res.team_label, "Gamma")
        self.assertEqual(kr3_res.product_label, "N/A") # Default
        self.assertListEqual(kr3_res.responsaveis, []) # Default

        # Check calls to gitlab_service.get_issue
        expected_calls = [
            call(objective_id), # Fetch objective
            call(kr_1_iid),     # Fetch KR1 (linked)
            call(kr_2_iid),     # Fetch KR2 (linked)
            call(non_kr_issue_iid), # Fetch non-KR (linked)
            call(kr_3_iid)      # Fetch KR3 (linked)
        ]
        self.mock_gitlab_service_instance_patched.get_issue.assert_has_calls(expected_calls, any_order=False)
        # The number of calls should be exactly this many.
        # The service fetches the objective, then iterates its links *references*
        # and then fetches *each* linked issue by its iid again.
        self.assertEqual(self.mock_gitlab_service_instance_patched.get_issue.call_count, 1 + len(mock_objective_issue.links.list.return_value))


    def test_get_krs_objective_not_found(self):
        non_existent_objective_id = 999
        self.mock_gitlab_service_instance_patched.get_issue.side_effect = GitlabGetError("Objective not found")

        krs_response = self.objective_service.get_krs_for_objective(non_existent_objective_id)

        self.assertEqual(len(krs_response), 0)
        self.mock_gitlab_service_instance_patched.get_issue.assert_called_once_with(non_existent_objective_id)

    def test_get_krs_objective_has_no_links(self):
        objective_id = 2
        mock_objective_issue = self._create_mock_gl_issue(
            iid=objective_id, title="Objective with no links", description="Desc", labels=["OKR::Objetivo"], web_url="http://fake.com/obj/2",
            links_list=[] # No links
        )
        self.mock_gitlab_service_instance_patched.get_issue.return_value = mock_objective_issue # Only called for objective

        krs_response = self.objective_service.get_krs_for_objective(objective_id)

        self.assertEqual(len(krs_response), 0)
        self.mock_gitlab_service_instance_patched.get_issue.assert_called_once_with(objective_id)

    def test_get_krs_objective_has_links_but_none_are_krs(self):
        objective_id = 3

        issue_a_iid = 301
        mock_issue_a = self._create_mock_gl_issue(iid=issue_a_iid, title="Issue A", description="Desc A", labels=["Bug"], web_url="http://fake.com/issue/a")
        issue_b_iid = 302
        mock_issue_b = self._create_mock_gl_issue(iid=issue_b_iid, title="Issue B", description="Desc B", labels=["Feature"], web_url="http://fake.com/issue/b")

        mock_objective_issue = self._create_mock_gl_issue(
            iid=objective_id, title="Objective 3", description="Objective Desc", labels=["OKR::Objetivo"], web_url="http://fake.com/obj/3",
            links_list=[mock_issue_a, mock_issue_b]
        )

        def get_issue_side_effect(issue_iid):
            if issue_iid == objective_id:
                return mock_objective_issue
            elif issue_iid == issue_a_iid:
                return mock_issue_a
            elif issue_iid == issue_b_iid:
                return mock_issue_b
            self.fail(f"gitlab_service.get_issue called with unexpected iid: {issue_iid}")

        self.mock_gitlab_service_instance_patched.get_issue.side_effect = get_issue_side_effect

        krs_response = self.objective_service.get_krs_for_objective(objective_id)

        self.assertEqual(len(krs_response), 0)

        expected_calls = [
            call(objective_id),
            call(issue_a_iid),
            call(issue_b_iid)
        ]
        self.mock_gitlab_service_instance_patched.get_issue.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(self.mock_gitlab_service_instance_patched.get_issue.call_count, 3)

    # --- Tests for list_objectives_by_filters ---

    def test_list_objectives_by_filters_all_params(self):
        mock_issue1 = self._create_mock_gl_issue(iid=1, title="Objective 1", description="Desc 1", labels=[], web_url="http://fake.com/1")
        mock_issue2 = self._create_mock_gl_issue(iid=2, title="Objective 2", description="Desc 2", labels=[], web_url="http://fake.com/2")
        self.mock_gitlab_service_instance_patched.list_issues.return_value = [mock_issue1, mock_issue2]

        year, team, product = "2023", "Alpha", "Omega"
        responses = self.objective_service.list_objectives_by_filters(year=year, team=team, product=product)

        expected_filter_labels = list(self.test_settings.gitlab_objective_labels) + [year, f"TEAM::{team}", f"PRODUCT::{product}"]

        self.mock_gitlab_service_instance_patched.list_issues.assert_called_once()
        called_args, called_kwargs = self.mock_gitlab_service_instance_patched.list_issues.call_args
        self.assertCountEqual(called_kwargs['labels'], expected_filter_labels) # Use assertCountEqual for lists where order doesn't matter

        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].id, mock_issue1.iid)
        self.assertEqual(responses[1].title, mock_issue2.title)

    def test_list_objectives_by_filters_year_and_team(self):
        mock_issue1 = self._create_mock_gl_issue(iid=3, title="Objective 3", description="Desc 3", labels=[], web_url="http://fake.com/3")
        self.mock_gitlab_service_instance_patched.list_issues.return_value = [mock_issue1]

        year, team = "2023", "Beta"
        responses = self.objective_service.list_objectives_by_filters(year=year, team=team)

        expected_filter_labels = list(self.test_settings.gitlab_objective_labels) + [year, f"TEAM::{team}"]
        self.mock_gitlab_service_instance_patched.list_issues.assert_called_once()
        called_args, called_kwargs = self.mock_gitlab_service_instance_patched.list_issues.call_args
        self.assertCountEqual(called_kwargs['labels'], expected_filter_labels)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].id, mock_issue1.iid)

    def test_list_objectives_by_filters_only_year(self):
        mock_issue1 = self._create_mock_gl_issue(iid=4, title="Objective 4", description="Desc 4", labels=[], web_url="http://fake.com/4")
        self.mock_gitlab_service_instance_patched.list_issues.return_value = [mock_issue1]
        year = "2024"
        responses = self.objective_service.list_objectives_by_filters(year=year)
        expected_filter_labels = list(self.test_settings.gitlab_objective_labels) + [year]
        self.mock_gitlab_service_instance_patched.list_issues.assert_called_once()
        called_args, called_kwargs = self.mock_gitlab_service_instance_patched.list_issues.call_args
        self.assertCountEqual(called_kwargs['labels'], expected_filter_labels)
        self.assertEqual(len(responses), 1)

    def test_list_objectives_by_filters_only_team(self):
        mock_issue1 = self._create_mock_gl_issue(iid=5, title="Objective 5", description="Desc 5", labels=[], web_url="http://fake.com/5")
        self.mock_gitlab_service_instance_patched.list_issues.return_value = [mock_issue1]
        team = "Gamma"
        responses = self.objective_service.list_objectives_by_filters(team=team)
        expected_filter_labels = list(self.test_settings.gitlab_objective_labels) + [f"TEAM::{team}"]
        self.mock_gitlab_service_instance_patched.list_issues.assert_called_once()
        called_args, called_kwargs = self.mock_gitlab_service_instance_patched.list_issues.call_args
        self.assertCountEqual(called_kwargs['labels'], expected_filter_labels)
        self.assertEqual(len(responses), 1)

    def test_list_objectives_by_filters_only_product(self):
        mock_issue1 = self._create_mock_gl_issue(iid=6, title="Objective 6", description="Desc 6", labels=[], web_url="http://fake.com/6")
        self.mock_gitlab_service_instance_patched.list_issues.return_value = [mock_issue1]
        product = "Sigma"
        responses = self.objective_service.list_objectives_by_filters(product=product)
        expected_filter_labels = list(self.test_settings.gitlab_objective_labels) + [f"PRODUCT::{product}"]
        self.mock_gitlab_service_instance_patched.list_issues.assert_called_once()
        called_args, called_kwargs = self.mock_gitlab_service_instance_patched.list_issues.call_args
        self.assertCountEqual(called_kwargs['labels'], expected_filter_labels)
        self.assertEqual(len(responses), 1)

    def test_list_objectives_by_filters_no_filters_raises_valueerror(self):
        expected_message = "At least one filter (year, team, or product) must be provided."
        with self.assertRaisesRegex(ValueError, expected_message):
            self.objective_service.list_objectives_by_filters()
        self.mock_gitlab_service_instance_patched.list_issues.assert_not_called()

    def test_list_objectives_by_filters_gitlab_returns_empty(self):
        self.mock_gitlab_service_instance_patched.list_issues.return_value = []
        year = "2023"
        responses = self.objective_service.list_objectives_by_filters(year=year)
        expected_filter_labels = list(self.test_settings.gitlab_objective_labels) + [year]

        self.mock_gitlab_service_instance_patched.list_issues.assert_called_once()
        called_args, called_kwargs = self.mock_gitlab_service_instance_patched.list_issues.call_args
        self.assertCountEqual(called_kwargs['labels'], expected_filter_labels)
        self.assertEqual(len(responses), 0)


if __name__ == '__main__':
    unittest.main()
