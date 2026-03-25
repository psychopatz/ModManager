# Item Verification & Pricing System

Modular architecture for item verification, analysis, confidence scoring, and pricing calculations.

## Directory Structure

```
src/
├── verify/                          # Verification and analysis modules
│   ├── __init__.py                 # Package init + module exports
│   ├── helpers.py                  # Common utility functions
│   ├── vanilla_loader.py           # Load vanilla item data
│   ├── mod_loader.py               # Load mod data and detect duplicates
│   ├── tag_validator.py            # Dynamic tag library management
│   ├── item_analyzer.py            # Worth calculation & stat extraction
│   ├── confidence.py               # Confidence scoring system
│   └── reporters.py                # Report generation & output
│
└── pricing/                         # Pricing configuration & calculation
    ├── __init__.py                 # Package init + loader function
    ├── config.json                 # Default pricing configuration
    ├── calculator.py               # Price calculation engine
    └── stock_manager.py            # Stock level management
```

## Verify Module

### Core Components

#### 1. **helpers.py**
Common utility functions used across all modules:
- `sanitize_path()` - Clean folder names
- `get_stat()` - Extract numeric properties
- `has_property()` - Check property existence
- `parse_categories()` - Extract category data
- `count_recipes()` - Count learned recipes

#### 2. **vanilla_loader.py** 
Loads and parses vanilla Project Zomboid item data:
- `get_vanilla_data()` - Scan scripts directory for items/fluids
- `get_opening_maps()` - Map unopened -> opened item variants
- `get_item_metadata()` - Extract computed fields for an item

*Returns:* Dictionaries of items and fluids with full properties

#### 3. **mod_loader.py**
Analyzes mod item registrations:
- `get_mod_data()` - Scan mod Lua files for item registrations
- `get_mod_duplicates()` - Detect duplicate registrations
- `find_item_in_mod()` - Query single item status

*Returns:* Mod item data and duplicate tracking

#### 4. **tag_validator.py**
Manages dynamic tag library:
- `get_dynamic_tags()` - Load tags from Tags_Reference.md
- `validate_tag()` - Check if tag is valid
- `get_tags_by_root()` - Filter tags by root category
- `parse_tags_from_lua()` - Parse Lua tag strings

#### 5. **item_analyzer.py**
Calculates item properties and prices:
- `calculate_worth()` - Property-based worth multiplier
- `calculate_stock_level()` - Determine min/max stock
- `analyze_item_stats()` - Comprehensive stat extraction
- `generate_lua_snippet()` - Create Lua registration code

#### 6. **confidence.py** ⭐ (NEW)
Confidence scoring for item analysis:
- `ConfidenceScorer` - Class for scoring system
- `score_item_confidence()` - Score single item
- `find_below_threshold()` - Find low-confidence items
- `generate_confidence_report()` - Create readable report

**Features:**
- Multi-component scoring (category, tags, properties, clarity)
- Configurable thresholds
- Detailed breakdown with recommendations
- Text-level confidence (VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW)

#### 7. **reporters.py**
Output generation:
- `write_hierarchical_files()` - Hierarchical folder output
- `write_mod_duplicates()` - Duplicate reports
- `write_confidence_report()` - Confidence findings
- `write_chunk_output()` - Formatted chunk export (lua/debug/csv)

## Pricing Module

### Components

#### 1. **__init__.py**
Main entry point:
- `load_pricing_config()` - Load config from file or defaults
- Returns configuration dictionary

#### 2. **config.json**
Configuration file with:
- `price_multipliers` - Category, rarity, quality, weight factors
- `min_price` / `max_price` - Price bounds
- `stock_levels` - Weight tiers and category multipliers
- `thresholds` - High/low value thresholds

#### 3. **calculator.py**
Price calculation engine:
- `PriceCalculator` - Main class
  - `calculate()` - Calculate final price
  - `batch_calculate()` - Calculate multiple items
  - `get_price_range()` - Get category ranges
  - `adjust_for_condition()` - Condition-based adjustment

