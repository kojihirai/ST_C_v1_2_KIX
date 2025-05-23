#!/bin/bash

# Ensure we're in the correct directory
cd "$(dirname "$0")/.."

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install -g pm2
fi

# Stop and delete all PM2 processes
echo "Stopping and deleting all PM2 processes..."
pm2 delete all

# Remove PM2 startup configuration
echo "Removing PM2 startup configuration..."
pm2 unstartup

# Get the absolute path to the virtual environment
VENV_PATH="$(pwd)/venv/bin/python3"

# Build Next.js application
echo "Building Next.js application..."
cd hmi
npm install
npm run build
cd ..

# Create PM2 ecosystem file
cat > ecosystem.config.js << EOL
module.exports = {
  apps: [
    {
      name: 'ota-service',
      script: 'ota/ota.py',
      interpreter: '${VENV_PATH}',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: '$(pwd)',
        PATH: '$(pwd)/venv/bin:${PATH}'
      },
      error_file: 'logs/ota-error.log',
      out_file: 'logs/ota-out.log',
      log_file: 'logs/ota-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'firmware-service',
      script: 'firmware/firmware.py',
      interpreter: '${VENV_PATH}',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: '$(pwd)',
        PATH: '$(pwd)/venv/bin:${PATH}'
      },
      error_file: 'logs/firmware-error.log',
      out_file: 'logs/firmware-out.log',
      log_file: 'logs/firmware-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'flask-hmi',
      script: 'flask_hmi/hmi.py',
      interpreter: '${VENV_PATH}',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: '$(pwd)',
        PATH: '$(pwd)/venv/bin:${PATH}'
      },
      error_file: 'logs/flask-hmi-error.log',
      out_file: 'logs/flask-hmi-out.log',
      log_file: 'logs/flask-hmi-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'nextjs-app',
      cwd: './hmi',
      script: 'node_modules/next/dist/bin/next',
      args: 'start',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        PORT: 3001
      },
      error_file: 'logs/nextjs-error.log',
      out_file: 'logs/nextjs-out.log',
      log_file: 'logs/nextjs-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
EOL

# Clean up old logs
echo "Cleaning up old logs..."
rm -rf logs
mkdir -p logs

# Start the applications
echo "Starting applications with PM2..."
pm2 start ecosystem.config.js

# Save the PM2 process list
pm2 save

# Setup PM2 to start on system boot
echo "Setting up PM2 startup script..."
STARTUP_CMD=$(pm2 startup | grep -o "sudo.*")
if [ ! -z "$STARTUP_CMD" ]; then
    echo "Executing PM2 startup command..."
    eval "$STARTUP_CMD"
else
    echo "Warning: Could not get PM2 startup command. You may need to run it manually."
    echo "Run 'pm2 startup' and execute the command it provides."
fi

echo "PM2 setup complete! Your applications are now running and will start automatically on system boot."
echo "To check status: pm2 status"
echo "To view logs: pm2 logs"
echo "To restart: pm2 restart all"
echo "To check detailed logs: pm2 logs flask-hmi --lines 100"
