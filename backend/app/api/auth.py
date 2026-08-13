"""
Authentication routes - Login, Register, Token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import secrets

from app.database import get_db
from app.models import Organization, TeamMembership, TeamRole, User, UserRole, PasswordResetToken
from app.schemas import UserCreate, UserResponse, Token, ForgotPasswordRequest, ResetPasswordRequest
from app.config import settings

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
login_failures: dict[str, list[datetime]] = {}
password_reset_requests: dict[str, list[datetime]] = {}


def get_login_rate_limit_key(username: str) -> str:
    return (username or "").strip().lower()


def prune_login_failures(key: str, now: datetime) -> list[datetime]:
    window_started_at = now - timedelta(seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    failures = [failed_at for failed_at in login_failures.get(key, []) if failed_at >= window_started_at]
    if failures:
        login_failures[key] = failures
    else:
        login_failures.pop(key, None)
    return failures


def enforce_login_rate_limit(username: str) -> None:
    key = get_login_rate_limit_key(username)
    failures = prune_login_failures(key, datetime.utcnow())
    if len(failures) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": str(settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)},
        )


def record_failed_login(username: str) -> None:
    key = get_login_rate_limit_key(username)
    failures = prune_login_failures(key, datetime.utcnow())
    failures.append(datetime.utcnow())
    login_failures[key] = failures


def clear_failed_login(username: str) -> None:
    login_failures.pop(get_login_rate_limit_key(username), None)


def enforce_password_reset_rate_limit(username: str) -> None:
    """Limit password reset requests per email to prevent email bombing."""
    key = get_login_rate_limit_key(username)
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    requests = [ts for ts in password_reset_requests.get(key, []) if ts >= hour_ago]
    if len(requests) >= settings.PASSWORD_RESET_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please try again later.",
        )
    requests.append(now)
    password_reset_requests[key] = requests


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def create_password_reset_token(db: Session, user: User) -> PasswordResetToken:
    """Create a fresh one-time password reset token for a user."""
    token = generate_password_reset_token()

    # Invalidate any prior unused tokens for this user.
    now = datetime.utcnow()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now})

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token(token),
        expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(reset_token)
    db.commit()
    return token, reset_token


def validate_password_reset_token(db: Session, token: str) -> User:
    """Validate a reset token and return its user, revoking on use."""
    token_hash = hash_password_reset_token(token)
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    if reset_token.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has already been used")
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

    reset_token.used_at = datetime.utcnow()
    db.commit()
    return user


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_user_token_payload(user: User) -> dict:
    return {
        "sub": str(user.id),
        "role": user.role.value,
        "token_version": user.token_version or 0,
    }


def validate_token_version(payload: dict, user: User) -> None:
    if int(payload.get("token_version", -1)) != (user.token_version or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")


def get_token_subject(payload: dict) -> int:
    subject = payload.get("sub")
    if subject is None:
        raise ValueError("Missing token subject")
    return int(subject)


def get_user_from_token(token: str, db: Session) -> User:
    """Validate a raw bearer access token and return the authenticated user.

    Shared by HTTP dependency auth and WebSocket token auth so the same
    validation rules apply to both transports.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = get_token_subject(payload)
        if payload.get("type") != "access":
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    validate_token_version(payload, user)
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    return get_user_from_token(token, db)


def require_role(*roles: UserRole):
    """Dependency to require specific user roles"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=UserRole(user_data.role),
        company_name=user_data.company_name,
        phone=user_data.phone
    )
    
    db.add(new_user)
    db.flush()

    if new_user.role == UserRole.EMPLOYER:
        organization = Organization(
            name=user_data.company_name or f"{user_data.full_name}'s Organization"
        )
        db.add(organization)
        db.flush()
        db.add(TeamMembership(
            organization_id=organization.id,
            user_id=new_user.id,
            role=TeamRole.OWNER
        ))

    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    enforce_login_rate_limit(form_data.username)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        record_failed_login(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    clear_failed_login(form_data.username)
    
    access_token = create_access_token(data=create_user_token_payload(user))
    refresh_token = create_refresh_token(data=create_user_token_payload(user))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token"""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = get_token_subject(payload)
        token_type: str = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    validate_token_version(payload, user)
    
    new_access_token = create_access_token(data=create_user_token_payload(user))
    new_refresh_token = create_refresh_token(data=create_user_token_payload(user))
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset link, sent to the account email."""
    enforce_password_reset_rate_limit(request.email)

    user = db.query(User).filter(User.email == request.email).first()

    # Respond identically whether or not the address is registered, so the
    # endpoint cannot be used to enumerate accounts.
    response_message = "If that email is registered, a password reset link has been sent."

    if user is None or not user.is_active:
        return {"message": response_message}

    token, _reset_record = create_password_reset_token(db, user)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    from app.services.email_service import send_password_reset_email
    await send_password_reset_email(user.email, reset_link)

    return {"message": response_message}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset a user's password using a one-time token."""
    user = validate_password_reset_token(db, request.token)

    if not request.new_password or len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    user.hashed_password = get_password_hash(request.new_password)
    # Revoke any existing sessions.
    user.token_version = (user.token_version or 0) + 1
    db.commit()

    return {"message": "Password has been reset successfully. You can now sign in."}
