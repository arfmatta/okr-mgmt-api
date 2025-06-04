import re # Though regex is not used in this version
from typing import List
from app.services import gitlab_service # Corrected: import the instance directly
from app.models import Activity
# Removed KRCreateRequest, KRResponse as they are not directly used here

class ActivityService:
    def __init__(self):
        self.gitlab_service = gitlab_service # Use the shared instance

    def _serialize_activity_to_table_row(self, activity: Activity) -> str:
        # Serializes Activity to a Markdown table row.
        project_action = activity.project_action_activity or ""
        stakeholders = activity.stakeholders or ""
        deadline_planned = activity.deadline_planned or ""
        deadline_achieved = activity.deadline_achieved or "" # Will be empty if None
        progress_planned = f"{activity.progress_planned_percent}%"
        progress_achieved = f"{activity.progress_achieved_percent}%"

        return (
            f"| {project_action} | {stakeholders} | {deadline_planned} | "
            f"{deadline_achieved} | {progress_planned} | {progress_achieved} |"
        )

    def add_activities_to_kr_description(self, kr_iid: int, new_activities: List[Activity]) -> str:
        # Adds activities as table rows to a KR description.
        # Appends to the end, assuming table is the last element or not present.
        # Returns the updated description string.
        try:
            # Fetch the current KR issue
            # Note: The gitlab_service.get_issue might raise an exception if not found.
            # This should be handled by the caller (router) or here if we want specific error messages.
            kr_issue = self.gitlab_service.get_issue(kr_iid)
            current_description = kr_issue.description or ""

            activity_rows_to_add = []
            for act in new_activities:
                activity_rows_to_add.append(self._serialize_activity_to_table_row(act))

            new_rows_string = "\n".join(activity_rows_to_add)

            # Logic to append:
            # If current_description is empty, or doesn't have a table, we might need to add headers.
            # For now, this simple append assumes headers are managed by the template or client.
            # A more robust solution would check for existing table/headers.
            if current_description.strip():
                # Ensure there's a newline before adding new rows if description is not empty
                updated_description = current_description.rstrip() + "\n" + new_rows_string
            else:
                # If the description is empty, ideally, we should add the Markdown table header.
                # For example:
                # header = "| Ação do Projeto/Atividade | Partes Interessadas | Prazo Planejado | Prazo Realizado | % Progresso Planejado | % Progresso Realizado |\n"
                # header += "|---|---|---|---|---|---|\n"
                # updated_description = header + new_rows_string
                # For now, keeping it simple as per the version in setup script of subtask 9:
                updated_description = new_rows_string


            self.gitlab_service.update_issue(
                issue_iid=kr_iid,
                description=updated_description
            )

            return updated_description # Return the full new description

        except Exception as e:
            # print(f"Error adding activities to KR {kr_iid} description: {e}") # Avoid print in service
            # Re-raise allowing router to handle it or wrap in a custom service exception
            raise

    # get_activities_for_kr method (parsing table) is omitted as per subtask 9.
    # Implementing a robust Markdown table parser is complex.

# Instantiate the service for use by routers
activity_service = ActivityService()
