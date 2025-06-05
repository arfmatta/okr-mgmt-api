from datetime import datetime, timedelta, timezone # Ensure timezone is imported
from typing import Optional, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt # type: ignore # jose is not fully typed, ignore for mypy if needed
from pydantic import BaseModel

from app.config import settings # To access SECRET_KEY, ALGORITHM, etc.
from app.models import User # Add this import at the top of app/security.py if not already there

# --- Pydantic Models for Token Data ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None # Or 'sub' or 'user_id'

# --- OAuth2 Scheme ---
# tokenUrl should point to the endpoint that provides the token (e.g., /auth/token)
# We'll create this endpoint later.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- Token Creation ---
def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- Dependency to Get Current User from Token ---
async def get_current_user_payload(token: str = Depends(oauth2_scheme)) -> Dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: Optional[str] = payload.get("sub") # Assuming subject ('sub') stores the username
        if username is None:
            # Fallback or alternative: check for a 'username' claim directly if 'sub' isn't used
            username = payload.get("username")
            if username is None:
                raise credentials_exception # No identifiable user claim

        # For now, we just care about the payload containing an identifier
        # In a real app, you might use TokenData model here:
        # token_data = TokenData(username=username)
        # And potentially fetch a user object from DB.
        # Here, we'll return the raw payload for now, or just the username.
        # Let's return the whole payload for flexibility, the caller can extract 'sub' or 'username'.
        return payload

    except JWTError:
        raise credentials_exception
    except Exception: # Catch any other error during decoding as unauthorized
        raise credentials_exception

# Note: A more complete get_current_user would typically return a User model instance.
# For this step, get_current_user_payload returning the payload dict is sufficient.
# We will add a User model and a refined get_current_user in the next steps.

async def get_current_active_user(payload: Dict = Depends(get_current_user_payload)) -> User:
    username = payload.get("sub") # Assuming 'sub' claim holds the username
    if username is None:
        username = payload.get("username") # Fallback to 'username' claim
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, # Or 403 if token is valid but user info missing
                detail="Could not validate user from token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return User(username=username)
