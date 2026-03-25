"""
Confidence scoring system for item analysis and tagging
Identifies items below threshold for manual refinement
"""
from .helpers import get_stat, has_property
from .item_analyzer import analyze_item_stats


class ConfidenceScorer:
    """
    Scores item tagging and analysis confidence
    """
    
    def __init__(self, config=None):
        """
        Initialize confidence scorer with configuration
        
        Args:
            config: Dictionary of threshold values
        """
        self.config = config or {
            'tag_confidence_min': 0.6,      # 60% minimum confidence for tags
            'category_confidence_min': 0.7, # 70% minimum for category
            'property_coverage_min': 0.5,  # 50% of properties must be present
            'default_threshold': 0.65
        }
    
    def score_item(self, item_id, props, category, tags):
        """
        Calculate overall confidence score for an item
        
        Args:
            item_id: Item ID
            props: Properties string
            category: Detected category
            tags: List of assigned tags
        
        Returns:
            dict: Confidence data with score, breakdown, and flags
        """
        scores = {
            'category_confidence': self._score_category(category, props),
            'tag_confidence': self._score_tags(tags, props, category),
            'property_coverage': self._score_property_coverage(props),
            'clarity_score': self._score_clarity(item_id, props, category)
        }
        
        # Calculate weighted overall score
        overall = (
            scores['category_confidence'] * 0.35 +
            scores['tag_confidence'] * 0.35 +
            scores['property_coverage'] * 0.20 +
            scores['clarity_score'] * 0.10
        )
        
        is_below_threshold = overall < self.config['default_threshold']
        confidence_level = self._get_confidence_level(overall)
        
        return {
            'item_id': item_id,
            'overall_score': round(overall, 3),
            'confidence_level': confidence_level,
            'scores': {k: round(v, 3) for k, v in scores.items()},
            'is_below_threshold': is_below_threshold,
            'threshold': self.config['default_threshold']
        }
    
    def _score_category(self, category, props):
        """
        Score confidence in category detection
        
        Args:
            category: Detected category
            props: Properties string
        
        Returns:
            float: Score 0-1
        """
        score = 0.5
        
        # Check for definitive category indicators
        if has_property(props, 'DisplayCategory'):
            score += 0.3
        
        if category in ['Food', 'Weapon', 'Clothing', 'Medical']:
            score += 0.2  # Common categories = higher confidence
        
        if has_property(props, 'Type'):
            score += 0.0  # Type field exists
        
        # Check for multiple category indicators
        indicator_count = sum([
            has_property(props, 'DisplayCategory'),
            has_property(props, 'ItemType'),
            has_property(props, 'Categories'),
            has_property(props, 'BodyLocation'),
            has_property(props, 'EatType')
        ])
        
        if indicator_count >= 3:
            score = min(1.0, score + 0.2)
        
        return min(1.0, score)
    
    def _score_tags(self, tags, props, category):
        """
        Score confidence in tag assignment
        
        Args:
            tags: List of assigned tags
            props: Properties string
            category: Item category
        
        Returns:
            float: Score 0-1
        """
        if not tags:
            return 0.3  # No tags = low confidence
        
        score = 0.5
        
        # Primary tag confidence
        if len(tags) > 0 and tags[0].startswith(category):
            score += 0.3
        
        # Multiple tags = better coverage
        if len(tags) >= 3:
            score += 0.2
        
        # Rarity tag present
        if any('Rarity' in t for t in tags):
            score += 0.1
        
        # Special tags (Quality, Origin, Theme)
        special_tags = sum(1 for t in tags if any(x in t for x in ['Quality', 'Origin', 'Theme']))
        if special_tags > 0:
            score += 0.1
        
        return min(1.0, score)
    
    def _score_property_coverage(self, props):
        """
        Score based on how many properties are populated vs. missing
        
        Args:
            props: Properties string
        
        Returns:
            float: Score 0-1
        """
        # Count non-empty, non-zero properties
        critical_props = [
            'Weight', 'DisplayCategory', 'ItemType', 'Categories'
        ]
        
        found_critical = sum(1 for p in critical_props if has_property(props, p))
        critical_coverage = found_critical / len(critical_props) if critical_props else 0.0
        
        # Count optional properties
        optional_props = [
            'Capacity', 'MaxDamage', 'BiteDefense', 'HungerChange', 'Calories',
            'ConditionMax', 'Insulation', 'UsesBattery'
        ]
        
        found_optional = sum(1 for p in optional_props if has_property(props, p))
        optional_coverage = found_optional / len(optional_props) if optional_props else 0.0
        
        # Overall coverage
        overall_coverage = (critical_coverage * 0.7) + (optional_coverage * 0.3)
        
        return min(1.0, overall_coverage)
    
    def _score_clarity(self, item_id, props, category):
        """
        Score clarity of item purpose based on ID and properties
        
        Args:
            item_id: Item ID
            props: Properties string
            category: Item category
        
        Returns:
            float: Score 0-1
        """
        score = 0.5
        
        # Clear ID naming conventions
        if item_id[0].isupper():  # Proper naming
            score += 0.2
        
        # ID matches category
        id_lower = item_id.lower()
        if any(cat_word in id_lower for cat_word in ['food', 'weapon', 'clothing', 'medical', 'book', 'tool']):
            score += 0.2
        
        # Has disambiguating tags
        if has_property(props, 'Tags') and 'Tags' in props:
            tag_count = props.count('Tags')
            if tag_count > 1:  # Multiple tag definitions = unclear
                score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _get_confidence_level(self, score):
        """
        Convert numeric score to text confidence level
        
        Args:
            score: Numeric confidence score 0-1
        
        Returns:
            str: Confidence level label
        """
        if score >= 0.9:
            return 'VERY_HIGH'
        elif score >= 0.8:
            return 'HIGH'
        elif score >= 0.7:
            return 'MEDIUM'
        elif score >= 0.6:
            return 'LOW'
        else:
            return 'VERY_LOW'


