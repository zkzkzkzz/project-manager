from fastapi.testclient import TestClient


from fastapi import status
from backend.models.sql_models import User


def create_test_project(
    client: TestClient, name: str = "Default test project", desc: str = "Default desc"
):

    response = client.post("/projects/", json={"name": name, "description": desc})

    assert (
        response.status_code == 201
    ), f"Failed to create test project: {response.text}"
    return response.json()["id"]


def test_create_project_success(authorized_client: TestClient, test_user: User):
    project_data = {"name": "Test create fixture", "description": "Desc create fixture"}
    response = authorized_client.post("/projects/", json=project_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == project_data["name"]
    assert data["description"] == project_data["description"]
    assert "id" in data
    assert data["owner_id"] == test_user.id


def test_create_project_unauthorized(client: TestClient):
    project_data = {
        "name": "Unauthorized create",
        "description": "Should fail",
    }

    response = client.post("/projects/", json=project_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_all_projects_success(
    authorized_client: TestClient, other_authorized_client: TestClient
):
    main_proj_id = create_test_project(authorized_client, name="Main user proj")
    other_proj_id = create_test_project(other_authorized_client, name="Other User Proj")
    response = authorized_client.get("/projects/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    project_ids_in_response = {p["id"] for p in data}
    assert main_proj_id in project_ids_in_response
    assert other_proj_id not in project_ids_in_response


def test_get_all_projects_unauthorized(client: TestClient):
    response = client.get("/projects/")
    assert response.status_code == 401


def test_get_specific_project_success_owner(authorized_client: TestClient):
    project_id = create_test_project(authorized_client)
    response = authorized_client.get(f"/projects/{project_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == project_id


def test_get_specific_project_forbidden_not_owner(
    authorized_client: TestClient, other_authorized_client: TestClient
):
    project_id = create_test_project(authorized_client)
    response = other_authorized_client.get(f"/projects/{project_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_specific_project_unauthorized(
    client: TestClient, authorized_client: TestClient
):
    # Setup: Create project as authorized user first
    project_id = create_test_project(authorized_client)
    # Action: Attempt get as unauthorized user
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_specific_project_not_found(authorized_client: TestClient):
    response = authorized_client.get("/projects/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_project_success_owner(authorized_client: TestClient):
    project_id = create_test_project(authorized_client)
    update_data = {"name": "Updated Name PUT", "description": "Updated Desc PUT"}
    response = authorized_client.put(f"/projects/{project_id}", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]


def test_update_project_forbidden_not_owner(
    authorized_client: TestClient, other_authorized_client: TestClient
):
    project_id = create_test_project(authorized_client)
    update_data = {"name": "Forbidden Update", "description": "Should fail"}
    response = other_authorized_client.put(f"/projects/{project_id}", json=update_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_project_not_found(authorized_client: TestClient):
    update_data = {"name": "Not Found Update", "description": "Should fail"}
    response = authorized_client.put("/projects/999999", json=update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_project_success_owner(authorized_client: TestClient):
    project_id = create_test_project(authorized_client)
    response = authorized_client.delete(f"/projects/{project_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Project deleted"

    get_response = authorized_client.get(f"/projects/{project_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_project_forbidden_not_owner(
    authorized_client: TestClient, other_authorized_client: TestClient
):
    project_id = create_test_project(authorized_client)
    response = other_authorized_client.delete(f"/projects/{project_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_project_unauthorized(client: TestClient, authorized_client: TestClient):

    project_id = create_test_project(authorized_client)

    response = client.delete(f"/projects/{project_id}")  # Correct URL
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_project_not_found(authorized_client):
    response = authorized_client.delete("/projects/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
