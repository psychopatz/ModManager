"""
Tag confidence scoring - Evaluates quality of auto-generated tags.
Identifies items that need manual review due to low confidence.
"""
from .matcher import match_item, compare_signatures


class TagConfidenceScorer:
    """
    Scores the quality of auto-generated tags.
    Multi-component scoring across:
    - Category confidence (how sure about category)
    - Tag specificity (how detailed are tags)
    - Property coverage (how many properties used)
    - Match clarity (how clear the signature match)
    """
    
    def __init__(self, config=None):
        """
        Initialize scorer.
        
        Args:
            config: Configuration dict with weights (optional)
        """
        self.config = config or {
            'category_weight': 0.35,
            'tag_weight': 0.35,
            'property_weight': 0.20,
            'clarity_weight': 0.10,
            'default_threshold': 0.65
        }
    
    def score_tags(self, item_id, props, tag_result):
        """
        Score the quality of tags for an item.
        
        Args:
            item_id: Item identifier
            props: Properties string
            tag_result: Result from auto_tag() or tag_item()
        
        Returns:
            dict: Scoring result with:
                - overall_score: Final score (0-1)
                - category_confidence: Category match quality (0-1)
                - tag_specificity: Tag detail level (0-1)
                - property_coverage: Properties used (0-1)
                - clarity_score: Match clarity (0-1)
                - confidence_level: Text level (VERY_HIGH|HIGH|MEDIUM|LOW|VERY_LOW)
                - below_threshold: Bool if below default threshold
                - recommendations: List of improvement suggestions
        """
        scores = {}
        
        # Component 1: Category Confidence (35%)
        scores['category_confidence'] = min(1.0, tag_result['confidence'] * 1.25)
        
        # Component 2: Tag Specificity (35%)
        scores['tag_specificity'] = self._score_tag_specificity(tag_result['tags'])
        
        # Component 3: Property Coverage (20%)
        scores['property_coverage'] = self._score_property_coverage(props, tag_result['details'])
        
        # Component 4: Clarity Score (10%)
        scores['clarity_score'] = self._score_clarity(item_id, props, tag_result)
        
        # Calculate overall
        overall = (
            scores['category_confidence'] * self.config['category_weight'] +
            scores['tag_specificity'] * self.config['tag_weight'] +
            scores['property_coverage'] * self.config['property_weight'] +
            scores['clarity_score'] * self.config['clarity_weight']
        )
        
        overall = min(1.0, max(0.0, overall))
        
        # Get text confidence level
        confidence_level = self._get_confidence_level(overall)
        
        # Generate recommendations
        recommendations = self._get_recommendations(scores, tag_result)
        
        # Check if below threshold
        below_threshold = overall < self.config['default_threshold']
        
        return {
            'overall_score': round(overall, 3),
            'confidence_level': confidence_level,
            'category_confidence': round(scores['category_confidence'], 3),
            'tag_specificity': round(scores['tag_specificity'], 3),
            'property_coverage': round(scores['property_coverage'], 3),
            'clarity_score': round(scores['clarity_score'], 3),
            'below_threshold': below_threshold,
            'recommendations': recommendations
        }
    
    @staticmethod
    def _score_tag_specificity(tags):
        """Score how specific and detailed the tags are."""
        if not tags:
            return 0.0
        
        score = 0.0
        
        # Base score for number of tags
        if len(tags) >= 5:
            score += 0.4
        elif len(tags) >= 3:
            score += 0.3
        elif len(tags) >= 1:
            score += 0.2
        
        # Bonus for hierarchical depth
        for tag in tags:
            if '.' in tag:
                depth = tag.count('.')
                if depth >= 3:
                    score += 0.05
                elif depth >= 2:
                    score += 0.03
        
        # Bonus for descriptive tags beyond primary
        descriptive_roots = {'Quality', 'Origin', 'Theme', 'Rarity'}
        descriptive_count = sum(1 for tag in tags if any(tag.startswith(root) for root in descriptive_roots))
        score += (descriptive_count * 0.1)
        
        return min(1.0, score)
    
    @staticmethod
    def _score_property_coverage(props, details):
        """Score how well properties are being used."""
        if not props or not details:
            return 0.2
        
        # Count property references
        props_lower = props.lower()
        coverage_count = 0
        
        # Check for key property usage
        property_checks = [
            ('Weight', props_lower),
            ('Damage', props_lower),
            ('Capacity', props_lower),
            ('Condition', props_lower),
            ('Defense', props_lower),
            ('Hunger', props_lower),
            ('Calories', props_lower),
            ('Fresh', props_lower)
        ]
        
        for prop_name, p_str in property_checks:
            if prop_name.lower() in p_str:
                coverage_count += 1
        
        # Normalize to 0-1
        return min(1.0, coverage_count / 8.0)
    
    @staticmethod
    def _score_clarity(item_id, props, tag_result):
        """Score clarity of categorization."""
        score = 0.0
        
        # ID naming convention score
        if len(item_id) > 3 and len(item_id) < 50:
            score += 0.25
        
        # Category match score
        if tag_result['category'] != 'Unknown':
            score += 0.25
        
        # Descriptor completeness
        descriptors = sum([
            tag_result['rarity'] is not None,
            tag_result['quality'] is not None,
            tag_result['origin'] is not None,
            len(tag_result['themes']) > 0
        ])
        score += (descriptors * 0.1)  # Max 0.4
        
        # Primary tag quality
        if tag_result['primary_tag'] and tag_result['primary_tag'] != 'Misc.General':
            score += 0.15
        
        return min(1.0, score)
    
    @staticmethod
    def _get_confidence_level(score):
        """Convert numeric score to text confidence level."""
        if score >= 0.85:
            return 'VERY_HIGH'
        elif score >= 0.70:
            return 'HIGH'
        elif score >= 0.50:
            return 'MEDIUM'
        elif score >= 0.30:
            return 'LOW'
        else:
            return 'VERY_LOW'
    
    @staticmethod
    def _get_recommendations(scores, tag_result):
        """Generate recommendations for improvement."""
        recommendations = []
        
        # Category confidence
        if scores['category_confidence'] < 0.4:
            recommendations.append("Review category detection - unclear item type")
        elif scores['category_confidence'] < 0.6:
            recommendations.append("Improve category match confidence by adding more properties")
        
        # Tag specificity
        if scores['tag_specificity'] < 0.4:
            recommendations.append("Assign more specific tags to clarify purpose")
        elif scores['tag_specificity'] < 0.6:
            recommendations.append("Add quality/origin/theme descriptors for clarity")
        
        # Property coverage
        if scores['property_coverage'] < 0.3:
            recommendations.append("Item is missing key properties for accurate analysis")
        elif scores['property_coverage'] < 0.5:
            recommendations.append("Add more property definitions to improve scoring")
        
        # Clarity
        if scores['clarity_score'] < 0.4:
            recommendations.append("Item ID or category is ambiguous - manual review recommended")
        
        # For unmatched items
        if tag_result['category'] == 'Unknown':
            recommendations.append("Item did not match any auto-tagging signature")
            recommendations.append("Consider manual categorization or property adjustment")
        
        return recommendations
    
    def score_batch(self, items_dict, tag_results):
        """
        Score multiple items at once.
        
        Args:
            items_dict: Dict of {item_id: props}
            tag_results: Dict of {item_id: tag_result}
        
        Returns:
            dict: Dict of {item_id: confidence_score}
        """
        scores = {}
        for item_id, props in items_dict.items():
            tag_result = tag_results.get(item_id, {})
            scores[item_id] = self.score_tags(item_id, props, tag_result)
        return scores
    
    def find_below_threshold(self, scores, threshold=None):
        """
        Find items below confidence threshold.
        
        Args:
            scores: Dict of {item_id: confidence_score} from score_batch()
            threshold: Confidence threshold (uses default if None)
        
        Returns:
            list: List of {item_id, overall_score, confidence_level, recommendations}
        """
        threshold = threshold or self.config['default_threshold']
        
        below = []
        for item_id, score in scores.items():
            if score['overall_score'] < threshold:
                below.append({
                    'item_id': item_id,
                    'overall_score': score['overall_score'],
                    'confidence_level': score['confidence_level'],
                    'category_confidence': score['category_confidence'],
                    'tag_specificity': score['tag_specificity'],
                    'property_coverage': score['property_coverage'],
                    'clarity_score': score['clarity_score'],
                    'recommendations': score['recommendations']
                })
        
        # Sort by score ascending (lowest confidence first)
        return sorted(below, key=lambda x: x['overall_score'])
