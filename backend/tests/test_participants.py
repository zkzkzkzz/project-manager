from fastapi import status
from fastapi.testclient import TestClient


def create_test_project(
    client: TestClient, name: str = "Default Test Project", desc: str = "Default Desc"
):
    response = client.post("/projects/", json={"name": name, "description": desc})
    assert (
        response.status_code == status.HTTP_201_CREATED
    ), f"Failed to create test project: {response.text}"
    return response.json()["id"]


def test_invite_user_success_owner(authorized_client, other_user):

    project_id = create_test_project(authorized_client, name="Project for invite")
    invite_login = other_user.login

    response = authorized_client.post(
        f"/projects/{project_id}/invite?user={invite_login}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert "successfully invited" in response.json()["message"]


def test_invite_user_forbidden_not_owner(
    authorized_client, other_authorized_client, other_user
):
    project_id = create_test_project(authorized_client, name="owners project")

    invite_login = other_user.login

    response = other_authorized_client.post(
        f"/projects/{project_id}/invite?user={invite_login}"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_invite_project_not_found(authorized_client, other_user):
    invite_login = other_user.login
    response = authorized_client.post(f"/projects/999999/invite?user={invite_login}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_invite_user_to_invite_not_found(authorized_client):
    project_id = create_test_project(authorized_client)
    response = authorized_client.post(
        f"/projects/{project_id}/invite?user=nonexistentuserlogin"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "User to invite not found" in response.json()["detail"]


def test_invite_owner_as_participant_fails(authorized_client, test_user):
    project_id = create_test_project(authorized_client)
    owner_login = test_user.login
    response = authorized_client.post(
        f"/projects/{project_id}/invite?user={owner_login}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Owner cannot invite themselves" in response.json()["detail"]


def test_invite_existing_participant_fails(authorized_client: TestClient, other_user):
    """Test inviting an already participating user again fails (400)."""
    project_id = create_test_project(authorized_client)
    participant_login = other_user.login

    # First invite (should succeed)
    authorized_client.post(f"/projects/{project_id}/invite?user={participant_login}")
    # Second invite (should fail)
    response = authorized_client.post(
        f"/projects/{project_id}/invite?user={participant_login}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already a participant" in response.json()["detail"]


def test_get_all_projects_includes_participated(
    authorized_client, other_authorized_client, other_user
):
    project_id_owned_by_main = create_test_project(
        authorized_client, name="mains owned"
    )
    project_id_participated = create_test_project(
        authorized_client, name="mains shared with other"
    )
    authorized_client.post(
        f"/projects/{project_id_participated}/invite?user={other_user.login}"
    )

    project_id_owned_by_other = create_test_project(
        other_authorized_client, name="Other's Owned"
    )

    # Make request as 'other_user' (other_authorized_client)
    response = other_authorized_client.get("/projects/")
    assert response.status_code == status.HTTP_200_OK
    project_ids_in_response = {p["id"] for p in response.json()}

    assert project_id_participated in project_ids_in_response
    assert project_id_owned_by_other in project_ids_in_response
    assert project_id_owned_by_main not in project_ids_in_response


def test_get_specific_project_success_participant(
    authorized_client, other_authorized_client, other_user
):
    project_id = create_test_project(authorized_client, name="shared project for GET")
    authorized_client.post(f"/projects/{project_id}/invite?user={other_user.login}")

    response = other_authorized_client.get(f"projects/{project_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == project_id


def test_update_project_success_participant(
    authorized_client: TestClient, other_authorized_client: TestClient, other_user
):
    """Test participant can PUT (update) a project they are invited to."""
    project_id = create_test_project(
        authorized_client, name="Shared Project for PUT"
    )  # Owned by main user
    # Invite 'other_user' (participant)
    authorized_client.post(f"/projects/{project_id}/invite?user={other_user.login}")

    update_data = {
        "name": "Updated by Participant",
        "description": "Participant was here",
    }
    # 'other_user' (participant) attempts to UPDATE the project
    response = other_authorized_client.put(f"/projects/{project_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["id"] == project_id


def test_delete_project_forbidden_participant(
    authorized_client, other_authorized_client, other_user
):
    project_id = create_test_project(
        authorized_client, name="shared project for delete test"
    )

    authorized_client.post(f"/projects/{project_id}/invite?user={other_user.login}")

    response = other_authorized_client.delete(f"/projects/{project_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
