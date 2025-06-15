import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def create_project(
    client: TestClient, token: str, name="Test Project", description="Desc"
):
    response = client.post(
        "/projects",
        json={"name": name, "description": description},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()["id"]


def test_upload_and_list_documents_authorized(
    authorized_client: TestClient, token: str, db_session: Session, test_user
):
    project_id = create_project(authorized_client, token)

    file_content = b"hello world"
    response = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("example.txt", io.BytesIO(file_content), "text/plain")},
    )

    assert response.status_code == 201
    data = response.json()
    assert isinstance(data, list) and len(data) == 1

    doc = data[0]
    assert doc["project_id"] == project_id
    assert doc["file_name"] == "example.txt"
    assert doc["s3_key"].startswith(f"fake_key_proj_{project_id}_call_")
    assert doc["uploader_id"] == test_user.id

    response = authorized_client.get(f"/projects/{project_id}/documents")
    assert response.status_code == 200
    list_data = response.json()
    assert isinstance(list_data, list) and len(list_data) == 1

    summary = list_data[0]
    # DocumentList includes id, project_id, file_name, file_type, uploaded_at, download_url
    assert summary["id"] == doc["id"]
    assert summary["file_name"] == "example.txt"
    assert summary["download_url"].startswith("https://fake-minio.local/")


def test_upload_no_files_returns_422(authorized_client: TestClient, token: str):
    # Create project
    project_id = create_project(authorized_client, token)

    # Call upload with no files field at all
    response = authorized_client.post(f"/projects/{project_id}/documents", files={})
    # Because the endpoint signature uses File(...), FastAPI responds with 422 Unprocessable Entity
    assert response.status_code == 422


def test_list_documents_forbidden_to_unauthorized(
    client: TestClient,
    authorized_client: TestClient,
    other_authorized_client: TestClient,
    token: str,
    other_token: str,
):
    project_id = create_project(authorized_client, token)

    response = other_authorized_client.get(f"/projects/{project_id}/documents")
    assert response.status_code == 403


def test_download_redirect_location_header(
    authorized_client: TestClient, token: str, db_session: Session
):
    project_id = create_project(authorized_client, token)
    response = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("file.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
    )

    assert response.status_code == 201
    doc_id = response.json()[0]["id"]

    print(f"Type of authorized_client: {type(authorized_client)}")
    assert isinstance(authorized_client, TestClient)

    download_resp = authorized_client.request(
        "GET", f"/documents/{doc_id}/download", follow_redirects=False
    )
    assert download_resp.status_code == 307

    assert "Location" in download_resp.headers
    location = download_resp.headers["Location"]
    assert location.startswith(
        "https://fake-minio.local/fake_key_proj_"
    ), "Expected presigned URL in Location header"


def test_download_forbidden_to_unauthorized(
    authorized_client: TestClient,
    other_authorized_client: TestClient,
    token: str,
    other_token: str,
):
    project_id = create_project(authorized_client, token)
    upload_resp = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={
            "files": (
                "secret.docx",
                io.BytesIO(b"secret"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    doc_id = upload_resp.json()[0]["id"]

    response = other_authorized_client.request(
        "GET", f"/documents/{doc_id}/download", follow_redirects=False
    )
    assert response.status_code == 403


def test_update_document_changes_s3_key_and_metadata_as_owner(
    authorized_client: TestClient, token: str, db_session: Session, test_user
):
    # Create project & upload original file
    project_id = create_project(authorized_client, token)
    upload_resp = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("old.txt", io.BytesIO(b"old content"), "text/plain")},
    )

    assert upload_resp.status_code == 201
    original_doc = upload_resp.json()[0]
    doc_id = original_doc["id"]
    old_key = original_doc["s3_key"]

    new_content = b"new content"
    update_resp = authorized_client.put(
        f"/documents/{doc_id}",
        files={"file": ("new.txt", io.BytesIO(new_content), "text/plain")},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()

    new_key = updated["s3_key"]

    assert new_key != old_key
    assert new_key.startswith(f"fake_key_proj_{project_id}_call_")

    assert updated["s3_key"] != old_key

    # updated_at should be newer than created_at
    assert "created_at" in updated and "updated_at" in updated


def test_update_doc_as_participant(
    authorized_client: TestClient,
    other_authorized_client: TestClient,
    token: str,
    other_token: str,
    other_user,
    db_session: Session,
):
    project_id = create_project(authorized_client, token)
    # owner uploads og doc
    upload_resp = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={
            "files": (
                "initial_doc_for_participant_update.txt",
                io.BytesIO(b"initial"),
                "text/plain",
            )
        },
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()[0]["id"]
    old_key = upload_resp.json()[0]["s3_key"]

    # owner invites other user
    invite_resp = authorized_client.post(
        f"/projects/{project_id}/invite?user={other_user.login}"
    )
    assert invite_resp.status_code == 200

    new_content = b"participant updated content"
    update_files = {
        "file": ("updated_by_participant.txt", io.BytesIO(new_content), "text/plain")
    }
    response = other_authorized_client.put(f"/documents/{doc_id}", files=update_files)

    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == "updated_by_participant.txt"
    assert data["s3_key"] != old_key


def test_update_forbidden_to_non_participant(
    authorized_client: TestClient,
    other_authorized_client: TestClient,
    token: str,
    other_token: str,
):

    project_id = create_project(authorized_client, token)
    upload_resp = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("fileA.txt", io.BytesIO(b"A"), "text/plain")},
    )

    doc_id = upload_resp.json()[0]["id"]

    resp = other_authorized_client.put(
        f"/documents/{doc_id}",
        files={"file": ("hacked.txt", io.BytesIO(b"hacked"), "text/plain")},
    )

    assert resp.status_code == 403


