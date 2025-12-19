#!/bin/bash

# Project name = current directory name
PROJECT_NAME="$(basename "$PWD")"

# Virtual environment base directory
VENV_BASE="$HOME/venv"
VENV_PATH="$VENV_BASE/$PROJECT_NAME"

# Function to print in green
print_green() {
    echo -e "\033[0;32m$1\033[0m"
}

# Function to print in red
print_red() {
    echo -e "\033[0;31m$1\033[0m"
}

# Ensure ~/venv exists
mkdir -p "$VENV_BASE"

# Create venv if not exists
if [ -d "$VENV_PATH" ]; then
    echo "Virtual environment '$VENV_PATH' already exists, skipping creation."
else
    echo "Creating virtual environment for project '$PROJECT_NAME'..."
    python3 -m venv "$VENV_PATH"
fi

# Activate venv
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install project dependencies
echo "Installing packages..."
pip install ffmpeg-python requests chardet

# List installed packages
echo "Installed packages:"
pip freeze 

# Activation hint
print_green "To activate this project's virtual environment manually:"
print_red "  source $VENV_PATH/bin/activate"

# Deactivate
echo "Deactivating virtual environment..."
deactivate

