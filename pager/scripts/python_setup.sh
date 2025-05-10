#!/bin/bash

# Ensure we're in the correct directory
cd "$(dirname "$0")/.."

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "Creating new virtual environment..."
python3 -m venv venv

# Activate virtual environment and upgrade pip
echo "Upgrading pip..."
source venv/bin/activate
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found!"
    echo "Please create a requirements.txt file with your dependencies."
    exit 1
fi

# Verify installation
echo "Verifying installation..."
python -c "import sys; print(f'Python version: {sys.version}')"
pip list

echo "Python virtual environment setup complete!"
echo "To activate the virtual environment, run: source venv/bin/activate"
