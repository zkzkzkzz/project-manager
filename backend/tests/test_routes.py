from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)

def test_create_project():
    project_data = {
        "name": "Test Project",
        "description": "This is a test project"
    }

    response = client.post('/projects/projects', json=project_data)

    assert response.status_code==201
    data=response.json()
    assert 'id' in data
    assert data['name']==project_data['name']
    assert data['description']==project_data['description']

def test_get_all_projects():
    response=client.get('/projects/projects')

    assert response.status_code==200
    data=response.json()
    assert isinstance(data, list)

    if len(data)>0:
        project=data[0]
        assert 'id' in project
        assert 'name' in project
        assert 'description' in project

def test_get_project():
    project_data={
        "name": "Test Project 2",
        "description": "Another test project"
    }

    create_response=client.post('/projects/projects', json=project_data)
    created_project=create_response.json()

    response = client.get(f"/projects/projects/{created_project['id']}")

    assert response.status_code==200
    data=response.json()
    assert data["id"] == created_project["id"]
    assert data["name"] == created_project["name"]
    assert data["description"] == created_project["description"]


def test_get_nonexistent_project():
    response = client.get('/projects/9999')
    assert response.status_code==404
    assert response.json()['detail']=='Not Found'


def test_update_project():
    project_data= {
        "name": "Initial Project",
        "description": "Initial Description"
    }

    create_response=client.post('/projects/projects', json=project_data)
    created_project=create_response.json()
    project_id=created_project['id']

    updated_data = {
        "name": "Updated Project",
        "description": "Updated Description"
    }

    response = client.put(f"/projects/projects/{project_id}", json=updated_data)

    assert response.status_code==200
    updated_project=response.json()
    assert updated_project["id"] == project_id
    assert updated_project["name"] == "Updated Project"
    assert updated_project["description"] == "Updated Description"

def test_update_nonexistent_project():
    nonexistent_id=9999
    updated_data = {
        "id": nonexistent_id,
        "name": "New Name",
        "description": "New Description"
    }

    response=client.put(f"/projects/projects/{nonexistent_id}", json=updated_data)

    assert response.status_code==404
    assert response.json()['detail']=="Project with that id not found"


def test_delete_project():
    project_data = {
        "name": "Project to Delete",
        "description": "This will be deleted"
    }
    create_response = client.post('/projects/projects', json=project_data)
    created_project = create_response.json()
    project_id = created_project['id']

    response=client.delete(f"/projects/projects/{project_id}")

    assert response.status_code==200
    assert response.json()=={'message':'Project deleted'}

    get_response=client.get(f'/projects/projects/{project_id}')
    assert get_response.status_code==404
    assert get_response.json()['detail']=='Project with that id not found'

def test_delete_nonexistent_project():
    nonexistent_id=9999
    response=client.delete(f'/projects/projects/{nonexistent_id}')
    assert response.status_code==404
    assert response.json()['detail']=='Project with this id not found'