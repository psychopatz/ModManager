# Auto-Tagging Subsystem

Property-based item categorization and tagging system. Uses 8 signature categories to automatically classify items and generate semantic tags.

## Quick Start

```python
from Utils.tag import auto_tag, AutoTagger

# Quick tagging
result = auto_tag('Katana', props_string)
print(result['primary_tag'])      # 'Weapon.Melee.Blade'
print(result['tags'])             # ['Weapon.Melee.Blade', 'Rarity.Common', ...]

# Batch tagging
tagger = AutoTagger()
results = tagger.tag_batch({
    'Katana': katana_props,
    'IceCream': ice_cream_props,
    'Backpack': backpack_props
})

print(tagger.get_stats())  # {processed: 3, matched: 3, matched_rate: 1.0}
```

## 8 Property-Based Signatures

### 1. **Weapons** (`signatures/weapons.py`)
**Match Criteria:**
- `MinDamage` + `MaxDamage` > 0.5 (hard requirement)
- Evidence: Type=Weapon, ID pattern, ConditionMax (durability), AmmoType (firearm)

**Output Tags:**
- `Weapon.Melee.Axe|Blade|Blunt|General`
- `Weapon.Firearm` / `Weapon.Explosive`
- `Weapon.HighDamage|MediumDamage|LowDamage`
- `Weapon.Durable|Fragile`

**Example:** Katana (MinDamage=10, MaxDamage=15, ConditionMax=50) → `Weapon.Melee.Blade`

### 2. **Clothing** (`signatures/clothing.py`)
**Match Criteria:**
- `BodyLocation` property OR Type=Clothing (hard requirement)
- Evidence: Defense stats, Coverage patterns, Environmental properties

**Output Tags:**
- `Clothing.Armor.Heavy|Medium|Light`
- `Clothing.Head|Hands|Feet|Torso|Legs|General`
- `Clothing.BiteResistant|ScratchResistant|...`
- `Clothing.Insulated|WindResistant`

**Example:** PoliceFace (BiteDefense=15) → `Clothing.Head`

### 3. **Food** (`signatures/food.py`)
**Match Criteria:**
- `HungerChange` != 0 OR `ThirstChange` != 0 (hard requirement)
- Evidence: Type=Food, ID pattern, Calories, Freshness

**Output Tags:**
- `Food.Meat|Fruit|Vegetable|Grain|Drink.Alcohol|Drink.Beverage`
- `Food.Perishable|NonPerishable`
- `Food.HighNutrition|MediumNutrition|LowNutrition`

**Example:** Apple (HungerChange=20, DaysFresh=15) → `Food.Fruit.Perishable`

### 4. **Tools** (`signatures/tools.py`)
**Match Criteria:**
- `UseDelta` > 0 OR `ConditionMax` >= 3.0 (hard requirement)
- Evidence: Type=Normal, ID pattern, Tool specialization

**Output Tags:**
- `Tool.Crafting|Farming|Utility|Light|General`
- `Tool.Durable|Fragile`
- `Tool.HighUse|MediumUse|LimitedUse`

**Example:** Hammer (UseDelta=0.1, ConditionMax=40) → `Tool.Crafting`

### 5. **Electronics** (`signatures/electronics.py`)
**Match Criteria:**
- ID matches electronics pattern (hard requirement)
- Evidence: Battery/Generator/Communication patterns

**Output Tags:**
- `Electronics.Battery|Generator|Communication|Light|Generic`
- `Electronics.PowerSource|PowerGenerator|Communicator`
- `Electronics.RequiresPower|Transmitter`

**Example:** RadioHandheld (ID pattern match) → `Electronics.Communication`

### 6. **Medical** (`signatures/medical.py`)
**Match Criteria:**
- Type=Medical OR ID matches medical pattern OR is Sterile (hard requirement)
- Evidence: Bandage/Pills/Surgical patterns, Sterile property

**Output Tags:**
- `Medical.Bandage|Medicine|Surgical|Topical|General`
- `Medical.Sterile|NonSterile`
- `Medical.Surgical|Consumable`

**Example:** SurgicalSteel (ID pattern + Sterile=true) → `Medical.Surgical`

### 7. **Containers** (`signatures/containers.py`)
**Match Criteria:**
- `Capacity` >= 5 (hard requirement)
- Evidence: ID pattern, WeightReduction, Size classification

**Output Tags:**
- `Container.Backpack|Pouch|Storage|General.Small|Medium|Large`
- `Container.HighCapacity|MediumCapacity|LowCapacity`
- `Container.WeightEfficient|WeightReduction`

