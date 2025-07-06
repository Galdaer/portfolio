#!/bin/bash
set -e

echo "Installing system dependencies..."
apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

echo "Installing uv for faster Python package management..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

echo "Installing Python packages..."
uv pip install --system --no-cache scispacy spacy flask requests || pip install --no-cache-dir scispacy spacy flask requests

echo "Installing SciSpacy model..."
uv pip install --system https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz || pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz

echo "Testing model installation..."
python -c "import spacy; nlp = spacy.load('en_core_sci_sm'); print('Model loaded successfully')"

echo "Starting SciSpacy server..."
python /app/scispacy_server.py
