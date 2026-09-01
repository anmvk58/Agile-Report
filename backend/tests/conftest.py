import os
os.environ["DATABASE_URL"]="sqlite:///./test.db"
os.environ["JWT_SECRET_KEY"]="test-secret"
import pytest
from fastapi.testclient import TestClient
from app.db.base import Base,SessionLocal,engine
from app.core.security import hash_password
from app.main import app
from app.models.entities import Role,User

@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    db=SessionLocal()
    db.add_all([User(username="admin",full_name="Admin",email="admin@example.com",password_hash=hash_password("Password1!"),role=Role.ADMIN),User(username="member",full_name="Member",email="member@example.com",password_hash=hash_password("Password1!"),role=Role.MEMBER),User(username="inactive",full_name="Inactive",email="inactive@example.com",password_hash=hash_password("Password1!"),role=Role.MEMBER,is_active=False)])
    db.commit(); db.close(); yield; Base.metadata.drop_all(engine)

@pytest.fixture
def client(): return TestClient(app)
@pytest.fixture
def admin_headers(client): return {"Authorization":"Bearer "+client.post("/api/auth/login",json={"username":"admin","password":"Password1!"}).json()["access_token"]}
@pytest.fixture
def member_headers(client): return {"Authorization":"Bearer "+client.post("/api/auth/login",json={"username":"member","password":"Password1!"}).json()["access_token"]}
