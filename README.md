# Project Manager API

A FastAPI backend for a project management dashboard application, allowing users to create, update, share, and delete project information and associated documents.

## Features

*   User registration and JWT-based authentication.
*   CRUD operations for projects.
*   Invite users to participate in projects.
*   Role-based permissions (Project Owner, Project Participant).
*   Document uploads, downloads (via pre-signed URLs), and deletion, linked to projects.
*   File storage using MinIO (S3-compatible).
*   PostgreSQL database.
*   Containerized development environment using Docker and Docker Compose.
*   Database schema management with Alembic. (Add this if you fully implemented Alembic)

## Tech Stack

*   **Backend:** Python 3.10+, FastAPI
*   **Database:** PostgreSQL
*   **Object Storage:** MinIO (S3 Compatible)
*   **Authentication:** JWT (python-jose), Passlib (bcrypt)
*   **ORM:** SQLAlchemy
*   **Data Validation:** Pydantic
*   **Containerization:** Docker, Docker Compose
*   **Migrations:** Alembic (SQLAlchemy) (Mention if applicable)
*   **Testing:** Pytest, FastAPI TestClient
*   **Linting/Formatting:** Black, Flake8, isort

## Prerequisites

*   Python 3.10 or higher
*   Docker Desktop (or Docker Engine + Docker Compose CLI) installed and running.
*   An IDE like PyCharm or VS Code (recommended).
*   Git.

## Local Development Setup (Using Docker Compose)

This is the recommended way to run the project locally as it sets up the API, database, and MinIO storage in isolated containers.

1.  **Clone the Repository:**
    ```bash
    git clone <your_repository_url>
    cd project_manager 
    ```

2.  **Create Environment File:**
    Copy the example environment file and customize it:
    ```bash
    cp .env.example .env
    ```
    Open the `.env` file and **MUST** set a strong `JWT_KEY`. Other variables like `PUBLIC_S3_HOST`, MinIO credentials (`MINIO_DEV_USER`, `MINIO_DEV_PASSWORD`), and `S3_BUCKET_NAME` are pre-configured for the Docker Compose setup but can be reviewed. Note that `DATABASE_URL` and `AWS_S3_ENDPOINT_URL` in this `.env` file are overridden by `docker-compose.yml` when running with Compose.

3.  **Build and Start Services:**
    From the project root directory (where `docker-compose.yml` is located):
    ```bash
    docker-compose up --build
    ```
    The `--build` flag is needed for the first run or if you change `Dockerfile` or `pip_requirements.txt`. For subsequent runs, `docker-compose up` is often sufficient.

4.  **First-Time Setup for Services (After `docker-compose up` is running):**
    You only need to do these steps once after the first successful `docker-compose up` or after running `docker-compose down -v`.

    *   **Apply Database Migrations/Schema:**
        Open a new terminal window, navigate to the project root, and run:
        ```bash
        docker-compose exec backend alembic upgrade head
        ```
        *(If not using Alembic, provide instructions to connect to the DB via `localhost:YOUR_DB_HOST_PORT` (e.g., 5433) with user `postgres`/pass `postgres` and run `db/schema.sql` against the `project_db` database.)*

    *   **Create MinIO Bucket:**
        1.  Open your web browser and navigate to the MinIO Console: `http://localhost:YOUR_MINIO_CONSOLE_HOST_PORT` (e.g., `http://localhost:9006` if you mapped host port 9006 to container console port 9001).
        2.  Log in using the MinIO credentials (default in Compose example: `minioadmin` / `minioadmin`, or what you set in `.env` for `MINIO_DEV_USER`/`MINIO_DEV_PASSWORD`).
        3.  Click on "Buckets" and then "Create Bucket".
        4.  Enter the bucket name defined by `S3_BUCKET_NAME` in your `.env` file (e.g., `project-bucket`).
        5.  (Optional, but needed if download redirect issues persist due to CORS after URL rewrite): Configure CORS for this bucket to allow requests from `http://localhost:8000`. (Provide brief instructions or link to MinIO docs for setting bucket CORS).

5.  **Accessing the Application:**
    *   API (Swagger UI): `http://localhost:8000/docs`
    *   MinIO Console: `http://localhost:YOUR_MINIO_CONSOLE_HOST_PORT` (e.g., 9006)
    *   PostgreSQL (from host, e.g., with pgAdmin): Connect to `localhost` on `YOUR_DB_HOST_PORT` (e.g., 5433), database `project_db`, user `postgres`, password `postgres`.

6.  **Stopping the Application:**
    Press `Ctrl+C` in the terminal where `docker-compose up` is running.
    To remove containers and networks:
    ```bash
    docker-compose down
    ```
    To also remove data volumes (`pgdata`, `minio_data`) for a completely fresh start:
    ```bash
    docker-compose down -v
    ```

## Running Tests

Ensure the Docker Compose environment is up and running (as the tests might target the containerized services if configured to do so, or you run tests inside the container).

*   **To run all tests (from project root on host):**
    ```bash
    pytest
    ```
    *(Specify if tests are configured to hit `localhost:mapped_ports` or if they should be run inside the container: `docker-compose exec backend pytest`)*

## Linting and Formatting

This project uses `black` for code formatting, and `flake8` for linting.
Run these from the project root:
```bash

black .
flake8 backend/ --count --ignore=E501,W503,W504 --max-line-length=88 --show-source --statistics