from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import SessionLocal
from app.models.entities import Role, User


def run():
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.username == "admin")) is not None:
            return

        db.add(User(
            username="admin",
            full_name="Quản trị hệ thống",
            email="admin@example.com",
            password_hash=hash_password(settings.admin_initial_password),
            role=Role.ADMIN,
        ))
        db.commit()


if __name__ == "__main__":
    run()
