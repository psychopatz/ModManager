"""
Auto-tagging analyzer - Main entry point for property-based tagging.
Integrates signature matching with descriptor generation.
"""
import re

from .matcher import match_item, match_batch, get_multi_category_matches
from .helpers import PropertyAnalyzer


class AutoTagger:
    """
    Main class for automatic item tagging.
    Uses property-based signatures to categorize and tag items.
    """
    
    def __init__(self, default_confidence_threshold=0.4):
        """
        Initialize auto-tagger.
        
        Args:
            default_confidence_threshold: Minimum confidence to accept category match
        """
        self.threshold = default_confidence_threshold
        self.stats = {
            'processed': 0,
            'matched': 0,
            'unmatched': 0,
            'multi_match': 0
        }
    
    def tag_item(self, item_id, props):
        """
        Tag a single item.
        
        Args:
            item_id: Item identifier
            props: Properties string
        
        Returns:
            dict: Tagging result with:
                - primary_tag: Primary category tag (str)
                - tags: All tags (list)
                - rarity: Rarity descriptor (str)
                - quality: Quality descriptor (str)
                - origin: Origin descriptor (str)
                - themes: Theme tags (list)
                - confidence: Confidence score (float)
                - category: Matched category (str)
        """
        self.stats['processed'] += 1
        
        # Get best category match
        match = match_item(item_id, props)
        
        if not match['matched'] or match['confidence'] < self.threshold:
            self.stats['unmatched'] += 1
            return self._get_default_tags(item_id, props)
        
        self.stats['matched'] += 1
        
        # Build tag result
        result = {
            'item_id': item_id,
            'category': match['category'],
            'primary_tag': match['tags'][0] if match['tags'] else 'Misc.General',
            'confidence': match['confidence'],
            'tags': match['tags'],
            'rarity': self._determine_rarity(item_id, props),
            'quality': self._determine_quality(item_id, props),
            'origin': self._determine_origin(item_id, props),
            'themes': self._determine_themes(item_id, props),
            'details': match['details']
        }
        
        # Add quality/origin/theme tags if present
        if result['rarity']:
            result['tags'].append(f"Rarity.{result['rarity']}")
        if result['quality']:
            result['tags'].append(f"Quality.{result['quality']}")
        if result['origin']:
            result['tags'].append(f"Origin.{result['origin']}")
        for theme in result['themes']:
            result['tags'].append(f"Theme.{theme}")
        
        return result
    
    def tag_batch(self, items_dict):
        """
        Tag multiple items at once.
        
        Args:
            items_dict: Dict of {item_id: props}
        
        Returns:
            dict: Dict of {item_id: tag_result}
        """
        results = {}
        for item_id, props in items_dict.items():
            results[item_id] = self.tag_item(item_id, props)
        return results
    
    def find_multi_category_items(self, items_dict, min_confidence=0.3):
        """
        Find items that match multiple categories.
        Useful for identifying ambiguous items for manual review.
        
        Args:
            items_dict: Dict of {item_id: props}
            min_confidence: Minimum confidence threshold
        
        Returns:
            dict: Dict of {item_id: [multi_matches]}
        """
        multi_category_items = {}
        
        for item_id, props in items_dict.items():
            matches = get_multi_category_matches(item_id, props, min_confidence)
            if len(matches) > 1:
                multi_category_items[item_id] = matches
        
        self.stats['multi_match'] = len(multi_category_items)
        return multi_category_items
    
    def get_stats(self):
        """Get tagging statistics."""
        return {
            **self.stats,
            'match_rate': round(self.stats['matched'] / max(1, self.stats['processed']), 3)
        }
    
    def reset_stats(self):
        """Reset tagging statistics."""
        self.stats = {
            'processed': 0,
            'matched': 0,
            'unmatched': 0,
            'multi_match': 0
        }
    
    @staticmethod
    def _determine_rarity(item_id, props):
        """Determine rarity descriptor."""
        analyzer = PropertyAnalyzer(props)
        
        item_id_lower = item_id.lower()
        
        # Check for worldstatic (rare)
        if analyzer.has_property('WorldStaticModel'):
            return 'Rare'
        
        # Check for authority items
        if any(x in item_id for x in ['Police', 'Military', 'Army', 'Swat']):
            return 'Uncommon'
        
        # Check for sterile (uncommon)
        if analyzer.has_property('Sterile'):
            return 'Uncommon'
        
        # Skill books by level
        if 'SkillBook' in item_id or 'Book' in item_id:
            import re
            level_match = re.search(r'(\d+)$', item_id)
            if level_match:
                level = int(level_match.group(1))
                if level >= 5:
                    return 'Legendary'
                elif level >= 3:
                    return 'Rare'
                elif level >= 2:
                    return 'Uncommon'
        
        return 'Common'
    
    @staticmethod
    def _determine_quality(item_id, props):
        """Determine quality descriptor."""
        item_id_lower = item_id.lower()
        analyzer = PropertyAnalyzer(props)
        
        if analyzer.has_property('Sterile'):
            return 'Sterile'
        
        if any(x in item_id_lower for x in ['gold', 'diamond', 'designer', 'expensive']):
            return 'Luxury'
        
        if any(x in item_id_lower for x in ['empty', 'dirty', 'broken', 'scrap']):
            return 'Waste'
        
        return None
    
    @staticmethod
    def _determine_origin(item_id, props):
        """Determine source-of-item origin descriptor."""
        return 'Vanilla'
    
    @staticmethod
    def _determine_themes(item_id, props):
        """Determine theme descriptors."""
        themes = []
        item_id_lower = item_id.lower()
        normalized = re.sub(r'([a-z])([A-Z])', r'\1 \2', item_id or '').replace('_', ' ')
        item_tokens = set(token.lower() for token in re.findall(r'[A-Za-z]+', normalized))
        analyzer = PropertyAnalyzer(props)
        
        if any(x in item_id_lower for x in ['camp', 'outdoor', 'wilderness', 'survival']):
            themes.append('Survival')
        
        if any(x in item_id_lower for x in ['weapon', 'combat', 'tactical', 'armor']):
            themes.append('Combat')
        
        if any(x in item_id_lower for x in ['winter', 'warm', 'insulated', 'thermal']):
            insulation = analyzer.get_stat('Insulation')
            if insulation > 0.5:
                themes.append('Winter')

        if item_tokens.intersection({'police', 'sheriff', 'cop'}):
            themes.append('Police')
        if item_tokens.intersection({'military', 'army', 'tactical'}):
            themes.append('Militia')
        if item_tokens.intersection({'doctor', 'medic', 'medical', 'surgical', 'hospital'}):
            themes.append('Clinical')
        if item_tokens.intersection({'industrial', 'factory', 'warehouse'}):
            themes.append('Industrial')
        if item_tokens.intersection({'primitive', 'tribal', 'stoneage', 'ancestral'}):
            themes.append('Primitive')

        return list(dict.fromkeys(themes))
    
    @staticmethod
    def _get_default_tags(item_id, props):
        """Generate default tags for unmatched items."""
        return {
            'item_id': item_id,
            'category': 'Unknown',
            'primary_tag': 'Misc.General',
            'confidence': 0.0,
            'tags': ['Misc.General'],
            'rarity': 'Common',
            'quality': None,
            'origin': 'Vanilla',
            'themes': [],
            'details': {}
        }


# Convenience function
def auto_tag(item_id, props, threshold=0.4):
    """
    Quick auto-tagging for a single item.
    
    Args:
        item_id: Item identifier
        props: Properties string
        threshold: Confidence threshold (default 0.4)
    
    Returns:
        dict: Tag result
    """
    tagger = AutoTagger(threshold)
    return tagger.tag_item(item_id, props)
