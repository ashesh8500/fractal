"""
SQLite-backed storage for portfolios and users using SQLAlchemy.
Stores portfolios (name, holdings as JSON string) and users (username, password hash, admin flag).
"""
from __future__ import annotations
import json
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB_URL = "sqlite:///db.sqlite"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class PortfolioRecord(Base):
    __tablename__ = "portfolios"
    name = Column(String(100), primary_key=True, index=True)
    holdings_json = Column(Text, nullable=False, default="{}")

    @property
    def holdings(self) -> Dict[str, float]:
        try:
            return json.loads(self.holdings_json or "{}")
        except Exception:
            return {}

    @holdings.setter
    def holdings(self, value: Dict[str, float]) -> None:
        self.holdings_json = json.dumps(value or {})


class UserRecord(Base):
    __tablename__ = "users"
    username = Column(String(100), primary_key=True, index=True)
    password_hash = Column(Text, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_public(self) -> Dict:
        return {
            "username": self.username,
            "is_admin": bool(self.is_admin),
            "created_at": self.created_at,
        }

    def to_internal(self) -> Dict:
        # Includes password_hash for internal use only
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "is_admin": bool(self.is_admin),
            "created_at": self.created_at,
        }


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


# -----------------------
# Portfolio CRUD helpers
# -----------------------
def upsert_portfolio(name: str, holdings: Dict[str, float]) -> Dict:
    with get_session() as db:
        rec = db.get(PortfolioRecord, name)
        if rec is None:
            rec = PortfolioRecord(name=name)
        rec.holdings = holdings
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return {"name": rec.name, "holdings": rec.holdings}


def get_portfolio(name: str) -> Optional[Dict]:
    with get_session() as db:
        rec = db.get(PortfolioRecord, name)
        if rec is None:
            return None
        return {"name": rec.name, "holdings": rec.holdings}


def list_portfolios() -> List[Dict]:
    with get_session() as db:
        rows = db.query(PortfolioRecord).all()
        return [{"name": r.name, "holdings": r.holdings} for r in rows]


def delete_portfolio(name: str) -> bool:
    with get_session() as db:
        rec = db.get(PortfolioRecord, name)
        if rec is None:
            return False
        db.delete(rec)
        db.commit()
        return True


# -----------------------
# User CRUD helpers
# -----------------------
def create_user(username: str, password_hash: str, is_admin: bool = False) -> Dict:
    """
    Create a new user storing the provided password_hash (already hashed).
    Returns public user dict.
    """
    with get_session() as db:
        existing = db.get(UserRecord, username)
        if existing is not None:
            raise ValueError(f"User '{username}' already exists")
        rec = UserRecord(
            username=username,
            password_hash=password_hash,
            is_admin=bool(is_admin),
            created_at=datetime.utcnow(),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.to_public()


def get_user_internal(username: str) -> Optional[Dict]:
    """
    Return internal representation including password_hash (for authentication).
    """
    with get_session() as db:
        rec = db.get(UserRecord, username)
        if rec is None:
            return None
        return rec.to_internal()


def get_user_public(username: str) -> Optional[Dict]:
    """
    Return public user representation (no password).
    """
    with get_session() as db:
        rec = db.get(UserRecord, username)
        if rec is None:
            return None
        return rec.to_public()


def list_users_public() -> List[Dict]:
    with get_session() as db:
        rows = db.query(UserRecord).all()
        return [r.to_public() for r in rows]


def update_user(username: str, password_hash: Optional[str] = None, is_admin: Optional[bool] = None) -> Optional[Dict]:
    """
    Update user's password_hash and/or is_admin flag.
    password_hash should be a hashed password (not plaintext).
    Returns public user dict or None if user not found.
    """
    with get_session() as db:
        rec = db.get(UserRecord, username)
        if rec is None:
            return None
        if password_hash is not None:
            rec.password_hash = password_hash
        if is_admin is not None:
            rec.is_admin = bool(is_admin)
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.to_public()


def delete_user(username: str) -> bool:
    with get_session() as db:
        rec = db.get(UserRecord, username)
        if rec is None:
            return False
        db.delete(rec)
        db.commit()
        return True
