#!/bin/bash

# Get project name from current directory
PROJECT_NAME="$(basename "$PWD")"

# Virtual environment path
VENV_PATH="$HOME/venv/$PROJECT_NAME"

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found: $VENV_PATH"
    echo "Please run the setup script first."
    exit 1
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run the project
python3 ./main.py

