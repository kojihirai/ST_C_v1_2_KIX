# create the tables for the database

import psycopg2

# postgres connection
conn = psycopg2.connect(
    host="localhost",
    database="data_mgmt",
    user="postgres",
    password="postgres"
)

# create the tables
cursor = conn.cursor()

# create the projects table
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    project_description TEXT,
    project_params JSONB,
    project_controls JSONB,
    experiment_count INTEGER DEFAULT 0,
    project_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    project_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# create the experiments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    experiment_name VARCHAR(255) NOT NULL,
    experiment_description TEXT,
    experiment_params JSONB,
    run_count INTEGER DEFAULT 0,
    experiment_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    experiment_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
""")

# create the runs table
cursor.execute("""
CREATE TABLE IF NOT EXISTS runs (
    run_id SERIAL PRIMARY KEY,
    project_id INTEGER,
    experiment_id INTEGER NOT NULL,
    run_name VARCHAR(255) NOT NULL,
    run_description TEXT,
    run_params JSONB,
    run_status VARCHAR(255) NOT NULL,
    run_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
);
""")

# create the run_data table
cursor.execute("""
CREATE TABLE IF NOT EXISTS run_videos (
    run_id INTEGER NOT NULL,
    video_id SERIAL PRIMARY KEY,
    video_path VARCHAR(255) NOT NULL,
    video_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);
""")

# create the experiment_commands table
cursor.execute("""
CREATE TABLE IF NOT EXISTS experiment_commands (
    command_id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    device VARCHAR(50) NOT NULL,
    command_data JSONB NOT NULL,
    sequence_order INTEGER NOT NULL,
    command_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
);
""")

# Add foreign key constraints
cursor.execute("""
ALTER TABLE experiments 
ADD CONSTRAINT IF NOT EXISTS fk_experiments_project 
FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
""")

cursor.execute("""
ALTER TABLE runs 
ADD CONSTRAINT IF NOT EXISTS fk_runs_experiment 
FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE;
""")

cursor.execute("""
ALTER TABLE runs 
ADD CONSTRAINT IF NOT EXISTS fk_runs_project 
FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
""")

cursor.execute("""
ALTER TABLE run_videos 
ADD CONSTRAINT IF NOT EXISTS fk_run_videos_run 
FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE;
""")

# Add indexes for common queries
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_experiments_project_id ON experiments(project_id);
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_runs_experiment_id ON runs(experiment_id);
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_runs_project_id ON runs(project_id);
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_run_videos_run_id ON run_videos(run_id);
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(run_status);
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_runs_project_experiment ON runs(project_id, experiment_id);
""")

# Add JSONB indexes for parameter queries
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_experiments_params ON experiments USING GIN (experiment_params);
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_runs_params ON runs USING GIN (run_params);
""")

# Create function for updating modified_at timestamp
cursor.execute("""
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.modified_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ language 'plpgsql';
""")

# Create triggers for automatic timestamp updates
cursor.execute("""
DROP TRIGGER IF EXISTS update_projects_modtime ON projects;
CREATE TRIGGER update_projects_modtime
BEFORE UPDATE ON projects
FOR EACH ROW EXECUTE FUNCTION update_modified_column();
""")

cursor.execute("""
DROP TRIGGER IF EXISTS update_experiments_modtime ON experiments;
CREATE TRIGGER update_experiments_modtime
BEFORE UPDATE ON experiments
FOR EACH ROW EXECUTE FUNCTION update_modified_column();
""")

cursor.execute("""
DROP TRIGGER IF EXISTS update_runs_modtime ON runs;
CREATE TRIGGER update_runs_modtime
BEFORE UPDATE ON runs
FOR EACH ROW EXECUTE FUNCTION update_modified_column();
""")

# Create function for updating experiment run count
cursor.execute("""
CREATE OR REPLACE FUNCTION update_experiment_run_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE experiments SET run_count = run_count + 1 WHERE experiment_id = NEW.experiment_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE experiments SET run_count = run_count - 1 WHERE experiment_id = OLD.experiment_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;
""")

# Create trigger for updating experiment run count
cursor.execute("""
DROP TRIGGER IF EXISTS update_experiment_run_count_trigger ON runs;
CREATE TRIGGER update_experiment_run_count_trigger
AFTER INSERT OR DELETE ON runs
FOR EACH ROW EXECUTE FUNCTION update_experiment_run_count();
""")

# Create view for experiment summary
cursor.execute("""
DROP VIEW IF EXISTS experiment_summary;
CREATE VIEW experiment_summary AS
SELECT 
  e.experiment_id,
  e.project_id,
  e.experiment_name,
  e.experiment_description,
  e.experiment_params,
  e.run_count,
  p.project_name,
  COUNT(r.run_id) as actual_run_count,
  MAX(r.run_created_at) as last_run_at
FROM experiments e
JOIN projects p ON e.project_id = p.project_id
LEFT JOIN runs r ON e.experiment_id = r.experiment_id
GROUP BY e.experiment_id, e.project_id, e.experiment_name, e.experiment_description, 
         e.experiment_params, e.run_count, p.project_name;
""")

# commit the changes
conn.commit()

# close the connection
conn.close()