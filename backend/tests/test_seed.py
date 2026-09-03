import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import seed
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models.entities import Role, User


@pytest.fixture
def seed_sessions(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(seed, "SessionLocal", sessions)
    monkeypatch.setattr(seed.settings, "admin_initial_password", "SeedTest123!")
    yield sessions
    engine.dispose()


def test_seed_only_creates_admin(seed_sessions):
    seed.run()
    with seed_sessions() as db:
        admin = db.scalars(select(User)).one()
        assert admin.username == "admin"
        assert admin.role == Role.ADMIN
        assert verify_password("SeedTest123!", admin.password_hash)
        for table in Base.metadata.sorted_tables:
            if table.name != "users":
                assert db.scalar(select(func.count()).select_from(table)) == 0


def test_seed_rerun_preserves_existing_admin(seed_sessions):
    seed.run()
    with seed_sessions() as db:
        admin = db.scalars(select(User)).one()
        admin.password_hash = hash_password("ChangedPass123!")
        admin.full_name = "Existing Admin"
        admin.is_active = False
        db.commit()
        previous_hash = admin.password_hash
    seed.run()
    with seed_sessions() as db:
        admin = db.scalars(select(User)).one()
        assert admin.password_hash == previous_hash
        assert admin.full_name == "Existing Admin"
        assert admin.is_active is False


def test_seed_adds_missing_admin_without_changing_other_users(seed_sessions):
    with seed_sessions() as db:
        db.add(User(username="existing", full_name="Existing Member", email="existing@example.com", password_hash=hash_password("MemberTest123!"), role=Role.MEMBER))
        db.commit()
    seed.run()
    seed.run()
    with seed_sessions() as db:
        users = db.scalars(select(User).order_by(User.username)).all()
        assert [user.username for user in users] == ["admin", "existing"]
        assert users[1].full_name == "Existing Member"
        assert verify_password("MemberTest123!", users[1].password_hash)
