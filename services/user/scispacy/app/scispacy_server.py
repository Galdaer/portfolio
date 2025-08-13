#!/usr/bin/env python3
"""
SciSpacy Server - REST API for biomedical text analysis
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
import json
import time
import hashlib
from functools import lru_cache
import yaml  # type: ignore

import spacy
from flask import Flask, request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load the SciSpacy model
# Using en_ner_bionlp13cg_md for comprehensive medical entity recognition
# This model has 77.84% F1-score and provides 16 entity types:
# AMINO_ACID, ANATOMICAL_SYSTEM, CANCER, CELL, CELLULAR_COMPONENT,
# DEVELOPING_ANATOMICAL_STRUCTURE, GENE_OR_GENE_PRODUCT, IMMATERIAL_ANATOMICAL_ENTITY,
# MULTI-TISSUE_STRUCTURE, ORGAN, ORGANISM, ORGANISM_SUBDIVISION,
# ORGANISM_SUBSTANCE, PATHOLOGICAL_FORMATION, SIMPLE_CHEMICAL, TISSUE
MODEL_NAME = os.environ.get("SPACY_MODEL", "en_ner_bionlp13cg_md")
nlp = None

# ------------------------------------------------------------
# Entity Metadata Configuration
# ------------------------------------------------------------
METADATA_PATH = os.environ.get("METADATA_PATH")
ENTITY_METADATA: Dict[str, Dict[str, Any]] = {}
ENTITY_RELATIONSHIPS: Dict[str, List[str]] = {}
_METADATA_HASH: Optional[str] = None

# ------------------------------------------------------------
# Caching Controls
# ------------------------------------------------------------
CACHE_ENABLED = os.environ.get("SCISPACY_CACHE", "true").lower() == "true"
CACHE_MAXSIZE = int(os.environ.get("SCISPACY_CACHE_SIZE", 256))
CACHE_TTL = int(os.environ.get("SCISPACY_CACHE_TTL", 300))  # seconds

_cache_store: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _metadata_hash() -> str:
    global _METADATA_HASH
    if _METADATA_HASH is not None:
        return _METADATA_HASH
    h = hashlib.sha256()
    h.update(json.dumps(ENTITY_METADATA, sort_keys=True).encode())
    h.update(json.dumps(ENTITY_RELATIONSHIPS, sort_keys=True).encode())
    _METADATA_HASH = h.hexdigest()[:16]
    return _METADATA_HASH


def _cache_key(text: str, enrich: bool) -> str:
    return hashlib.md5(f"{_metadata_hash()}|{int(enrich)}|{text}".encode()).hexdigest()


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    if not CACHE_ENABLED:
        return None
    entry = _cache_store.get(key)
    if not entry:
        return None
    ts, value = entry
    if CACHE_TTL > 0 and (time.time() - ts) > CACHE_TTL:
        _cache_store.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: Dict[str, Any]) -> None:
    if not CACHE_ENABLED:
        return
    if len(_cache_store) >= CACHE_MAXSIZE:
        # Simple FIFO eviction: pop oldest timestamp
        oldest_key = min(_cache_store.items(), key=lambda kv: kv[1][0])[0]
        _cache_store.pop(oldest_key, None)
    _cache_store[key] = (time.time(), value)


def _cache_stats() -> Dict[str, Any]:
    return {
        "enabled": CACHE_ENABLED,
        "size": len(_cache_store),
        "maxsize": CACHE_MAXSIZE,
        "ttl": CACHE_TTL,
    }


def _load_external_metadata() -> None:
    """Load external metadata (YAML or JSON) if path provided.

    Expected top-level keys: entity_metadata, relationships
    Both optional; absence keeps server generic.
    """
    global ENTITY_METADATA, ENTITY_RELATIONSHIPS
    if not METADATA_PATH:
        logger.info("No METADATA_PATH set; running in pass-through mode")
        return
    if not os.path.exists(METADATA_PATH):
        logger.warning("METADATA_PATH '%s' does not exist", METADATA_PATH)
        return
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            if METADATA_PATH.endswith(('.yml', '.yaml')):
                data = yaml.safe_load(f)  # type: ignore[arg-type]
            else:
                data = json.load(f)
        if isinstance(data, dict):
            ENTITY_METADATA = data.get("entity_metadata", {}) or {}
            ENTITY_RELATIONSHIPS = data.get("relationships", {}) or {}
            # Invalidate metadata hash & cache when metadata changes
            global _METADATA_HASH
            _METADATA_HASH = None
            _cache_store.clear()
            logger.info(
                "Loaded external metadata: %d entity types, %d relationship groups",
                len(ENTITY_METADATA),
                len(ENTITY_RELATIONSHIPS),
            )
        else:
            logger.warning("Metadata file did not parse to dict; ignoring")
    except Exception as exc:
        logger.exception("Failed loading metadata: %s", exc)


_load_external_metadata()

def _high_priority_labels() -> set[str]:
    return {label for label, meta in ENTITY_METADATA.items() if meta.get("priority") == "high"}


def enrich_entity(ent) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
    """Return enriched entity dictionary with metadata & context.

    The context window strategy: capture the sentence containing the entity plus
    a configurable character window around it (defaults to ±40 chars) to help
    agents ground follow‑up searches.
    """
    label = ent.label_
    base_meta = ENTITY_METADATA.get(label, {})
    context_sentence = ent.sent.text if hasattr(ent, "sent") else ""
    window = 40
    # character based window on original doc text
    doc_text = ent.doc.text  # type: ignore[attr-defined]
    start = max(ent.start_char - window, 0)
    end = min(ent.end_char + window, len(doc_text))
    char_window = doc_text[start:end]

    enriched: Dict[str, Any] = {
        "text": ent.text,
        "type": label,
        "category": base_meta.get("category", "unknown"),
        "usage_hint": base_meta.get("usage_hint", ""),
        "start": ent.start_char,
        "end": ent.end_char,
        "sentence": context_sentence,
        "char_window": char_window,
        "label": label,
        "description": spacy.explain(label) or label,
    }
    if "agent_relevance" in base_meta:
        enriched["agent_relevance"] = base_meta.get("agent_relevance")
    if "priority" in base_meta:
        enriched["priority"] = base_meta.get("priority")
    if ENTITY_RELATIONSHIPS:
        enriched["relationships"] = ENTITY_RELATIONSHIPS.get(label, [])
    return enriched


def build_clinical_summary(enriched_entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Optional summary only if metadata supplies priority fields.

    Keeps server neutral: if no priority metadata present, return None.
    """
    if not any("priority" in e for e in enriched_entities):
        return None
    meds = [e["text"] for e in enriched_entities if e.get("type") == "SIMPLE_CHEMICAL"]
    organs = [e["text"] for e in enriched_entities if e.get("type") in {"ORGAN", "ANATOMICAL_SYSTEM"}]
    path = [e["text"] for e in enriched_entities if e.get("type") in {"CANCER", "PATHOLOGICAL_FORMATION"}]
    genes = [e["text"] for e in enriched_entities if e.get("type") == "GENE_OR_GENE_PRODUCT"]
    return {
        "has_medication": bool(meds),
        "anatomical_focus": sorted(set(organs)),
        "key_findings": {
            "medications": sorted(set(meds)),
            "organs_affected": sorted(set(organs)),
            "pathology": sorted(set(path)),
            "genetic_targets": sorted(set(genes)),
        },
        "high_priority_detected": any(e.get("priority") == "high" for e in enriched_entities),
    }


