import sys
from unittest.mock import MagicMock

print("Executing tests/unit/__init__.py for monkeypatching (v3)...")

try:
    # Step 1: Import the library module
    import gitlab
    print("Imported gitlab library.")

    # Step 2: Store the original library class
    ORIGINAL_LIBRARY_GITLAB = gitlab.Gitlab
    print(f"Stored ORIGINAL_LIBRARY_GITLAB: {ORIGINAL_LIBRARY_GITLAB}")

    # Step 3: Monkeypatch the library class *before* our service module imports it
    gitlab.Gitlab = MagicMock(spec=ORIGINAL_LIBRARY_GITLAB)
    print(f"Monkeypatched gitlab.Gitlab. It is now: {gitlab.Gitlab}")
    # Ensure its return_value.auth is also a MagicMock
    if hasattr(gitlab.Gitlab.return_value, 'auth'):
         gitlab.Gitlab.return_value.auth = MagicMock()


    # Step 4: Import the parent package of the service module
    import app.services
    print("Imported app.services package.")
    # Now, access the specific module app.services.gitlab_service
    # This should execute the module-level code in gitlab_service.py,
    # including gitlab_service = GitlabService(), which uses the patched gitlab.Gitlab.
    # Forcing a specific reference to the module, in case of weird import cache behavior
    _gitlab_service_module = sys.modules['app.services.gitlab_service']
    print(f"Accessed app.services.gitlab_service module: {_gitlab_service_module}")


    # Step 5: Store the original application service wrapper class from the module
    ORIGINAL_APP_GITLAB_SERVICE = _gitlab_service_module.GitlabService
    print(f"Stored ORIGINAL_APP_GITLAB_SERVICE: {ORIGINAL_APP_GITLAB_SERVICE}")

    # Step 6: Monkeypatch our application service wrapper class in that module's namespace
    _gitlab_service_module.GitlabService = MagicMock(spec=ORIGINAL_APP_GITLAB_SERVICE)
    print(f"Monkeypatched _gitlab_service_module.GitlabService. It is now: {_gitlab_service_module.GitlabService}")

    print("Monkeypatching complete in tests/unit/__init__.py (v3).")

except ImportError as e:
    print(f"Error importing modules for monkeypatching in tests/unit/__init__.py (v3): {e}", file=sys.stderr)
    raise e
except Exception as e:
    print(f"Unexpected error during monkeypatching in tests/unit/__init__.py (v3): {e}", file=sys.stderr)
    print(f"Type of app.services.gitlab_service: {type(app.services.gitlab_service)}", file=sys.stderr)
    if 'app.services.gitlab_service' in sys.modules:
        print(f"Contents of sys.modules['app.services.gitlab_service']: {dir(sys.modules['app.services.gitlab_service'])}", file=sys.stderr)
    raise e
