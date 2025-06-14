#!/bin/bash

cd "$(dirname "$0")/.."

if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install -g pm2
fi

echo "Stopping and deleting all PM2 processes..."
pm2 delete all

echo "Removing PM2 startup configuration..."
pm2 unstartup

VENV_PATH="$(pwd)/venv/bin/python3"
VENV_ACTIVATE="$(pwd)/venv/bin/activate"

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
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: '$(pwd)',
        PATH: '$(pwd)/venv/bin:${PATH}',
        VIRTUAL_ENV: '$(pwd)/venv'
      },
      error_file: 'logs/firmware-error.log',
      out_file: 'logs/firmware-out.log',
      log_file: 'logs/firmware-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
EOL

echo "Cleaning up old logs..."
rm -rf logs
mkdir -p logs

echo "Starting applications with PM2..."
pm2 start ecosystem.config.js

# Start firmware service with sudo, ensuring it uses the venv Python
echo "Starting firmware service with sudo..."
sudo -E env "PATH=$PATH" "VIRTUAL_ENV=$(pwd)/venv" pm2 restart firmware-service --interpreter "sudo -E env 'PATH=$PATH' 'VIRTUAL_ENV=$(pwd)/venv' ${VENV_PATH}"

pm2 save

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
echo "To check detailed logs: pm2 logs ota-service --lines 100"