def test_update_doc_not_found(authorized_client: TestClient):
    files_payload = {"file": ("any.txt", io.BytesIO(b"any"), "text/plain")}
    response = authorized_client.put(
        "/documents/99999", files=files_payload
    )  # Non-existent ID
    assert response.status_code == 404


def test_delete_by_owner_who_uploads(
    authorized_client: TestClient, token: str, db_session: Session, test_user
):
    project_id = create_project(authorized_client, token)
    upload_resp = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("todelete.txt", io.BytesIO(b"bye"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()[0]["id"]

    del_resp = authorized_client.delete(f"/documents/{doc_id}")
    assert del_resp.status_code == 204

    list_resp = authorized_client.get(f"/projects/{project_id}/documents")
    assert list_resp.status_code == 200  # ??
    assert list_resp.json() == []


def test_delete_document_as_owner_who_is_not_uploader(
    authorized_client: TestClient,
    other_authorized_client: TestClient,
    token: str,
    other_token: str,
    other_user,
    db_session: Session,
):
    project_id = create_project(authorized_client, token)

    invite_resp = authorized_client.post(
        f"/projects/{project_id}/invite?user={other_user.login}"
    )
    assert invite_resp.status_code == 200

    # other user uploads a file
    upload_files = {
        "files": (
            "doc_by_participant.txt",
            io.BytesIO(b"participant data"),
            "text/plain",
        )
    }
    upload_resp = other_authorized_client.post(
        f"/projects/{project_id}/documents", files=upload_files
    )

    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()[0]["id"]

    # owner(auth client) can delete
    del_resp = authorized_client.delete(f"/documents/{doc_id}")
    assert del_resp.status_code == 204


def test_delete_doc_as_og_uploader_who_is_participant(
    authorized_client: TestClient,  # Owner (to create project)
    other_authorized_client: TestClient,  # Participant and Uploader
    token: str,  # Owner's token
    other_user,  # Participant user object (for invite)
    db_session: Session,
):
    project_id = create_project(authorized_client, token)
    # Invite 'other_user' to be a participant
    invite_resp = authorized_client.post(
        f"/projects/{project_id}/invite?user={other_user.login}"
    )
    assert invite_resp.status_code == 200

    # participant uploads
    upload_files = {
        "files": (
            "doc_by_participant_for_self_delete.txt",
            io.BytesIO(b"self delete data"),
            "text/plain",
        )
    }
    upload_resp = other_authorized_client.post(
        f"/projects/{project_id}/documents", files=upload_files
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()[0]["id"]

    # Participant (other_authorized_client, who is the uploader) deletes their own document
    del_resp = other_authorized_client.delete(f"/documents/{doc_id}")
    assert del_resp.status_code == 204


def test_delete_forbidden_non_owner_non_uploader(
    authorized_client: TestClient,
    other_authorized_client: TestClient,
    token: str,
    other_token: str,
    db_session: Session,
    test_user,
    other_user,
):

    project_id = create_project(authorized_client, token)

    upload_resp = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("private.txt", io.BytesIO(b"private"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()[0]["id"]

    invite_resp = authorized_client.post(
        f"/projects/{project_id}/invite", params={"user": other_user.login}
    )
    assert invite_resp.status_code == 200

    resp = other_authorized_client.delete(f"/documents/{doc_id}")
    assert resp.status_code == 403


def test_delete_doc_by_user_not_in_project(
    authorized_client: TestClient,  # Owner, uploader
    third_authorized_client: TestClient,  # Not owner, not participant, not uploader
    token: str,
    db_session: Session,
):
    project_id = create_project(authorized_client, token)
    upload_resp = authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("secret_doc.txt", io.BytesIO(b"secret"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()[0]["id"]

    del_resp = third_authorized_client.delete(f"/documents/{doc_id}")
    assert del_resp.status_code == 403


def test_list_documents_includes_only_owner_and_participant(
    authorized_client: TestClient,
    other_authorized_client: TestClient,
    token: str,
    other_token: str,
    db_session: Session,
    test_user,
    other_user,
):
    project_id = create_project(authorized_client, token)
    authorized_client.post(
        f"/projects/{project_id}/documents",
        files={"files": ("visible.txt", io.BytesIO(b"visible"), "text/plain")},
    )

    resp_owner = authorized_client.get(f"/projects/{project_id}/documents")
    assert resp_owner.status_code == 200
    assert len(resp_owner.json()) == 1

    resp_other = other_authorized_client.get(f"/projects/{project_id}/documents")
    assert resp_other.status_code == 403

    invite_resp = authorized_client.post(
        f"/projects/{project_id}/invite?user={other_user.login}"
    )
    assert invite_resp.status_code == 200

    resp_other2 = other_authorized_client.get(f"/projects/{project_id}/documents")
    assert resp_other2.status_code == 200
    assert len(resp_other2.json()) == 1
