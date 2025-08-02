#!/usr/bin/env python3
"""
SciSpacy Server - REST API for biomedical text analysis
"""

import logging
import os
from typing import Dict, Any, Tuple

import spacy
from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load the SciSpacy model
MODEL_NAME = os.environ.get("SPACY_MODEL", "en_core_sci_sm")
nlp = None


def load_model() -> bool:
    global nlp
    try:
        logger.info(f"Loading SciSpacy model: {MODEL_NAME}")
        nlp = spacy.load(MODEL_NAME)
        logger.info("Model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load model {MODEL_NAME}: {e}")
        return False


@app.route("/health")
def health() -> Tuple[Dict[str, Any], int]:
    """Health check endpoint"""
    if nlp is None:
        return {"status": "error", "message": "Model not loaded"}, 500
    return {"status": "ok", "model": MODEL_NAME}, 200


@app.route("/")
def root() -> Dict[str, Any]:
    """Root endpoint with API info"""
    return {
        "service": "SciSpacy NLP Server",
        "model": MODEL_NAME,
        "endpoints": [
            "GET /health - Health check",
            "POST /analyze - Analyze text for biomedical entities",
            "GET /info - Model information",
        ],
    }


@app.route("/info")
def info() -> Tuple[Dict[str, Any], int]:
    """Model information endpoint"""
    if nlp is None:
        return {"error": "Model not loaded"}, 500

    entities = []
    if "ner" in nlp.pipe_names:
        ner_pipe = nlp.get_pipe("ner")
        # Use getattr to safely access 'labels' if it exists
        labels = getattr(ner_pipe, "labels", None)
        if labels is not None:
            entities = list(labels)
    return {"model": MODEL_NAME, "pipeline": nlp.pipe_names, "entities": entities}


@app.route("/analyze", methods=["POST"])
def analyze() -> Tuple[Dict[str, Any], int]:
    """Analyze text for biomedical entities"""
    if nlp is None:
        return {"error": "Model not loaded"}, 500

    try:
        data = request.get_json()
        if not data or "text" not in data:
            return {"error": "Missing 'text' field in request"}, 400

        text = data["text"]
        if not text.strip():
            return {"error": "Empty text provided"}, 400

        # Process the text
        doc = nlp(text)

        # Extract entities
        entities = []
        for ent in doc.ents:
            entities.append(
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "description": spacy.explain(ent.label_) or ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": getattr(ent, "_.confidence", 1.0) if hasattr(ent, "_") else 1.0,
                }
            )

        # Extract sentences
        sentences = [sent.text.strip() for sent in doc.sents]

        # Extract tokens with POS tags
        tokens = []
        for token in doc:
            if not token.is_space:
                tokens.append(
                    {
                        "text": token.text,
                        "lemma": token.lemma_,
                        "pos": token.pos_,
                        "tag": token.tag_,
                        "is_alpha": token.is_alpha,
                        "is_stop": token.is_stop,
                    }
                )

        result = {
            "text": text,
            "entities": entities,
            "sentences": sentences,
            "tokens": tokens,
            "entity_count": len(entities),
            "sentence_count": len(sentences),
            "token_count": len(tokens),
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error processing text: {e}")
        return {"error": f"Processing failed: {str(e)}"}, 500


if __name__ == "__main__":
    # Load the model on startup
    if not load_model():
        logger.error("Failed to load model, exiting")
        exit(1)

    # Get configuration from environment
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 8001))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"Starting SciSpacy server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
