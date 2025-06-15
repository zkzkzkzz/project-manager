import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.db.apply_schema import Base, get_db
from backend.main import app
import backend.models.sql_models as db_models
from backend.core.s3_utils import s3_store

from typing import Generator

from backend.core.security import create_access_token, hash_password

os.environ["JWT_KEY"] = "test_jwt_key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["AWS_ACCESS_KEY_ID"] = "test_access"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test_secret"
os.environ["AWS_S3_ENDPOINT_URL"] = "http://localhost:9000"

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    if os.path.exists("./test.db"):
        os.remove("./test.db")

    print("[DB Setup] Creating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[DB Setup] Tables created.")

    yield
    print("[DB Setup] Test session finished.")


@pytest.fixture(scope="function", autouse=True)
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    print(f"\n[DB] Session {id(session)} created, TX started.")
    try:
        yield session

    finally:
        print(f"[DB] Rolling back session {id(session)}.")
        session.close()
        transaction.rollback()
        connection.close()
        print(f"[DB] Session {id(session)} rollback/closed.")


@pytest.fixture(scope="function")
def test_user(db_session) -> db_models.User:  # Use the clean session
    user_data = {"login": "testuser@fixture.com", "password": "Password123"}
    # Check if user ALREADY exists (shouldn't happen with proper rollback)

    hashed_password = hash_password(user_data["password"])
    user = db_models.User(login=user_data["login"], hashed_password=hashed_password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    # Store plain password for login simulation (not ideal, but works for this setup)
    user.plain_password = user_data["password"]
    print(f"[User] Created test_user ID: {user.id}")
    return user


@pytest.fixture(scope="function")
def other_user(db_session) -> db_models.User:
    user_data = {"login": "otheruser@fixture.com", "password": "Password123"}

    hashed_password = hash_password(user_data["password"])
    user = db_models.User(login=user_data["login"], hashed_password=hashed_password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    user.plain_password = user_data["password"]
    print(f"[User] Created other_user ID: {user.id}")
    return user


@pytest.fixture(scope="function")
def token(test_user) -> str:
    return create_access_token(subject=test_user.login)


@pytest.fixture(scope="function")
def other_token(other_user: db_models.User) -> str:  # Add type hints
    """Generates JWT for the secondary test user."""
    return create_access_token(subject=other_user.login)


@pytest.fixture(scope="function", autouse=True)
def apply_db_override(db_session: Session):
    """Auto-applied fixture to override DB for all function-scoped tests."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    print(f"[Override] DB override set for session {id(db_session)}")
    yield  # Let tests run
    del app.dependency_overrides[get_db]
    print(f"[Override] DB override removed for session {id(db_session)}")


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Provides a basic TestClient (DB override applied by autouse fixture)."""
    _client = TestClient(app)
    print(f"[Client] Created unauth client {id(_client)}")
    return _client  # Return the new instance


@pytest.fixture(scope="function")
def authorized_client(token: str):
    _client = TestClient(app)  # Create NEW instance
    _client.headers["Authorization"] = f"Bearer {token}"  # Set header on NEW instance
    print(f"[Client] Created auth client {id(_client)} for test_user")
    return _client  # Return the new instance


@pytest.fixture(scope="function")
def other_authorized_client(other_token: str):
    _client = TestClient(app)  # Create NEW instance
    _client.headers["Authorization"] = (
        f"Bearer {other_token}"  # Set header on NEW instance
    )
    print(f"[Client] Created auth client {id(_client)} for other_user")
    return _client  # Return the new instance


@pytest.fixture(scope="function")
def third_user(db_session) -> db_models.User:
    user_data = {"login": "thirduser@fixture.com", "password": "Password123"}
    hashed_password = hash_password(user_data["password"])
    user = db_models.User(login=user_data["login"], hashed_password=hashed_password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    user.plain_password = user_data["password"]
    return user


@pytest.fixture(scope="function")
def third_token(third_user) -> str:
    return create_access_token(subject=third_user.login)


@pytest.fixture(scope="function")
def third_authorized_client(third_token: str, client: TestClient):
    client.headers["Authorization"] = f"Bearer {third_token}"
    return client


class MockS3Upload:
    def __init__(self):
        self.call_count = 0

    def __call__(self, file, project_id):
        self.call_count += 1
        return f"fake_key_proj_{project_id}_call_{self.call_count}"


@pytest.fixture(autouse=True)
def patch_s3_store(monkeypatch):
    mock_uploader = MockS3Upload()
    monkeypatch.setattr(s3_store, "upload", mock_uploader)
    monkeypatch.setattr(
        s3_store, "presign", lambda key: f"https://fake-minio.local/{key}?sig"
    )
    monkeypatch.setattr(s3_store, "delete", lambda key: True)
    yield
