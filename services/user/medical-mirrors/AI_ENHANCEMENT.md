# ICD-10 AI-Driven Enhancement

## Overview
The medical-mirrors service now supports AI-driven enhancement for ICD-10 codes using SciSpacy NLP and Ollama LLM, replacing hardcoded medical dictionaries with intelligent, context-aware enrichment.

## Features

### AI-Driven Mode (Recommended)
- **SciSpacy NLP**: Extracts medical entities without hardcoding
- **Ollama LLM**: Generates synonyms and clinical notes using medical understanding
- **No hardcoded knowledge**: Dynamic, context-aware enhancement
- **PHI-safe**: Local LLM ensures no data leaves the premises

### Pattern-Based Mode (Fallback)
- Uses regex patterns and predefined medical dictionaries
- Faster but less comprehensive
- Used as fallback when AI services are unavailable

## Configuration

### Default Mode (AI Enhancement)
AI enhancement is **enabled by default** for robustness and data quality. The service will automatically use AI-driven enhancement when available.

### Disable AI Enhancement (Use Pattern-Based)
To explicitly disable AI enhancement and use pattern-based mode:
```bash
USE_AI_ENHANCEMENT=false
```

Or update the service configuration:
```yaml
# medical-mirrors.conf
env=...,USE_AI_ENHANCEMENT=false
```

### Prerequisites for AI Mode
1. **SciSpacy Service**: Must be running at port 8080
   ```bash
   make scispacy-run
   make scispacy-health
   ```

2. **Ollama Service**: Must be running at port 11434 with llama3.2:latest model
   ```bash
   ollama serve
   ollama pull llama3.2:latest
   ```

## Usage

### Via Make Commands
```bash
# Run with default AI enhancement
make medical-mirrors-update

# Quick test with AI enhancement (default)
make medical-mirrors-quick-test

# Explicitly disable AI and use pattern-based
USE_AI_ENHANCEMENT=false make medical-mirrors-update
```

### Via Direct Script
```bash
# AI-driven mode (default)
python3 src/icd10/icd10_enrichment.py

# Explicitly use pattern-based mode
python3 src/icd10/icd10_enrichment.py --no-ai

# Or via environment
USE_AI=false python3 src/icd10/icd10_enrichment.py
```

### Via API Endpoint
```bash
# The service automatically uses the configured mode
curl -X POST http://localhost:8081/smart-update
```

## Coverage Improvements

### Pattern-Based Enhancement
- Synonyms: 0.02% → 24.4%
- Inclusion Notes: 0% → 16%
- Exclusion Notes: 0% → 1.1%
- Children Codes: 2.3% → 21.7%

### AI-Driven Enhancement (Expected)
- Synonyms: 0.02% → 40-60%
- Inclusion Notes: 0% → 30-50%
- Exclusion Notes: 0% → 20-40%
- Clinical Context: Added for all codes

## Architecture

### Components
1. **SciSpacy Client** (`src/icd10/scispacy_client.py`)
   - Biomedical entity recognition
   - Medical concept extraction
   - No hardcoded medical terms

2. **Ollama Client** (`src/icd10/llm_client.py`)
   - Medical text generation
   - Context-aware synonym creation
   - Clinical note generation

3. **AI Enhancer** (`src/icd10/icd10_ai_enrichment.py`)
   - Orchestrates AI services
   - Batch processing with rate limiting
   - Progress tracking and statistics

4. **Main Enhancer** (`src/icd10/icd10_enrichment.py`)
   - Mode selection (AI vs pattern)
   - Database integration
   - Backward compatibility

## Testing

### Test AI Services
```bash
# Test AI enhancement capabilities
python3 tests/icd10/test_ai_enhancement.py

# Test with quick dataset
USE_AI_ENHANCEMENT=true QUICK_TEST=true make medical-mirrors-update
```

### Monitor Progress
```bash
# Watch enhancement progress
make medical-mirrors-progress

# Check enhancement statistics
make medical-mirrors-logs | grep "enhancement"
```

## Performance Considerations

### AI Mode
- **Slower**: ~10-20 codes per second due to AI processing
- **Higher quality**: More comprehensive and accurate enhancements
- **Resource intensive**: Requires GPU for optimal Ollama performance

### Pattern Mode
- **Faster**: ~100-200 codes per second
- **Lower quality**: Limited to predefined patterns
- **CPU efficient**: No GPU required

## Troubleshooting

### AI Services Not Available
```bash
# Check SciSpacy
curl http://localhost:8080/health

# Check Ollama
curl http://localhost:11434/api/tags

# Start services if needed
make scispacy-run
ollama serve
```

### Slow Performance
- Increase batch size in `icd10_enrichment.py`
- Ensure GPU is available for Ollama
- Consider running overnight for full dataset

### Low Enhancement Coverage
- Verify AI services are healthy
- Check for rate limiting in logs
- Ensure proper model is loaded (llama3.2:latest)

## Future Enhancements

1. **Model Fine-tuning**: Train specialized medical LLM
2. **Caching Layer**: Cache AI responses for common terms
3. **Parallel Processing**: Multi-threaded AI calls
4. **Quality Metrics**: Automated enhancement quality scoring
5. **Billing Codes**: Extend AI enhancement to billing codes