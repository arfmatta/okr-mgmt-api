import re
from typing import List
from app.services import gitlab_service # Use the shared gitlab_service instance
from app.models import Activity, KRCreateRequest, KRResponse # Assuming models are in app.models
# We might need KRService to get KRs, or just use gitlab_service directly if we have KR's IID
# from app.services.kr_service import kr_service # Avoid circular dependency if KRService uses ActivityService

# Define a clear marker for the activities section in Markdown
ACTIVITIES_HEADER = "\n\n--- Activities ---\n"
ACTIVITY_LINE_REGEX = re.compile(
    r"-\sProject/Action:\s*(?P<project_action_activity>.+?)\s*;\s*"
    r"Stakeholders:\s*(?P<stakeholders>.+?)\s*;\s*"
    r"Deadline Planned:\s*(?P<deadline_planned>.+?)\s*;\s*"
    r"Deadline Achieved:\s*(?P<deadline_achieved>.*?)\s*;\s*" # Non-greedy, can be empty
    r"Progress Planned:\s*(?P<progress_planned_percent>\d+\.?\d*)%\s*;\s*"
    r"Progress Achieved:\s*(?P<progress_achieved_percent>\d+\.?\d*)%\s*"
)
# Example Activity line:
# - Project/Action: Task 1; Stakeholders: Team A; Deadline Planned: Q1/2024; Deadline Achieved: ; Progress Planned: 100%; Progress Achieved: 0%

class ActivityService:
    def __init__(self):
        self.gitlab_service = gitlab_service

    def _serialize_activity(self, activity: Activity) -> str:
        """Serializes a single Activity object to a Markdown list item string."""
        return (
            f"- Project/Action: {activity.project_action_activity}; "
            f"Stakeholders: {activity.stakeholders}; "
            f"Deadline Planned: {activity.deadline_planned}; "
            f"Deadline Achieved: {activity.deadline_achieved or ''}; " # Ensure empty string if None
            f"Progress Planned: {activity.progress_planned_percent}%; "
            f"Progress Achieved: {activity.progress_achieved_percent}%"
        )

    def _parse_activities_from_description(self, description: str) -> List[Activity]:
        """Parses Activity objects from the KR issue's description text."""
        activities: List[Activity] = []
        if ACTIVITIES_HEADER in description:
            activities_text = description.split(ACTIVITIES_HEADER, 1)[1]
            for line in activities_text.strip().split('\n'):
                if line.strip().startswith("-"):
                    match = ACTIVITY_LINE_REGEX.match(line.strip())
                    if match:
                        data = match.groupdict()
                        activities.append(Activity(
                            project_action_activity=data['project_action_activity'],
                            stakeholders=data['stakeholders'],
                            deadline_planned=data['deadline_planned'],
                            deadline_achieved=data['deadline_achieved'] if data['deadline_achieved'] else None,
                            progress_planned_percent=float(data['progress_planned_percent']),
                            progress_achieved_percent=float(data['progress_achieved_percent'])
                        ))
        return activities

    def add_activities_to_kr(self, kr_iid: int, new_activities: List[Activity]) -> List[Activity]:
        """
        Adds a list of activities to a Key Result's description.
        Retrieves the KR, appends new activities to its description, and updates the KR.
        Returns all activities for the KR (old and new).
        """
        try:
            kr_issue = self.gitlab_service.get_issue(kr_iid)
            if not kr_issue:
                raise ValueError(f"KR with IID {kr_iid} not found.")

            current_description = kr_issue.description or ""

            # Separate existing activities text from the main description
            main_description_part = current_description
            activities_text_part = ""

            if ACTIVITIES_HEADER in current_description:
                parts = current_description.split(ACTIVITIES_HEADER, 1)
                main_description_part = parts[0]
                if len(parts) > 1: # Should always be true if header is present
                    activities_text_part = parts[1]

            # Serialize new activities
            serialized_new_activities = "\n".join([self._serialize_activity(act) for act in new_activities])

            # Combine new activities with existing ones (if any)
            if activities_text_part.strip(): # If there was existing activities text
                updated_activities_text = activities_text_part.strip() + "\n" + serialized_new_activities
            else:
                updated_activities_text = serialized_new_activities

            # Reconstruct the full description
            new_full_description = main_description_part.strip() + ACTIVITIES_HEADER + updated_activities_text.strip()

            self.gitlab_service.update_issue(
                issue_iid=kr_iid,
                description=new_full_description
            )

            # Return all activities (parsed from the updated description)
            return self._parse_activities_from_description(new_full_description)

        except Exception as e:
            print(f"Error adding activities to KR {kr_iid}: {e}") # Replace with actual logging
            raise

    def get_activities_for_kr(self, kr_iid: int) -> List[Activity]:
        """Retrieves and parses activities from a Key Result's description."""
        try:
            kr_issue = self.gitlab_service.get_issue(kr_iid)
            if not kr_issue:
                # Or raise an error, depending on desired behavior
                return []

            return self._parse_activities_from_description(kr_issue.description or "")
        except Exception as e:
            print(f"Error getting activities for KR {kr_iid}: {e}") # Replace with actual logging
            raise

# Instantiate the service
activity_service = ActivityService()
