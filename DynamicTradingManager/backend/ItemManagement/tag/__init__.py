"""
Auto-tagging subsystem - Property-based item categorization.

Main entry points:
- auto_tag(item_id, props) - Tag a single item
- AutoTagger.tag_batch(items_dict) - Tag multiple items
- TagConfidenceScorer - Score tag quality

Example usage:
    from src.tag import auto_tag, AutoTagger, TagConfidenceScorer
    
    # Quick tagging
    result = auto_tag('Katana', props_string)
    print(result['tags'])
    
    # Batch tagging with statistics
    tagger = AutoTagger()
    results = tagger.tag_batch(all_items)
    print(tagger.get_stats())
    
    # Score tag quality
    scorer = TagConfidenceScorer()
    scores = scorer.score_batch(all_items, results)
    below_threshold = scorer.find_below_threshold(scores)
"""

from .analyzer import AutoTagger, auto_tag
from .confidence import TagConfidenceScorer
from .matcher import match_item, match_batch, get_multi_category_matches, compare_signatures
from .helpers import PropertyAnalyzer, has_property, get_stat, extract_tags_from_props

__all__ = [
    # Main API
    'auto_tag',
    'AutoTagger',
    'TagConfidenceScorer',
    
    # Utility functions
    'match_item',
    'match_batch',
    'get_multi_category_matches',
    'compare_signatures',
    'PropertyAnalyzer',
    'has_property',
    'get_stat',
    'extract_tags_from_props',
]

__version__ = '1.0.0'
