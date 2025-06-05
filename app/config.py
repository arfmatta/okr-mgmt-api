from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Any
from pydantic import field_validator, Field # For Pydantic v2 features

class Settings(BaseSettings):
    gitlab_api_url: str = "https://gitlab.com"
    gitlab_access_token: str
    gitlab_project_id: str # Should be the numeric ID

    # These will be loaded as comma-separated strings from .env
    # and then converted to List[str].
    # Using Field(..., alias=...) allows the .env variable name to be different from the Python attribute name.
    gitlab_objective_labels_str: str = Field(alias="GITLAB_OBJECTIVE_LABELS", default="")
    gitlab_kr_labels_str: str = Field(alias="GITLAB_KR_LABELS", default="")

    # These will hold the processed list of strings
    gitlab_objective_labels: List[str] = []
    gitlab_kr_labels: List[str] = []

    # The field_validator for the _str fields is primarily to handle the 'default' if the env var is missing.
    # pydantic-settings itself will load existing env vars as strings.
    # This validator mainly ensures that if the env var is not set, the default="" is processed as a string.
    @field_validator('gitlab_objective_labels_str', 'gitlab_kr_labels_str', mode='before')
    @classmethod
    def _ensure_str_from_env(cls, value: Any) -> str:
        # If the value comes from .env, it's already a string.
        # If it's from a default or other source and could be None.
        if value is None:
            return ""
        return str(value) # Ensure it's a string

    # model_post_init is called after the model is initialized with values from all sources (env, defaults, etc.)
    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context) # It's good practice to call super()

        if self.gitlab_objective_labels_str: # Check if the string has content
            # Split by comma, strip whitespace from each part, and filter out empty strings
            self.gitlab_objective_labels = [label.strip() for label in self.gitlab_objective_labels_str.split(',') if label.strip()]
        else:
            self.gitlab_objective_labels = [] # Default to empty list if string is empty

        if self.gitlab_kr_labels_str: # Check if the string has content
            self.gitlab_kr_labels = [label.strip() for label in self.gitlab_kr_labels_str.split(',') if label.strip()]
        else:
            self.gitlab_kr_labels = [] # Default to empty list if string is empty

    model_config = SettingsConfigDict(
        env_file=".env",        # Load from .env file
        env_file_encoding='utf-8', # Specify encoding for .env file
        extra='ignore'          # Ignore any extra fields loaded from .env
    )

# Create a global instance of the settings to be used by other modules
settings = Settings()

# Example of how to see loaded settings (for local debugging)
# if __name__ == "__main__":
#     print(f"Loaded settings via app.config:")
#     print(f"  GITLAB_API_URL: {settings.gitlab_api_url}")
#     print(f"  GITLAB_PROJECT_ID: {settings.gitlab_project_id}")
#     print(f"  GITLAB_OBJECTIVE_LABELS_STR (from env): '{settings.gitlab_objective_labels_str}'")
#     print(f"  GITLAB_OBJECTIVE_LABELS (parsed list): {settings.gitlab_objective_labels}")
#     print(f"  GITLAB_KR_LABELS_STR (from env): '{settings.gitlab_kr_labels_str}'")
#     print(f"  GITLAB_KR_LABELS (parsed list): {settings.gitlab_kr_labels}")
#     print(f"  GITLAB_ACCESS_TOKEN is set: {'Yes' if settings.gitlab_access_token else 'No'}")