#### 4. **stock_manager.py**
Stock level management:
- `StockManager` - Main class
  - `calculate_stock()` - Calculate min/max levels
  - `batch_calculate()` - Calculate multiple items
  - `get_stock_analysis()` - Analyze distribution

## Usage Examples

### Load and Analyze Vanilla Items

```python
from Utils.verify import get_vanilla_data, calculate_worth

items, fluids = get_vanilla_data("/path/to/vanilla/scripts")

for item_id, data in items.items():
    props = data['props']
    category = data['category']
    worth = calculate_worth(item_id, props, category, 'General')
    print(f"{item_id}: {worth}")
```

### Confidence Scoring

```python
from Utils.verify import find_below_threshold, generate_confidence_report

# Find items below 65% confidence
below_threshold = find_below_threshold(items_data, threshold=0.65)

# Generate report
report = generate_confidence_report(below_threshold)
print(report)

# Write to file
from Utils.verify import write_confidence_report
write_confidence_report("./output", report)
```

### Price Calculation

```python
from Utils.pricing import load_pricing_config, PriceCalculator

config = load_pricing_config()
calc = PriceCalculator(config)

item_data = {
    'category': 'Weapon',
    'rarity': 'Rare',
    'quality': 'Sterile',
    'weight': 2.5
}

price = calc.calculate(base_worth=15.0, item_data=item_data)
```

### Stock Management

```python
from Utils.pricing import StockManager

stock_mgr = StockManager(config)
stock = stock_mgr.calculate_stock(weight=0.3, category='Food', props=props)
# Returns: {'min': 5, 'max': 20}
```

## Command-Line Usage

### Run ItemID_Verify with confidence checking

```bash
python ItemID_Verify.py --confidence --threshold 0.65
```

This generates `confidence.txt` showing items below threshold for refinement.

### Get tag information

```bash
python ItemID_Verify.py --getTags Food
python ItemID_Verify.py --getTags all
```

### Generate chunk output

```bash
python ItemID_Verify.py --chunk 50 --status VanillaOnly
```

## Output Files

### confidence.txt
Shows items scoring below the confidence threshold with:
- Overall confidence score
- Component scores (category, tags, properties, clarity)
- Visual progress bars for each score
- Refinement recommendations

Example:
```
⚠ 15 ITEMS BELOW CONFIDENCE THRESHOLD
================================================================================

[ExampleItem]
  Overall Score: 0.58 (Threshold: 0.65)
  Confidence Level: LOW
  Category: Food
  Tags: Food.Cooking, Rarity.Common
  Score Breakdown:
    category_confidence      ████░░░░░░░░░░░░░░░░ 0.4
    tag_confidence           ███████░░░░░░░░░░░░░░ 0.5
    property_coverage        █████████░░░░░░░░░░░░ 0.6
    clarity_score            ████████░░░░░░░░░░░░░ 0.5
  Recommendations:
    - Review category detection - unclear item type
    - Assign more specific tags to clarify purpose
```

## Configuration

### Pricing Config (config.json)

Modify multipliers to adjust pricing:
```json
{
  "price_multipliers": {
    "rarity_multipliers": {
      "Common": 1.0,
      "Uncommon": 1.5,
      "Rare": 2.5,
      "Legendary": 4.0
    },
    "category_multipliers": {
      "Weapon": 2.5,
      "Medical": 1.8,
      "Food": 1.0
    }
  }
}
```

### Confidence Thresholds

Adjust in `confidence.py`:
```python
self.config = {
    'tag_confidence_min': 0.6,
    'category_confidence_min': 0.7,
    'property_coverage_min': 0.5,
    'default_threshold': 0.65  # Main threshold
}
```

## Integration Notes

- All modules are designed to be **property-agnostic** and use vanilla script data
- The system falls back gracefully when data is missing
- Confidence scores help identify items needing manual review
- Pricing is fully configurable for economy balancing
- Modular design allows adding new analyzers without touching existing code

## Future Extensions

Potential modules to add:
- `tag_assigner.py` - Automatic tag assignment engine
- `batch_processor.py` - Process multiple files in parallel
- `export.py` - Export to various formats (SQL, JSON, CSV)
- `validator.py` - Validate generated data
