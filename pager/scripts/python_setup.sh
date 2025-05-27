#!/bin/bash

cd "$(dirname "$0")/.."

if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python3 first."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install pip3 first."
    exit 1
fi

if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

echo "Creating new virtual environment..."
python3 -m venv venv

echo "Upgrading pip..."
source venv/bin/activate
pip install --upgrade pip

echo "Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found!"
    echo "Please create a requirements.txt file with your dependencies."
    exit 1
fi

echo "Verifying installation..."
python -c "import sys; print(f'Python version: {sys.version}')"
pip list

echo "Python virtual environment setup complete!"
echo "To activate the virtual environment, run: source venv/bin/activate"
