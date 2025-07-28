"""Common utilities for the scraping manager application."""

import hashlib
import json
from typing import Dict, List, Any


def generate_hash(data: Dict[str, Any], fields: List[str]) -> str:
    """
    Generate a SHA256 hash from specified fields in a dictionary.
    
    Args:
        data: Dictionary containing the data to hash
        fields: List of field names to include in the hash
        
    Returns:
        SHA256 hash as a hex string
    """
    hash_data = {}
    for field in fields:
        if field in data:
            hash_data[field] = data[field]
    
    # Sort keys to ensure consistent hashing
    hash_string = json.dumps(hash_data, sort_keys=True)
    return hashlib.sha256(hash_string.encode()).hexdigest()


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "2m 30s" or "1h 15m"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"