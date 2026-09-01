import os
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import bcrypt
from dotenv import load_dotenv

try:
    from backend.app.database.connection import get_db
    from backend.app.models.models import User
    from backend.app.schemas.schemas import TokenData
except ModuleNotFoundError:
    from app.database.connection import get_db
    from app.models.models import User
    from app.schemas.schemas import TokenData

load_dotenv()

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-resume-analyzer-key-1234-9876")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# OAuth2 Scheme for Swagger UI API testing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify standard text password against hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode JWT token to retrieve credentials."""
    try:
        if not isinstance(token, str):
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        is_admin: bool = payload.get("is_admin", False)
        
        if email is None or user_id is None:
            return None
        return TokenData(email=email, user_id=user_id, is_admin=is_admin)
    except Exception:
        return None

def get_token_from_request(request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Extract token from either:
    1. HTTPOnly Cookie named 'access_token' (used by frontend web views)
    2. Authorization header (Bearer token, used by Swagger and API consumers)
    """
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        # If stored as 'Bearer <token>' in cookies
        if cookie_token.startswith("Bearer "):
            return cookie_token.split(" ")[1]
        return cookie_token
    if isinstance(token, str):
        return token
    return None

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_token_from_request)
) -> User:
    """Retrieve the current logged-in user or raise/redirect on credentials failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_101_SWITCHING_PROTOCOLS, # Standard fallback
        detail="Could not validate credentials",
    )
    
    # Check if request is HTML to redirect to login page instead of raising 401
    is_html_request = "text/html" in request.headers.get("accept", "")

    if not token:
        if is_html_request:
            raise HTMLUnauthorizedException()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = decode_access_token(token)
    if token_data is None:
        if is_html_request:
            raise HTMLUnauthorizedException()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        if is_html_request:
            raise HTMLUnauthorizedException()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    return user

def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure current logged-in user is an administrator."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Admin privilege required."
        )
    return current_user

class HTMLUnauthorizedException(Exception):
    """Custom exception raised when HTML web client fails authorization."""
    pass
