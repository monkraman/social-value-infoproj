import threading
import time
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate
from app.core.security import (
    hash_password,
    verify_password,
    needs_rehash,
    create_access_token,
    validate_password_strength,
)


class LoginLocked(Exception):
    """Too many failed sign-ins for this email; retry after `retry_after` seconds."""

    def __init__(self, retry_after: int):
        super().__init__(f"Too many failed sign-in attempts. Try again in {max(1, retry_after // 60)} minutes.")
        self.retry_after = retry_after


class _FailedLoginTracker:
    """In-process lockout after repeated failures (per email). Resets on success or after the lockout."""

    def __init__(self):
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}

    def check(self, key: str) -> None:
        with self._lock:
            until = self._locked_until.get(key, 0)
            if until > time.time():
                raise LoginLocked(int(until - time.time()))

    def fail(self, key: str) -> None:
        window = settings.LOGIN_LOCKOUT_MINUTES * 60
        now = time.time()
        with self._lock:
            recent = [t for t in self._failures.get(key, []) if now - t < window] + [now]
            self._failures[key] = recent
            if len(recent) >= settings.LOGIN_MAX_FAILURES:
                self._locked_until[key] = now + window
                self._failures[key] = []

    def success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)


login_tracker = _FailedLoginTracker()


class AuthService:
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower().strip()).first()

    def get_by_id(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def register(self, db: Session, req: UserCreate) -> User:
        if self.get_by_email(db, req.email):
            raise ValueError("A user with this email already exists.")

        user = User(
            name=req.name.strip(),
            email=req.email.lower().strip(),
            password_hash=hash_password(req.password),
            role=req.role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate(self, db: Session, email: str, password: str) -> Optional[User]:
        key = email.lower().strip()
        login_tracker.check(key)
        user = self.get_by_email(db, key)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            login_tracker.fail(key)
            return None
        login_tracker.success(key)
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            db.commit()
        return user

    def change_password(self, db: Session, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")
        if verify_password(new_password, user.password_hash):
            raise ValueError("New password must be different from the current one.")
        validate_password_strength(new_password, email=user.email, name=user.name)
        user.password_hash = hash_password(new_password)
        db.commit()

    def create_token_for_user(self, user: User) -> str:
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        }
        return create_access_token(payload)

    def bootstrap_initial_admin(self, db: Session) -> Optional[User]:
        """Creates the first superadmin from INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD,
        only when the users table is empty. There is no built-in default account."""
        if db.query(User).first() is not None:
            return None
        email, password = settings.INITIAL_ADMIN_EMAIL, settings.INITIAL_ADMIN_PASSWORD
        if not email or not password:
            print("[Auth] No users exist. Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD, "
                  "or run scripts/seed_users.py, to create the first superadmin.")
            return None
        validate_password_strength(password, email=email)
        admin = User(
            name="Social Value Administrator",
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role="superadmin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"[Auth] Created initial superadmin {admin.email}.")
        return admin


auth_service = AuthService()
