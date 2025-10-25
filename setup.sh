#!/bin/bash
# Setup script for Slideshow Manager

echo "================================"
echo "Slideshow Manager Setup"
echo "================================"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies"
    exit 1
fi

echo "✓ Python dependencies installed"

# Check and install ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg not found. Installing..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "Error: Homebrew not found. Please install ffmpeg manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        elif command -v yum &> /dev/null; then
            sudo yum install -y ffmpeg
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm ffmpeg
        else
            echo "Error: Could not find a package manager. Please install ffmpeg manually."
            exit 1
        fi
    else
        echo "Error: Unsupported OS. Please install ffmpeg manually."
        exit 1
    fi
fi

echo "✓ ffmpeg is installed"

echo ""
echo "================================"
echo "Setup complete!"
echo "Run: python3 slideshow_manager.py"
echo "================================"

