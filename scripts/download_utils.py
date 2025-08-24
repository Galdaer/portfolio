#!/usr/bin/env python3
"""
Download Utilities for Medical Data Scripts

Shared utility functions for monitoring disk space, logging,
and preventing storage bloat during downloads.
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def check_disk_space(path: str, min_free_gb: float = 10.0) -> Dict[str, Any]:
    """
    Check available disk space and warn if running low.
    
    Args:
        path: Directory path to check
        min_free_gb: Minimum free space in GB before warning
        
    Returns:
        Dict with disk usage information and warnings
    """
    try:
        total, used, free = shutil.disk_usage(path)
        
        usage_info = {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round((used / total) * 100, 2),
            "warnings": []
        }
        
        # Generate warnings
        if usage_info["free_gb"] < min_free_gb:
            usage_info["warnings"].append(
                f"LOW DISK SPACE: Only {usage_info['free_gb']:.1f}GB free "
                f"(minimum recommended: {min_free_gb}GB)"
            )
        
        if usage_info["usage_percent"] > 90:
            usage_info["warnings"].append(
                f"CRITICAL: Disk usage at {usage_info['usage_percent']:.1f}% - "
                "immediate cleanup recommended"
            )
        elif usage_info["usage_percent"] > 80:
            usage_info["warnings"].append(
                f"WARNING: Disk usage at {usage_info['usage_percent']:.1f}% - "
                "consider cleanup soon"
            )
        
        return usage_info
        
    except Exception as e:
        return {
            "error": str(e),
            "warnings": [f"Could not check disk space: {e}"]
        }


def log_download_progress(logger: logging.Logger, 
                         filename: str, 
                         current: int, 
                         total: int,
                         file_size_mb: Optional[float] = None) -> None:
    """
    Log download progress with disk space awareness.
    
    Args:
        logger: Logger instance
        filename: Name of file being downloaded
        current: Current progress (bytes or items)
        total: Total expected (bytes or items)
        file_size_mb: File size in MB (optional)
    """
    percent = (current / total * 100) if total > 0 else 0
    
    # Basic progress log
    if file_size_mb:
        logger.info(f"Downloading {filename}: {percent:.1f}% ({file_size_mb:.1f}MB)")
    else:
        logger.info(f"Processing {filename}: {current}/{total} ({percent:.1f}%)")
    
    # Check disk space every 10% for large downloads
    if file_size_mb and file_size_mb > 100 and percent % 10 < 1:
        disk_info = check_disk_space(str(Path(filename).parent))
        for warning in disk_info.get("warnings", []):
            logger.warning(f"DISK SPACE: {warning}")


def prevent_pretty_printing() -> Dict[str, Any]:
    """
    Return safe JSON serialization parameters to prevent pretty printing.
    
    Returns:
        Dict of parameters for json.dump() without indent/formatting
    """
    return {
        "ensure_ascii": False,
        "separators": (',', ':'),  # Compact separators
        "default": str
    }


def log_file_operation(logger: logging.Logger, 
                      operation: str, 
                      file_path: str,
                      size_mb: Optional[float] = None) -> None:
    """
    Log file operations with size information.
    
    Args:
        logger: Logger instance
        operation: Type of operation (created, compressed, deleted, etc.)
        file_path: Path to the file
        size_mb: File size in MB (optional)
    """
    size_info = f" ({size_mb:.1f}MB)" if size_mb else ""
    logger.info(f"File {operation}: {Path(file_path).name}{size_info}")


def get_directory_size_mb(directory: Path) -> float:
    """
    Get total size of directory in MB.
    
    Args:
        directory: Path to directory
        
    Returns:
        Size in MB
    """
    total_size = 0
    try:
        for file in directory.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
    except (OSError, PermissionError):
        pass
    
    return round(total_size / (1024**2), 2)


def create_download_logger(name: str, log_dir: Optional[str] = None) -> logging.Logger:
    """
    Create a standardized logger for download scripts.
    
    Args:
        name: Logger name (usually script name)
        log_dir: Directory for log files (optional)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler if log directory specified
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_path / f"{name}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed formatter for file
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Simple formatter for console
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def summarize_download_session(logger: logging.Logger, 
                             stats: Dict[str, Any],
                             data_dir: str) -> None:
    """
    Log a summary of the download session with disk usage.
    
    Args:
        logger: Logger instance
        stats: Dictionary of download statistics
        data_dir: Path to data directory for disk usage check
    """
    logger.info("=" * 60)
    logger.info("DOWNLOAD SESSION SUMMARY")
    logger.info("=" * 60)
    
    # Log statistics
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            if key.endswith('_size') or key.endswith('_bytes'):
                # Format size values
                mb_value = value / (1024**2) if key.endswith('_bytes') else value
                logger.info(f"{key.replace('_', ' ').title()}: {mb_value:.1f} MB")
            else:
                logger.info(f"{key.replace('_', ' ').title()}: {value}")
        else:
            logger.info(f"{key.replace('_', ' ').title()}: {value}")
    
    # Check final disk usage
    disk_info = check_disk_space(data_dir)
    logger.info(f"Final Disk Usage: {disk_info.get('usage_percent', 'Unknown')}%")
    logger.info(f"Free Space: {disk_info.get('free_gb', 'Unknown')} GB")
    
    # Log any warnings
    for warning in disk_info.get("warnings", []):
        logger.warning(warning)
    
    logger.info("=" * 60)


# Export commonly used functions
__all__ = [
    'check_disk_space',
    'log_download_progress', 
    'prevent_pretty_printing',
    'log_file_operation',
    'get_directory_size_mb',
    'create_download_logger',
    'summarize_download_session'
]