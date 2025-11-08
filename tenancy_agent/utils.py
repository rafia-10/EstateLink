"""Utility functions for data processing"""
from datetime import timedelta
from typing import List, Dict, Any, Optional


def rows_to_dicts(columns: List[str], rows: List[tuple], timedelta_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Convert database rows to list of dictionaries

    Args:
        columns: List of column names
        rows: List of row tuples
        timedelta_fields: Optional list of fields to convert from timedelta to int

    Returns:
        List of dictionaries
    """
    result = []
    for row in rows:
        item = dict(zip(columns, row))
        # Convert timedelta fields to integers
        if timedelta_fields:
            for field in timedelta_fields:
                if isinstance(item.get(field), timedelta):
                    item[field] = item[field].days
        result.append(item)
    return result