**Example:** NormalBackpack (Capacity=40, WR=0.3) → `Container.Backpack.Medium`

### 8. **Resources** (`signatures/resources.py`)
**Match Criteria:**
- ID matches resource pattern OR `UseDelta` > 0 OR has crafting recipes
- Evidence: Fuel/Metal/Wood/Fabric patterns, Harvestable property

**Output Tags:**
- `Resource.Metal|Wood|Fabric|Fuel|General`
- `Resource.Fuel|Craftable|Harvestable`

**Example:** MetalSheet (ID + crafting) → `Resource.Metal`

## Architecture

```
src/tag/
├── helpers.py              - Property extraction utilities
├── matcher.py             - Signature matching coordinator
├── analyzer.py            - Main AutoTagger class
├── confidence.py          - Tag confidence scoring
├── __init__.py           - Public API exports
└── signatures/            - Property-based signatures
    ├── weapons.py
    ├── clothing.py
    ├── food.py
    ├── tools.py
    ├── electronics.py
    ├── medical.py
    ├── containers.py
    └── resources.py
```

## Core Concepts

### PropertyAnalyzer
Utility class for comprehensive property analysis:

```python
from Utils.tag.helpers import PropertyAnalyzer

analyzer = PropertyAnalyzer(props_string)
damage = analyzer.get_stat('MaxDamage')
has_armor = analyzer.has_property('BiteDefense')
```

### Matching Process
1. Extract properties from item Lua definitions
2. Test against 8 signatures (order: Weapon → Food → Clothing → Container → Medical → Tool → Electronics → Resource)
3. Return best match with confidence score
4. Fallback to `Misc.General` if no category > 0.0 confidence

### Confidence Scoring
Multi-component scoring:
- **Category Confidence** (35%): How certain about primary category match
- **Tag Specificity** (35%): How detailed/hierarchical the tags are
- **Property Coverage** (20%): How many relevant properties are used
- **Clarity Score** (10%): How unambiguous the categorization is

**Overall Score Interpretation:**
- ≥ 0.85: VERY_HIGH (confident, production-ready)
- 0.70-0.85: HIGH (good match, minor review recommended)
- 0.50-0.70: MEDIUM (acceptable, review suggested)
- 0.30-0.50: LOW (uncertain, manual review recommended)
- < 0.30: VERY_LOW (poor match, likely needs correction)

Default threshold: 0.65

## API Reference

### auto_tag(item_id, props, threshold=0.4)
Quick auto-tagging for a single item.

```python
result = auto_tag('Katana', props_string)
# Returns: {
#   'item_id': 'Katana',
#   'category': 'Weapon',
#   'primary_tag': 'Weapon.Melee.Blade',
#   'confidence': 0.85,
#   'tags': ['Weapon.Melee.Blade', 'Rarity.Common', ...],
#   'rarity': 'Common',
#   'quality': None,
#   'origin': None,
#   'themes': [],
#   'details': {...}
# }
```

### AutoTagger
Main class for batch tagging with statistics.

```python
tagger = AutoTagger(default_confidence_threshold=0.4)

# Tag single item
result = tagger.tag_item('Katana', props)

# Tag multiple items
results = tagger.tag_batch({'Katana': props1, 'Apple': props2})

# Find multi-category items (ambiguous)
multi_items = tagger.find_multi_category_items(items_dict, min_confidence=0.3)

# Get statistics
stats = tagger.get_stats()
# Returns: {processed: N, matched: M, unmatched: K, multi_match: J, match_rate: 0.X}
```

### TagConfidenceScorer
Score quality of auto-generated tags.

```python
scorer = TagConfidenceScorer()

# Score individual tags
score = scorer.score_tags(item_id, props, tag_result)
# Returns: {
#   'overall_score': 0.75,
#   'confidence_level': 'HIGH',
#   'category_confidence': 0.85,
#   'tag_specificity': 0.72,
#   'property_coverage': 0.60,
#   'clarity_score': 0.80,
#   'below_threshold': False,
#   'recommendations': [...]
# }

# Score batch
scores = scorer.score_batch(items_dict, tag_results)

# Find below-threshold items
below = scorer.find_below_threshold(scores, threshold=0.65)
# Returns: [{item_id, overall_score, confidence_level, recommendations}, ...]
```

