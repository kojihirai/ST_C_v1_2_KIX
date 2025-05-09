import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="data_mgmt",
    user="dune",
    password="dune"
)

cursor = conn.cursor()

# ENUM for run_status
cursor.execute("""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'run_status_enum') THEN
        CREATE TYPE run_status_enum AS ENUM ('pending', 'running', 'completed', 'failed');
    END IF;
END$$;
""")

# PROJECTS table
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    project_description TEXT,
    project_params JSONB,
    project_controls JSONB,
    experiment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# EXPERIMENTS table
cursor.execute("""
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    experiment_name VARCHAR(255) NOT NULL,
    experiment_description TEXT,
    experiment_params JSONB,
    run_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
""")

# RUNS table with start_time and stop_time
cursor.execute("""
CREATE TABLE IF NOT EXISTS runs (
    run_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    experiment_id INTEGER NOT NULL,
    run_name VARCHAR(255) NOT NULL,
    run_description TEXT,
    run_params JSONB,
    run_status run_status_enum NOT NULL,
    start_time TIMESTAMP,
    stop_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
);
""")

# RUN_VIDEOS table
cursor.execute("""
CREATE TABLE IF NOT EXISTS run_videos (
    video_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL,
    video_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);
""")

# INDEXES
cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiments_project_id ON experiments(project_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_experiment_id ON runs(experiment_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_project_id ON runs(project_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_videos_run_id ON run_videos(run_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(run_status);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_project_experiment ON runs(project_id, experiment_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiments_params ON experiments USING GIN (experiment_params);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_params ON runs USING GIN (run_params);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_params ON projects USING GIN (project_params);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_controls ON projects USING GIN (project_controls);")

# FUNCTION for auto-update timestamps
cursor.execute("""
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.modified_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")

# TIMESTAMP TRIGGERS
for table in ["projects", "experiments", "runs"]:
    cursor.execute(f"""
    DROP TRIGGER IF EXISTS update_{table}_modtime ON {table};
    CREATE TRIGGER update_{table}_modtime
    BEFORE UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
    """)

# RUN COUNT trigger for experiments
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

cursor.execute("""
DROP TRIGGER IF EXISTS update_experiment_run_count_trigger ON runs;
CREATE TRIGGER update_experiment_run_count_trigger
AFTER INSERT OR DELETE ON runs
FOR EACH ROW EXECUTE FUNCTION update_experiment_run_count();
""")

# EXPERIMENT COUNT trigger for projects
cursor.execute("""
CREATE OR REPLACE FUNCTION update_project_experiment_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE projects SET experiment_count = experiment_count + 1 WHERE project_id = NEW.project_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE projects SET experiment_count = experiment_count - 1 WHERE project_id = OLD.project_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;
""")

cursor.execute("""
DROP TRIGGER IF EXISTS update_project_experiment_count_trigger ON experiments;
CREATE TRIGGER update_project_experiment_count_trigger
AFTER INSERT OR DELETE ON experiments
FOR EACH ROW EXECUTE FUNCTION update_project_experiment_count();
""")

# VIEWS

# EXPERIMENT SUMMARY
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
  COUNT(r.run_id) AS actual_run_count,
  MAX(r.created_at) AS last_run_at
FROM experiments e
JOIN projects p ON e.project_id = p.project_id
LEFT JOIN runs r ON e.experiment_id = r.experiment_id
GROUP BY e.experiment_id, e.project_id, e.experiment_name, e.experiment_description, 
         e.experiment_params, e.run_count, p.project_name;
""")

# RUN SUMMARY (now includes start/stop time)
cursor.execute("""
DROP VIEW IF EXISTS run_summary;
CREATE VIEW run_summary AS
SELECT 
  r.run_id,
  r.run_name,
  r.run_status,
  r.start_time,
  r.stop_time,
  r.created_at,
  r.modified_at,
  e.experiment_name,
  p.project_name
FROM runs r
JOIN experiments e ON r.experiment_id = e.experiment_id
JOIN projects p ON r.project_id = p.project_id;
""")

conn.commit()
conn.close()
