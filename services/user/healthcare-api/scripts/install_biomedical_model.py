#!/usr/bin/env python3
"""
Install biomedical spaCy model for PHI detection.
This is done separately to avoid compilation issues during main requirements install.
"""

import subprocess
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_biomedical_model():
    """Install the biomedical spaCy model."""
    try:
        logger.info("Installing scispacy...")
        subprocess.run([sys.executable, "-m", "pip", "install", "scispacy>=0.5.3"], check=True)
        
        logger.info("Installing biomedical spaCy model...")
        model_url = "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_ner_bionlp13cg_md-0.5.3.tar.gz"
        subprocess.run([sys.executable, "-m", "pip", "install", model_url], check=True)
        
        logger.info("✅ Biomedical model installed successfully")
        
        # Test the model
        logger.info("Testing biomedical model...")
        import spacy
        nlp = spacy.load("en_ner_bionlp13cg_md")
        # Test with a simple sentence
        doc = nlp("patient with diabetes")
        logger.info(f"✅ Biomedical model loaded successfully: {len(doc.ents)} entities found")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install biomedical model: {e}")
        logger.info("Falling back to standard English model...")
        try:
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
            logger.info("✅ Standard English model installed as fallback")
        except subprocess.CalledProcessError as fallback_e:
            logger.error(f"❌ Failed to install fallback model: {fallback_e}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_biomedical_model()
