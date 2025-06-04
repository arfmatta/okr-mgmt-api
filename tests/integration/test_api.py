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

        if not all([settings.gitlab_api_url, settings.gitlab_access_token, settings.gitlab_project_id,
                    settings.gitlab_objective_labels, settings.gitlab_kr_labels]):
            raise EnvironmentError("GitLab API settings (URL, Token, Project ID, Labels) not configured. "
                                   "Ensure .env file is present and correctly set up for integration testing.")

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
            description="This is created by an integration test."
        )
        response = self.client.post("/objectives/", json=payload.model_dump())

        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertIsInstance(data.get("id"), int)
        self.assertGreater(data.get("id"), 0)
        self.assertEqual(data.get("title"), f"OBJ{payload.obj_number}: {payload.title.upper()}")
        self.assertIn("###  Descrição:", data.get("description"))
        self.assertIn(f"> {payload.description}", data.get("description")) # Description is quoted
        self.assertIn("### Resultados Chave", data.get("description"))
        self.assertTrue(data.get("web_url").startswith(settings.gitlab_api_url))

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
            meta_prevista=100.0,
            meta_realizada=10.0, # Example value
            responsaveis=["Integration Tester"]
        )
        response = self.client.post("/krs/", json=payload.model_dump())

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
        self.assertTrue(data.get("web_url").startswith(settings.gitlab_api_url))
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
            progress_planned_percent=100.0,
            progress_achieved_percent=0.0
        )
        activities_payload = ActivityCreateRequest(activities=[activity_detail])

        # Endpoint is POST /activities/kr/{kr_iid} as per app/routers/activities.py
        response = self.client.post(f"/activities/kr/{target_kr_iid}", json=activities_payload.model_dump())

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

if __name__ == '__main__':
    import sys
    # Ensures 'app' module can be found when running script directly from tests/integration/
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    print("Running integration tests directly. Make sure .env is configured in project root and PYTHONPATH includes project root.")
    unittest.main()
