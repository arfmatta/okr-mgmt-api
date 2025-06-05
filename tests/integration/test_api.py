import unittest
import os
import time # For potential cleanup delays or rate limiting
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Ensure that the main app can be imported.
from app.main import app
from app.models import ObjectiveCreateRequest, ObjectiveResponse, KRCreateRequest, KRResponse, Activity, ActivityCreateRequest
from app.config import settings

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
print(f"Attempting to load .env from: {dotenv_path}")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
    print(f"Loaded .env file. GITLAB_PROJECT_ID from settings: {settings.gitlab_project_id}")
else:
    print(".env file not found at expected location. Ensure it exists for integration tests.")

class TestAPIIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.created_objective_iids = []
        cls.created_kr_iids = []
        cls.access_token = None
        cls.auth_headers = {}

        if not all([settings.gitlab_api_url, settings.gitlab_access_token, settings.gitlab_project_id,
                    settings.gitlab_objective_labels, settings.gitlab_kr_labels]):
            raise EnvironmentError("GitLab API settings (URL, Token, Project ID, Labels) not configured. "
                                   "Ensure .env file is present and correctly set up for integration testing.")

        # Acquire JWT token for the test class
        token_response = cls.client.post("/auth/token", data={"username": "testuser", "password": "testpass"})
        if token_response.status_code != 200:
            raise Exception(f"Failed to acquire test token in setUpClass: {token_response.text}")
        cls.access_token = token_response.json()["access_token"]
        cls.auth_headers = {"Authorization": f"Bearer {cls.access_token}"}
        print("Access token acquired for integration tests.")

    @classmethod
    def tearDownClass(cls):
        # Placeholder for cleanup
        # In a real test suite, you would add code here to delete or close issues created during tests.
        # For example, using the python-gitlab library directly.
        # print(f"Cleaning up {len(cls.created_kr_iids)} KRs and {len(cls.created_objective_iids)} Objectives.")
        pass

    def test_01_create_objective(self):
        print(f"Running test_01_create_objective with project_id: {settings.gitlab_project_id}")
        payload = ObjectiveCreateRequest(
            obj_number=99, # Using a distinct number for test objectives
            title="Integration Test Objective",
            description="This is created by an integration test.",
            team_label="IntegrationTeam",
            product_label="IntegrationProduct"
        )
        response = self.client.post("/objectives/", json=payload.model_dump(), headers=self.__class__.auth_headers)

        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertIsInstance(data.get("id"), int)
        self.assertGreater(data.get("id"), 0)
        self.assertEqual(data.get("title"), f"OBJ{payload.obj_number}: {payload.title.upper()}")
        self.assertIn("###  Descrição:", data.get("description"))
        self.assertIn(f"> {payload.description}", data.get("description")) # Description is quoted
        self.assertIn("### Resultados Chave", data.get("description"))
        self.assertIn("web_url", data)
        # Permita que web_url comece com http ou https, e ignore possíveis barras finais
        self.assertTrue(
            data.get("web_url").startswith("http://") or data.get("web_url").startswith("https://"),
            f"web_url '{data.get('web_url')}' does not start with http(s)://"
        )
        # Permita que o host real seja diferente do host do settings (ex: ambiente de produção vs homologação)
        from urllib.parse import urlparse
        expected_host = urlparse(settings.gitlab_api_url).hostname
        actual_host = urlparse(data.get("web_url")).hostname
        self.assertTrue(
            expected_host.split(".", 1)[-1] == actual_host.split(".", 1)[-1],
            f"web_url host '{actual_host}' não termina com '{expected_host.split('.', 1)[-1]}'"
        )

        if data.get("id"):
            self.__class__.created_objective_iids.append(data["id"])
            print(f"Objective created with IID: {data['id']}")

    def test_02_create_kr(self):
        if not self.__class__.created_objective_iids:
            self.skipTest("Skipping KR creation test as no objective IID is available from test_01_create_objective.")

        parent_objective_iid = self.__class__.created_objective_iids[0]
        print(f"Running test_02_create_kr, creating KR under objective IID: {parent_objective_iid}")

        payload = KRCreateRequest(
            objective_iid=parent_objective_iid,
            kr_number=1, # Test KR number
            title="Integration Test KR",
            description="This KR is created by an integration test.", # This will be quoted by KRService
            meta_prevista=100,
            meta_realizada=10, # Example value
            responsaveis=["Integration Tester"],
            team_label="IntegrationTeam",
            product_label="IntegrationProduct"
        )
        response = self.client.post("/krs/", json=payload.model_dump(), headers=self.__class__.auth_headers)

        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertIsInstance(data.get("id"), int)
        self.assertGreater(data.get("id"), 0)
        # KRService._get_objective_prefix and title formatting: "OBJ<prefix> - KR<num>: <title>"
        # We can't know the exact objective prefix (OBJ99 or OBJ<iid>) without running test_01 or querying GitLab.
        # So, we check for the KR specific part of the title.
        self.assertIn(f"- KR{payload.kr_number}: {payload.title}", data.get("title"))
        self.assertIn("### Descrição", data.get("description")) # From KRService._format_kr_description
        self.assertIn(f"> {payload.description}", data.get("description")) # Check quoted input description
        self.assertIn(f"**Meta prevista**: {payload.meta_prevista}%", data.get("description"))
        self.assertIn(f"**Meta realizada**: {payload.meta_realizada}%", data.get("description"))
        self.assertIn(f"**Responsável(eis)**: {', '.join(payload.responsaveis)}", data.get("description"))
        self.assertIn("| Projetos/Ações/Atividades |", data.get("description")) # Check for activities table header
        #não funciona no gitlab de homolog, pq retorna url de produção
        #self.assertTrue(data.get("web_url").startswith(settings.gitlab_api_url))
        self.assertEqual(data.get("objective_iid"), parent_objective_iid)

        if data.get("id"):
            self.__class__.created_kr_iids.append(data["id"])
            print(f"KR created with IID: {data['id']}")

    def test_03_add_activities_to_kr(self):
        if not self.__class__.created_kr_iids:
            self.skipTest("Skipping Add Activities test as no KR IID is available from test_02_create_kr.")

        target_kr_iid = self.__class__.created_kr_iids[0]
        print(f"Running test_03_add_activities_to_kr for KR IID: {target_kr_iid}")

        activity_detail = Activity(
            project_action_activity="Integration Test Activity 1",
            stakeholders="Dev Team",
            deadline_planned="Q4/2024",
            deadline_achieved=None, # Test None case for deadline_achieved
            progress_planned_percent=100, # Changed from 100.0
            progress_achieved_percent=0   # Changed from 0.0
        )
        activities_payload = ActivityCreateRequest(activities=[activity_detail])

        # Endpoint is POST /activities/kr/{kr_iid} as per app/routers/activities.py
        response = self.client.post(f"/activities/kr/{target_kr_iid}", json=activities_payload.model_dump(), headers=self.__class__.auth_headers)

        self.assertEqual(response.status_code, 200, response.text) # Returns 200 OK with DescriptionResponse
        data = response.json()
        self.assertIn("description", data) # Expecting {"description": "..."}

        # Verify the activity (as a Markdown table row) is now in the KR's description
        # ActivityService._serialize_activity_to_table_row creates:
        # | {project_action} | {stakeholders} | {deadline_planned} | {deadline_achieved or ""} | {progress_planned}% | {progress_achieved}% |
        self.assertIn(f"| {activity_detail.project_action_activity} |", data["description"])
        self.assertIn(f"| {activity_detail.stakeholders} |", data["description"])
        self.assertIn(f"| {activity_detail.deadline_planned} |", data["description"])
        self.assertIn(f"|  |", data["description"]) # deadline_achieved is None, so empty cell
        self.assertIn(f"| {activity_detail.progress_planned_percent}% |", data["description"])
        self.assertIn(f"| {activity_detail.progress_achieved_percent}% |", data["description"])

        print(f"Activities added to KR IID: {target_kr_iid}")

    def test_04_access_protected_route_no_token(self):
        print("Running test_04_access_protected_route_no_token")
        # Attempt to access POST /objectives/ which is now protected
        payload = { # Using dict directly for simplicity, matches ObjectiveCreateRequest structure
            "obj_number": 101,
            "title": "Test Objective No Token",
            "description": "This should fail.",
            "team_label": "TeamAuthTest",
            "product_label": "ProductAuthTest"
        }
        response = self.client.post("/objectives/", json=payload)
        # Expect 401 Unauthorized because OAuth2PasswordBearer by default returns 401
        # if no token is present, before our custom validation logic is even hit.
        self.assertEqual(response.status_code, 401, response.text)
        self.assertIn("Not authenticated", response.json().get("detail"),
                      "Detail message might vary based on FastAPI/Starlette defaults for missing token")

    # test_05_get_token_and_access_protected_route is removed as its functionality
    # is now covered by setUpClass token acquisition and test_01_create_objective.

    def test_06_access_protected_get_routes(self):
        print("Running test_06_access_protected_get_routes")

        # Test GET /objectives/ without token
        response_no_token_obj_list = self.client.get("/objectives/")
        self.assertEqual(response_no_token_obj_list.status_code, 401)
        self.assertIn("Not authenticated", response_no_token_obj_list.json().get("detail"))

        # Test GET /objectives/ with token
        response_with_token_obj_list = self.client.get("/objectives/", headers=self.__class__.auth_headers)
        self.assertEqual(response_with_token_obj_list.status_code, 200)
        self.assertIsInstance(response_with_token_obj_list.json(), list) # Expect a list of objectives

        # Test GET /krs/ without token
        response_no_token_kr_list = self.client.get("/krs/")
        self.assertEqual(response_no_token_kr_list.status_code, 401)
        self.assertIn("Not authenticated", response_no_token_kr_list.json().get("detail"))

        # Test GET /krs/ with token
        response_with_token_kr_list = self.client.get("/krs/", headers=self.__class__.auth_headers)
        self.assertEqual(response_with_token_kr_list.status_code, 200)
        self.assertIsInstance(response_with_token_kr_list.json(), list) # Expect a list of KRs

if __name__ == '__main__':
    import sys
    # Ensures 'app' module can be found when running script directly from tests/integration/
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    print("Running integration tests directly. Make sure .env is configured in project root and PYTHONPATH includes project root.")
    unittest.main()
