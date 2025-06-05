from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # For form data username/password
from typing import Any # For type hinting flexibility if needed

from app.security import create_access_token, Token # Import from app.security
# from app.models import User # Not strictly needed for this simple /token endpoint yet

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # In a real application, you would verify form_data.username and form_data.password
    # against a database of users.
    # For this example, we'll use a hardcoded user for demonstration.
    # You could also add basic password checking with passlib if you want to extend this.

    # Hardcoded user check (example)
    # Replace with actual user verification logic later
    if form_data.username == "testuser" and form_data.password == "testpass":
        # The 'sub' (subject) of the token is typically the username or user ID.
        access_token = create_access_token(
            data={"sub": form_data.username}
            # You can add more claims to the token data here if needed
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Example of how to get user from DB (for future reference, not for this step):
# async def get_user_from_db(username: str) -> Optional[UserInDB]:
#     # Replace with your actual database query
#     if username in fake_users_db:
#         user_dict = fake_users_db[username]
#         return UserInDB(**user_dict)
#     return None
