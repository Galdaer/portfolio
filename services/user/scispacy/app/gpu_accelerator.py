#!/usr/bin/env python3
"""
GPU Accelerator for SciSpacy using PyTorch
Works around CuPy issues with sm_120 architecture
"""

import torch
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GPUAccelerator:
    """GPU acceleration for SpaCy operations using PyTorch instead of CuPy"""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            logger.info(f"GPU Accelerator initialized on {torch.cuda.get_device_name(0)}")
        else:
            logger.warning("GPU Accelerator running on CPU")
    
    def batch_process_texts(self, nlp, texts: List[str], batch_size: int = 32) -> List[Any]:
        """
        Process texts in batches on GPU using PyTorch
        """
        docs = []
        
        # Process in batches for efficiency
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Use nlp.pipe for batch processing (more efficient)
            batch_docs = list(nlp.pipe(batch, batch_size=batch_size))
            docs.extend(batch_docs)
            
            # Clear GPU cache periodically
            if torch.cuda.is_available() and i % (batch_size * 10) == 0:
                torch.cuda.empty_cache()
        
        return docs
    
    def accelerate_similarity(self, vectors1: np.ndarray, vectors2: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity on GPU using PyTorch
        """
        # Convert to PyTorch tensors and move to GPU
        t1 = torch.from_numpy(vectors1).float().to(self.device)
        t2 = torch.from_numpy(vectors2).float().to(self.device)
        
        # Normalize vectors
        t1_norm = torch.nn.functional.normalize(t1, p=2, dim=1)
        t2_norm = torch.nn.functional.normalize(t2, p=2, dim=1)
        
        # Compute cosine similarity
        similarity = torch.mm(t1_norm, t2_norm.t())
        
        # Move back to CPU and convert to numpy
        return similarity.cpu().numpy()
    
    def accelerate_embeddings(self, texts: List[str], model) -> torch.Tensor:
        """
        Generate embeddings on GPU using a transformer model
        """
        if hasattr(model, 'encode'):
            # For sentence transformers
            with torch.cuda.amp.autocast():
                embeddings = model.encode(texts, convert_to_tensor=True, device=self.device)
            return embeddings
        else:
            # For other models, process through SpaCy
            docs = self.batch_process_texts(model, texts)
            vectors = [doc.vector for doc in docs]
            return torch.tensor(vectors, device=self.device)

# Global instance
gpu_accelerator = None

def get_gpu_accelerator():
    """Get or create GPU accelerator instance"""
    global gpu_accelerator
    if gpu_accelerator is None:
        gpu_accelerator = GPUAccelerator()
    return gpu_accelerator