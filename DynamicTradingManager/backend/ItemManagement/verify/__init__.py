"""
Verify module - Modular item verification and analysis system
Handles vanilla/mod comparison, item analysis, and confidence scoring
"""

from .vanilla_loader import get_vanilla_data, get_opening_maps
from .mod_loader import get_mod_data, get_mod_duplicates
from .tag_validator import get_dynamic_tags
from .item_analyzer import calculate_worth, analyze_item_stats
from .confidence import score_item_confidence, find_below_threshold, generate_confidence_report
from .reporters import write_hierarchical_files, write_mod_duplicates, write_confidence_report
from .helpers import sanitize_path, get_stat

__all__ = [
    'get_vanilla_data',
    'get_opening_maps',
    'get_mod_data',
    'get_mod_duplicates',
    'get_dynamic_tags',
    'calculate_worth',
    'analyze_item_stats',
    'score_item_confidence',
    'find_below_threshold',
    'generate_confidence_report',
    'write_hierarchical_files',
    'write_mod_duplicates',
    'write_confidence_report',
    'sanitize_path',
    'get_stat'
]
