# import re # Not used currently
from typing import List # Ensure List is imported
from app.services import gitlab_service
from app.models import Activity

class ActivityService:
    def __init__(self):
        self.gitlab_service = gitlab_service

    def _serialize_activity_to_table_row(self, activity: Activity) -> str:
        project_action = activity.project_action_activity or ""
        stakeholders = activity.stakeholders or ""
        deadline_planned = activity.deadline_planned or ""
        deadline_achieved = activity.deadline_achieved or ""
        progress_planned = f"{activity.progress_planned_percent}%"
        progress_achieved = f"{activity.progress_achieved_percent}%"

        return (
            f"| {project_action} | {stakeholders} | {deadline_planned} | "
            f"{deadline_achieved} | {progress_planned} | {progress_achieved} |"
        )

    def add_activities_to_kr_description(self, kr_iid: int, new_activities: List[Activity]) -> str:
        try:
            kr_issue = self.gitlab_service.get_issue(kr_iid)
            current_description = kr_issue.description or ""

            activity_rows_to_add: List[str] = [] # Type hint for clarity
            for act in new_activities:
                activity_rows_to_add.append(self._serialize_activity_to_table_row(act))

            new_rows_string = "\n".join(activity_rows_to_add)

            # Logic for adding new rows, including table header if description was empty
            # and new activities are being added.
            if not current_description.strip(): # Description is empty or only whitespace
                if new_rows_string: # Only add header if there are new rows to add
                    table_header = (
                        "| Projetos/Ações/Atividades | Partes interessadas | Prazo Previsto | Prazo Realizado | % Previsto | % Realizado |\n"
                        "|---------------------------|----------------------|----------------|-----------------|------------|-------------|"
                    )
                    updated_description = table_header + "\n" + new_rows_string
                else: # No current description and no new activities
                    updated_description = "" # Keep it empty
            else: # Description has content
                updated_description = current_description.rstrip() + "\n" + new_rows_string

            # Only update if there was a change (though update_issue might be idempotent)
            if updated_description != (kr_issue.description or ""):
                 self.gitlab_service.update_issue(
                    issue_iid=kr_iid,
                    description=updated_description
                )

            return updated_description

        except Exception as e:
            # Log error, e.g. using logging module
            # print(f"Error adding activities to KR {kr_iid}: {e}")
            raise # Re-raise for the router to handle

activity_service = ActivityService()
