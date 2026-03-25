"""
Auto-tagging usage examples and quick tests.
Run from Scripts/ directory: python -c "from ItemGenerator.src.tag.examples import *"
"""

# Example 1: Quick tag a single item
def example_single_item():
    """Tag a single item."""
    from ItemGenerator.src.tag import auto_tag
    
    katana_props = """
    item Katana {
        Type = Weapon,
        MinDamage = 10.0,
        MaxDamage = 15.0,
        ConditionMax = 50,
        Weight = 2.5,
    }
    """
    
    result = auto_tag('Katana', katana_props)
    
    print("=" * 60)
    print("EXAMPLE 1: Single Item Tagging")
    print("=" * 60)
    print(f"Item: {result['item_id']}")
    print(f"Category: {result['category']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Primary Tag: {result['primary_tag']}")
    print(f"All Tags: {', '.join(result['tags'])}")
    print()


# Example 2: Batch tagging with statistics
def example_batch_tagging():
    """Tag multiple items and show statistics."""
    from ItemGenerator.src.tag import AutoTagger
    
    items_dict = {
        'Katana': """
            item Katana {
                Type = Weapon,
                MinDamage = 10.0,
                MaxDamage = 15.0,
                ConditionMax = 50,
            }
        """,
        'Apple': """
            item Apple {
                Type = Food,
                HungerChange = 20,
                Calories = 50,
                DaysFresh = 15,
            }
        """,
        'NormalBackpack': """
            item NormalBackpack {
                Type = Clothing,
                Capacity = 40,
                WeightReduction = 0.3,
            }
        """
    }
    
    tagger = AutoTagger()
    results = tagger.tag_batch(items_dict)
    stats = tagger.get_stats()
    
    print("=" * 60)
    print("EXAMPLE 2: Batch Tagging")
    print("=" * 60)
    
    for item_id, result in results.items():
        print(f"\n{item_id}:")
        print(f"  Category: {result['category']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Tags: {', '.join(result['tags'][:3])}...")
    
    print(f"\nStatistics:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Matched: {stats['matched']}")
    print(f"  Match Rate: {stats['match_rate']:.1%}")
    print()


# Example 3: Quality scoring
def example_confidence_scoring():
    """Score the quality of tags."""
    from ItemGenerator.src.tag import AutoTagger, TagConfidenceScorer
    
    items_dict = {
        'Katana': """
            item Katana {
                Type = Weapon,
                MinDamage = 10.0,
                MaxDamage = 15.0,
                ConditionMax = 50,
                Weight = 2.5,
            }
        """,
        'MysteryItem': """
            item MysteryItem {
                Weight = 1.0,
            }
        """
    }
    
    tagger = AutoTagger()
    results = tagger.tag_batch(items_dict)
    
    scorer = TagConfidenceScorer()
    scores = scorer.score_batch(items_dict, results)
    
    print("=" * 60)
    print("EXAMPLE 3: Confidence Scoring")
    print("=" * 60)
    
    for item_id, score in scores.items():
        print(f"\n{item_id}:")
        print(f"  Overall Score: {score['overall_score']:.3f}")
        print(f"  Confidence Level: {score['confidence_level']}")
        print(f"  Component Breakdown:")
        print(f"    - Category: {score['category_confidence']:.3f}")
        print(f"    - Tag Specificity: {score['tag_specificity']:.3f}")
        print(f"    - Property Coverage: {score['property_coverage']:.3f}")
        print(f"    - Clarity: {score['clarity_score']:.3f}")
        
        if score['recommendations']:
            print(f"  Recommendations:")
            for rec in score['recommendations']:
                print(f"    - {rec}")
    print()


# Example 4: Find items below threshold
def example_below_threshold():
    """Find items that need manual review."""
    from ItemGenerator.src.tag import AutoTagger, TagConfidenceScorer
    
    items_dict = {
        'GoodItem': """
            item GoodItem {
                Type = Weapon,
                MinDamage = 10.0,
                MaxDamage = 15.0,
                ConditionMax = 50,
            }
        """,
        'PoorItem': """
            item PoorItem {
                Weight = 0.5,
            }
        """,
        'ConfusingItem': """
            item ConfusingItem {
                Capacity = 10,
                MinDamage = 2.0,
                HungerChange = 5,
            }
        """
    }
    
    tagger = AutoTagger()
    results = tagger.tag_batch(items_dict)
    
    scorer = TagConfidenceScorer()
    scores = scorer.score_batch(items_dict, results)
    
    below_items = scorer.find_below_threshold(scores, threshold=0.65)
    
    print("=" * 60)
    print("EXAMPLE 4: Below-Threshold Items (Need Manual Review)")
    print("=" * 60)
    print(f"Found {len(below_items)} items below 0.65 threshold:\n")
    
    for item in below_items:
        print(f"[{item['item_id']}]")
        print(f"  Score: {item['overall_score']:.3f} ({item['confidence_level']})")
        print(f"  Recommendations:")
        for rec in item['recommendations']:
            print(f"    - {rec}")
        print()


# Example 5: Multi-category items
def example_multi_category():
    """Find items that could fit multiple categories."""
    from ItemGenerator.src.tag import AutoTagger
    
    # Item that could be Food or Container or Resource
    ambiguous_item = """
        item MysteryBox {
            Capacity = 5,
            HungerChange = 10,
            UseDelta = 0.05,
            Weight = 1.0,
        }
    """
    
    tagger = AutoTagger()
    results = tagger.tag_batch({'MysteryBox': ambiguous_item})
    
    multi_items = tagger.find_multi_category_items({'MysteryBox': ambiguous_item})
    
    print("=" * 60)
    print("EXAMPLE 5: Multi-Category Items (Ambiguous)")
    print("=" * 60)
    
    if 'MysteryBox' in multi_items:
        print(f"\n[MysteryBox] - Could be:")
        for match in multi_items['MysteryBox']:
            print(f"  - {match['category']} ({match['confidence']:.2%})")
            print(f"    Tags: {', '.join(match['tags'][:2])}...")
    print()


# Example 6: Signature debugging
def example_signature_debug():
    """See how item matches all 8 signatures."""
    from ItemGenerator.src.tag.matcher import compare_signatures
    
    katana_props = """
        item Katana {
            Type = Weapon,
            MinDamage = 10.0,
            MaxDamage = 15.0,
            ConditionMax = 50,
        }
    """
    
    debug = compare_signatures('Katana', katana_props)
    
    print("=" * 60)
    print("EXAMPLE 6: Signature Comparison (Debug All 8)")
    print("=" * 60)
    print(f"Item: {debug['item_id']}")
    print(f"Best Match: {debug['best_match']} ({debug['best_confidence']:.2%})\n")
    
    print("All Signatures (ranked by confidence):")
    for i, sig in enumerate(debug['all_signatures'], 1):
        status = "✓" if sig['matched'] else "✗"
        print(f"  {i}. {sig['category']:15} {status} {sig['confidence']:.2%}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("AUTO-TAGGING SYSTEM - USAGE EXAMPLES")
    print("=" * 60 + "\n")
    
    example_single_item()
    example_batch_tagging()
    example_confidence_scoring()
    example_below_threshold()
    example_multi_category()
    example_signature_debug()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
