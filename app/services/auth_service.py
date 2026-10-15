import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.auth import UserCreate
from app.core.security import hash_password, verify_password, create_access_token


class AuthService:
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower().strip()).first()

    def get_by_id(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def register(self, db: Session, req: UserCreate) -> User:
        existing = self.get_by_email(db, req.email)
        if existing:
            raise ValueError(f"User with email '{req.email}' already exists.")

        user = User(
            name=req.name.strip(),
            email=req.email.lower().strip(),
            password_hash=hash_password(req.password),
            role=req.role or "superadmin",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate(self, db: Session, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    def create_token_for_user(self, user: User) -> str:
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
        return create_access_token(payload)

    def ensure_default_superadmin(self, db: Session) -> User:
        """Provisions default superadmin if no users exist in database."""
        default_email = "admin@infosys.com"
        admin = self.get_by_email(db, default_email)
        if not admin:
            admin = User(
                name="Infosys Superadmin",
                email=default_email,
                password_hash=hash_password("admin123"),
                role="superadmin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("[Auth] Initialized default superadmin: admin@infosys.com (password: admin123)")
        return admin


auth_service = AuthService()
