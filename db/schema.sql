CREATE TABLE users (
	id BIGSERIAL PRIMARY KEY,
	login VARCHAR(55) UNIQUE NOT NULL,
	hashed_password VARCHAR(255) NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE projects (
	id BIGSERIAL PRIMARY KEY,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	owner_id BIGINT NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

	CONSTRAINT fk_owner
		FOREIGN KEY(owner_id)
		REFERENCES users(id)
		ON DELETE CASCADE
);

CREATE TABLE documents(
	id BIGSERIAL PRIMARY KEY,
	project_id BIGINT NOT NULL,
	file_name VARCHAR(255),
	s3_key VARCHAR(1024) UNIQUE NOT NULL,
	file_type VARCHAR(50),
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploader_id BIGINT REFERENCES users(id) ON DELETE SET NULL,

	CONSTRAINT fk_project
		FOREIGN KEY (project_id)
		REFERENCES projects(id)
		ON DELETE CASCADE
);

CREATE TABLE project_participants (
	user_id BIGINT NOT NULL,
	project_id BIGINT NOT NULL,
	role VARCHAR(50) NOT NULL DEFAULT 'participant',
	added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

	PRIMARY KEY (user_id, project_id),

	CONSTRAINT fk_user
		FOREIGN KEY(user_id)
		REFERENCES users(id)
		ON DELETE CASCADE,
	CONSTRAINT fk_project
		FOREIGN KEY(project_id)
		REFERENCES projects(id)
		ON DELETE CASCADE

);

CREATE INDEX idx_projects_owner_id ON projects(owner_id);
CREATE INDEX idx_documents_projects_id ON documents(project_id);
CREATE INDEX idx_project_participants_user_id ON project_participants(user_id);
CREATE INDEX idx_project_participants_project_id ON project_participants(project_id);

CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
	NEW.updated_at = NOW();
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp_users
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_projects
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_documents
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();