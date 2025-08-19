# SciSpacy Service Integration Guide

## Overview
The SciSpacy service exposes biomedical entity extraction with optional enrichment. Agents can choose between lightweight pass-through output or enriched metadata-driven results by setting `enrich=true`.

## Endpoints
- `POST /analyze` – Required field: `text`. Optional enrichment via query/body param `enrich=true`.
- `GET /metadata` – Shows whether enrichment metadata is loaded.
- `GET /cache/stats` – Cache status (size, ttl, enabled).
- `POST/GET /extract-by-type` – Only available if metadata loaded.

## Enrichment
Provide an external YAML/JSON file referenced by `METADATA_PATH` with:
```yaml
entity_metadata:
  SIMPLE_CHEMICAL:
    category: chemical
    usage_hint: drugs, small molecules
    priority: high
    agent_relevance: [medical_search]
relationships:
  SIMPLE_CHEMICAL: [GENE_OR_GENE_PRODUCT]
```

If no metadata is loaded or `enrich` is false:
```json
{"schema_version":1, "enriched":false, "entities":[{"text":"aspirin","label":"SIMPLE_CHEMICAL"}]} 
```
With enrichment:
```json
{
  "schema_version":2,
  "enriched":true,
  "entities":[{"text":"aspirin","type":"SIMPLE_CHEMICAL","priority":"high", ...}],
  "entities_by_type": {"SIMPLE_CHEMICAL":[ ... ]},
  "high_priority_entities":[...]
}
```

## Caching
Enabled by default (`SCISPACY_CACHE=true`). Keys include metadata hash + enrichment flag + text.
Env vars:
- `SCISPACY_CACHE` (true/false)
- `SCISPACY_CACHE_SIZE` (default 256)
- `SCISPACY_CACHE_TTL` seconds (default 300, 0 = no TTL expiry)

Cache is invalidated automatically when metadata file changes (hash recalculated).

## Search Agent Usage
Medical search agent now:
1. Calls `/analyze?enrich=true`.
2. Prioritizes entities with `priority=high` (if enrichment active) by inserting them earlier in the concept list.
3. Falls back gracefully when enrichment not available (no `priority` fields).

## Recommended Query Construction
1. Start with unique high-priority entity texts.
2. Add ORGAN / ANATOMICAL_SYSTEM for contextual breadth.
3. Append SIMPLE_CHEMICAL and GENE_OR_GENE_PRODUCT for pharmacologic/genomic depth.
4. De-duplicate while preserving the weighting order.

## Error Handling Patterns
- 400 on missing text.
- 400 on `/extract-by-type` when metadata not loaded (caller should fallback to local filtering).
- 500 only on unexpected processing errors.

## Future Extensions
- Add optional confidence scoring from model pipeline if available.
- Support streaming sentence-level entity emission for long texts.
- Provide HEAD /warm endpoint for pre-loading model in orchestrators.