### Signature Matching
```python
from Utils.tag.matcher import match_item, get_multi_category_matches, compare_signatures

# Get best match
result = match_item('Katana', props)
# Returns: {category, confidence, details, tags, matched}

# Get all matches above threshold
matches = get_multi_category_matches('Item', props, min_confidence=0.3)
# Returns: [{category, confidence, tags}, ...]

# Debug: compare all signatures
comparison = compare_signatures('Item', props)
# Shows detailed analysis of all 8 signatures
```

## Usage Examples

### Example 1: Tag Vanilla Items
```python
from Utils.verify import get_vanilla_data
from Utils.tag import AutoTagger

items, fluids = get_vanilla_data(VANILLA_PATH)

tagger = AutoTagger()
results = tagger.tag_batch(items)
stats = tagger.get_stats()

print(f"Matched: {stats['matched']}/{stats['processed']}")
for item_id, result in results.items():
    if result['category'] == 'Unknown':
        print(f"{item_id}: NO MATCH - Check properties")
```

### Example 2: Find Low-Confidence Items
```python
from Utils.tag import AutoTagger, TagConfidenceScorer

tagger = AutoTagger()
results = tagger.tag_batch(items_dict)

scorer = TagConfidenceScorer()
scores = scorer.score_batch(items_dict, results)

below_threshold = scorer.find_below_threshold(scores, threshold=0.65)

for item in below_threshold:
    print(f"{item['item_id']}: {item['confidence_level']}")
    for rec in item['recommendations']:
        print(f"  - {rec}")
```

### Example 3: Find Multi-Category Items
```python
tagger = AutoTagger()
results = tagger.tag_batch(items_dict)

# Items that could fit multiple categories
multi_items = tagger.find_multi_category_items(items_dict, min_confidence=0.4)

for item_id, matches in multi_items.items():
    print(f"{item_id}: Could be")
    for match in matches:
        print(f"  - {match['category']} ({match['confidence']:.2%})")
```

### Example 4: Debug Categories
```python
from Utils.tag.matcher import compare_signatures

# See how item matches all 8 signatures
debug = compare_signatures('Katana', props)

print(f"Best Match: {debug['best_match']} ({debug['best_confidence']:.2%})")
print("\nAll Signatures:")
for sig in debug['all_signatures']:
    print(f"  {sig['category']}: {sig['confidence']:.2%} {'✓' if sig['matched'] else '✗'}")
```

## Integration with Existing System

### Connecting to ItemID_Verify.py
```python
from Scripts.ItemGenerator.Utils.tag import auto_tag
from Scripts.ItemGenerator.Utils.verify import get_vanilla_data

# Get vanilla items
items, fluids = get_vanilla_data(VANILLA_PATH)

# Tag them
for item_id, props in items.items():
    tag_result = auto_tag(item_id, props)
    items[item_id]['dt_tags'] = tag_result['tags']
```

### Connecting to tagging.py
```python
# tagging.py can use signature matching for validation
from Utils.tag import compare_signatures

# Validate existing tags against signatures
debug = compare_signatures(item_id, props)

# Log if signature vs tag mismatch
if debug['best_match'] != current_category:
    print(f"Warning: {item_id} signature match {debug['best_match']} != tagged {current_category}")
```

## Configuration

Adjust confidence weights in TagConfidenceScorer:

```python
config = {
    'category_weight': 0.35,      # How much category match matters
    'tag_weight': 0.35,            # How much tag detail matters
    'property_weight': 0.20,       # How much property coverage matters
    'clarity_weight': 0.10,        # How much clarity matters
    'default_threshold': 0.65      # Below this = manual review
}

scorer = TagConfidenceScorer(config)
```

## Performance

- Single item: ~5-10ms
- Batch 1000 items: ~2-5 seconds
- Batch 3000 items: ~5-10 seconds

Bottleneck: Regex property extraction in PropertyAnalyzer

## Troubleshooting

### Items Not Matching Any Signature
- Check if properties are present in props string
- Verify property names are correct (case matters for Type=, DisplayCategory=)
- Use `compare_signatures()` to debug

### Low Confidence Scores
- Add missing properties to item definition
- Check ID naming convention (should be descriptive)
- Review property values (e.g., MinDamage=0 won't match weapon)

### Multi-Category Items
Use `tagger.find_multi_category_items()` to identify ambiguous items
Consider adding discriminating properties

## Future Enhancements

- [ ] Machine learning confidence adjustment based on manual corrections
- [ ] Custom signature definitions per mod
- [ ] Hierarchical tag refinement
- [ ] Integration with Items taxonomy
- [ ] Automatic property inference from tags
