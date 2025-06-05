import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError # type: ignore
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer


# Modules to be tested (assuming they are in app.security)
# Need to adjust path if running tests from a different directory or using a specific test runner setup
# For now, assume app is on PYTHONPATH
from app import security # This imports app.security
from app.config import Settings # To override settings for testing
from app.models import User # User model for get_current_active_user

class TestSecurity(unittest.TestCase):

    def setUp(self):
        # Use a consistent set of test settings for JWT
        self.test_settings = Settings(
            SECRET_KEY="test_secret_key_for_unit_tests",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=15,
            # Dummy values for other required settings in your Settings model
            gitlab_api_url="http://fake.gitlab",
            gitlab_access_token="fake_token",
            gitlab_project_id="fake_project_id"
        )
        self.settings_patcher = patch('app.security.settings', self.test_settings)
        self.mock_settings = self.settings_patcher.start()

    def tearDown(self):
        self.settings_patcher.stop()

    def test_create_access_token(self):
        username = "testuser"
        token_data = {"sub": username}

        # Test with default expiry
        token_default_expiry = security.create_access_token(data=token_data)
        payload_default = jwt.decode(token_default_expiry, self.test_settings.SECRET_KEY, algorithms=[self.test_settings.ALGORITHM])
        self.assertEqual(payload_default["sub"], username)
        self.assertTrue("exp" in payload_default)

        # Test with custom expiry
        custom_delta = timedelta(minutes=5)
        token_custom_expiry = security.create_access_token(data=token_data, expires_delta=custom_delta)
        payload_custom = jwt.decode(token_custom_expiry, self.test_settings.SECRET_KEY, algorithms=[self.test_settings.ALGORITHM])
        self.assertEqual(payload_custom["sub"], username)
        # Check if expiry is roughly correct (allowing for small processing delay)
        expected_exp_time = datetime.now(timezone.utc) + custom_delta
        actual_exp_time = datetime.fromtimestamp(payload_custom["exp"], tz=timezone.utc)
        self.assertAlmostEqual(actual_exp_time, expected_exp_time, delta=timedelta(seconds=5))

    async def test_get_current_active_user_success(self):
        username = "test_user_from_token"
        # Create a valid token for testing get_current_active_user
        # get_current_active_user depends on get_current_user_payload, which uses oauth2_scheme
        # We need to mock the result of get_current_user_payload

        mock_payload = {"sub": username}

        # Create a mock dependency for get_current_user_payload
        async def mock_get_user_payload():
            return mock_payload

        # Patch the dependency within the security module where get_current_active_user is defined
        with patch('app.security.get_current_user_payload', new=mock_get_user_payload):
            user = await security.get_current_active_user() # Call with patched dependency
            self.assertIsInstance(user, User)
            self.assertEqual(user.username, username)

    async def test_get_current_active_user_no_sub_or_username_in_payload(self):
        # Mock payload without 'sub' or 'username'
        mock_payload = {"other_claim": "some_value"}

        async def mock_get_user_payload_empty():
            return mock_payload

        with patch('app.security.get_current_user_payload', new=mock_get_user_payload_empty):
            with self.assertRaises(HTTPException) as context:
                await security.get_current_active_user()
            self.assertEqual(context.exception.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertIn("Could not validate user from token payload", context.exception.detail)

    # Note: Testing get_current_user_payload directly is more involved as it depends on
    # oauth2_scheme which expects a real request or a mock request context.
    # For unit tests, focusing on create_access_token and the logic within
    # get_current_active_user (assuming get_current_user_payload works) is often pragmatic.
    # To test get_current_user_payload itself, you might need to mock Depends(oauth2_scheme)
    # or use a TestClient approach if it's tightly coupled to request state.

if __name__ == '__main__':
    unittest.main()
