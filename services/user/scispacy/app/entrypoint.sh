#!/bin/bash
set -e

echo "Installing system dependencies..."
apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

echo "Installing uv for faster Python package management..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

echo "Installing Python packages..."
uv pip install --system --no-cache scispacy spacy flask requests || pip install --no-cache-dir scispacy spacy flask requests

echo "Installing SciSpacy model for medical NER..."
# Install en_ner_bionlp13cg_md - comprehensive medical entity recognition (16 entity types)
# AMINO_ACID, ANATOMICAL_SYSTEM, CANCER, CELL, CELLULAR_COMPONENT, DEVELOPING_ANATOMICAL_STRUCTURE,
# GENE_OR_GENE_PRODUCT, IMMATERIAL_ANATOMICAL_ENTITY, MULTI-TISSUE_STRUCTURE, ORGAN, ORGANISM,
# ORGANISM_SUBDIVISION, ORGANISM_SUBSTANCE, PATHOLOGICAL_FORMATION, SIMPLE_CHEMICAL, TISSUE
uv pip install --system https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bionlp13cg_md-0.5.4.tar.gz || pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bionlp13cg_md-0.5.4.tar.gz

echo "Testing model installation..."
python -c "import spacy; nlp = spacy.load('en_ner_bionlp13cg_md'); print('Model loaded successfully')"

echo "Starting SciSpacy server..."
python /app/scispacy_server.py