def group_entities_by_type(enriched_entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for e in enriched_entities:
        grouped.setdefault(e["type"], []).append(e)
    return grouped


def filter_entities(enriched_entities: List[Dict[str, Any]], types: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not types:
        return enriched_entities
    requested = {t.strip() for t in types if t.strip()}
    return [e for e in enriched_entities if e["type"] in requested]


def load_model() -> bool:
    global nlp
    try:
        logger.info(f"Loading SciSpacy model: {MODEL_NAME}")
        nlp = spacy.load(MODEL_NAME)
        logger.info("Model loaded successfully")
        return True
    except Exception as e:
        logger.exception(f"Failed to load model {MODEL_NAME}: {e}")
        return False


@app.route("/health")
def health() -> tuple[dict[str, Any], int]:
    """Health check endpoint"""
    if nlp is None:
        return {"status": "error", "message": "Model not loaded"}, 500
    return {"status": "ok", "model": MODEL_NAME}, 200


@app.route("/")
def root() -> dict[str, Any]:
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
def info() -> tuple[dict[str, Any], int]:
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
    return {"model": MODEL_NAME, "pipeline": nlp.pipe_names, "entities": entities}, 200


@app.route("/analyze", methods=["POST"])
def analyze() -> tuple[dict[str, Any], int]:
    """Analyze text for biomedical entities.

    Enrichment is OPTIONAL. Control via:
      - query/body param: enrich=true|false
      - env default: DEFAULT_ENRICH (true/false)
    Without enrichment only raw entities (text,label,start,end,description) are returned.
    """
    if nlp is None:
        return {"error": "Model not loaded"}, 500

    try:
        data = request.get_json()
        if not data or "text" not in data:
            return {"error": "Missing 'text' field in request"}, 400

        text = data["text"]
        if not text.strip():
            return {"error": "Empty text provided"}, 400

        # Determine enrichment preference
        req_json = data if isinstance(data, dict) else {}
        default_enrich = os.environ.get("DEFAULT_ENRICH", "false").lower() == "true"
        enrich_param = request.args.get("enrich")
        enrich = (
            req_json.get("enrich")
            if "enrich" in req_json
            else (enrich_param.lower() == "true" if enrich_param else default_enrich)
        )

        doc = nlp(text)

        # Caching
        ck = _cache_key(text, bool(enrich and (ENTITY_METADATA or ENTITY_RELATIONSHIPS)))
        cached = _cache_get(ck)
        if cached:
            return cached, 200
        sentences = [sent.text.strip() for sent in doc.sents]
        tokens = [
            {
                "text": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "tag": token.tag_,
                "is_alpha": token.is_alpha,
                "is_stop": token.is_stop,
            }
            for token in doc
            if not token.is_space
        ]
        if enrich and (ENTITY_METADATA or ENTITY_RELATIONSHIPS):
            enriched_entities = [enrich_entity(ent) for ent in doc.ents]
            entities_by_type = group_entities_by_type(enriched_entities)
            high_priority_entities = [e for e in enriched_entities if e.get("priority") == "high"]
            clinical_summary = build_clinical_summary(enriched_entities)
            response: Dict[str, Any] = {
                "text": text,
                "entities": enriched_entities,
                "entities_by_type": entities_by_type,
                "high_priority_entities": high_priority_entities,
                **({"clinical_summary": clinical_summary} if clinical_summary else {}),
                "sentences": sentences,
                "tokens": tokens,
                "entity_count": len(enriched_entities),
                "sentence_count": len(sentences),
                "token_count": len(tokens),
                "schema_version": 2,
                "enriched": True,
            }
            _cache_put(ck, response)
            return response, 200
        else:
            simple_entities = [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "description": spacy.explain(ent.label_) or ent.label_,
                }
                for ent in doc.ents
            ]
            response = {
                "text": text,
                "entities": simple_entities,
                "entity_count": len(simple_entities),
                "sentences": sentences,
                "sentence_count": len(sentences),
                "tokens": tokens,
                "token_count": len(tokens),
                "schema_version": 1,
                "enriched": False,
            }
            _cache_put(ck, response)
            return response, 200

    except Exception as e:
        logger.exception(f"Error processing text: {e}")
        return {"error": f"Processing failed: {str(e)}"}, 500


@app.route("/extract-by-type", methods=["POST", "GET"])
def extract_by_type() -> Tuple[Dict[str, Any], int]:
    """Filtered extraction endpoint (requires enrichment metadata).

    If metadata not loaded or enrichment disabled, returns 400 to signal the caller
    to fallback to /analyze + local filtering.
    """
    if nlp is None:
        return {"error": "Model not loaded"}, 500
    if not (ENTITY_METADATA or ENTITY_RELATIONSHIPS):
        return {"error": "Metadata not loaded; /extract-by-type unavailable"}, 400

    if request.method == "GET":
        text = request.args.get("text", "")
        types_param = request.args.get("types", "")
        types_list = [t for t in types_param.split(",") if t]
    else:
        payload = request.get_json(silent=True) or {}
        text = payload.get("text", "")
        types_list = payload.get("types") or []

    if not text.strip():
        return {"error": "Missing or empty text"}, 400

    doc = nlp(text)
    enriched_entities = [enrich_entity(ent) for ent in doc.ents]
    filtered = filter_entities(enriched_entities, types_list)
    response = {
        "text": text,
        "requested_types": types_list,
        "entities": filtered,
        "entity_count": len(filtered),
        "schema_version": 2,
    }
    return response, 200


@app.route("/metadata", methods=["GET"])
def metadata_info() -> Tuple[Dict[str, Any], int]:
    """Expose currently loaded external metadata (no heavy computation)."""
    return {
        "entity_types": list(ENTITY_METADATA.keys()),
        "has_relationships": bool(ENTITY_RELATIONSHIPS),
        "relationship_count": len(ENTITY_RELATIONSHIPS),
        "enrichment_enabled": bool(ENTITY_METADATA or ENTITY_RELATIONSHIPS),
    }, 200


@app.route("/cache/stats", methods=["GET"])
def cache_stats() -> Tuple[Dict[str, Any], int]:
    return _cache_stats(), 200


if __name__ == "__main__":
    # Load the model on startup
    if not load_model():
        logger.error("Failed to load model, exiting")
        sys.exit(1)

    # Get configuration from environment
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 8001))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"Starting SciSpacy server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