def score_item_confidence(item_id, props, category, tags, config=None):
    """
    Convenience function to score single item
    
    Args:
        item_id: Item ID
        props: Properties string
        category: Category
        tags: Tags list
        config: Optional config dict
    
    Returns:
        dict: Confidence score data
    """
    scorer = ConfidenceScorer(config)
    return scorer.score_item(item_id, props, category, tags)


def find_below_threshold(items_data, threshold=0.65, config=None):
    """
    Find all items below confidence threshold
    
    Args:
        items_data: Dictionary of item data with tags
        threshold: Confidence threshold (0-1)
        config: Optional scorer config
    
    Returns:
        list: Items below threshold sorted by score
    """
    scorer = ConfidenceScorer(config)
    below_threshold = []
    
    for item_id, data in items_data.items():
        props = data.get('props', '')
        category = data.get('category', 'Unknown')
        tags = data.get('dt_tags', [])
        
        score_data = scorer.score_item(item_id, props, category, tags)
        
        if score_data['overall_score'] < threshold:
            score_data['item_data'] = data
            below_threshold.append(score_data)
    
    # Sort by score ascending (worst first)
    return sorted(below_threshold, key=lambda x: x['overall_score'])


def generate_confidence_report(below_threshold_items):
    """
    Generate formatted report of low-confidence items
    
    Args:
        below_threshold_items: List from find_below_threshold()
    
    Returns:
        str: Formatted report text
    """
    if not below_threshold_items:
        return "✓ All items passed confidence threshold!\n"
    
    report_lines = [
        f"\n⚠ {len(below_threshold_items)} ITEMS BELOW CONFIDENCE THRESHOLD\n",
        "=" * 100 + "\n"
    ]
    
    for item_data in below_threshold_items:
        report_lines.append(f"\n[{item_data['item_id']}]")
        report_lines.append(f"  Overall Score: {item_data['overall_score']} (Threshold: {item_data['threshold']})")
        report_lines.append(f"  Confidence Level: {item_data['confidence_level']}")
        report_lines.append(f"  Category: {item_data['item_data'].get('category', 'Unknown')}")
        report_lines.append(f"  Tags: {', '.join(item_data['item_data'].get('dt_tags', []))}")
        
        report_lines.append("  Score Breakdown:")
        for scorer_name, score in item_data['scores'].items():
            bar_length = int(score * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            report_lines.append(f"    {scorer_name:<25} {bar} {score:.1%}")
        
        # Recommendations
        recommendations = _get_refinement_recommendations(item_data)
        if recommendations:
            report_lines.append("  Recommendations:")
            for rec in recommendations:
                report_lines.append(f"    - {rec}")
    
    report_lines.append("\n" + "=" * 100)
    return "\n".join(report_lines)


def _get_refinement_recommendations(item_data):
    """
    Generate refinement recommendations based on score breakdown
    
    Args:
        item_data: Item score data
    
    Returns:
        list: Recommendation strings
    """
    recommendations = []
    scores = item_data['scores']
    
    if scores['category_confidence'] < 0.6:
        recommendations.append("Review category detection - unclear item type")
    
    if scores['tag_confidence'] < 0.6:
        recommendations.append("Assign more specific tags to clarify purpose")
    
    if scores['property_coverage'] < 0.4:
        recommendations.append("Item has minimal properties - verify it's not missing data")
    
    if scores['clarity_score'] < 0.5:
        recommendations.append("Item ID is unclear or doesn't match category - consider manual review")
    
    return recommendations
