import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)

# The taxonomy is dynamically discovered from the exported Lua config
KNOWN_PAGES = ["Food", "Medical", "Weapon", "Tool", "Container", "Clothing", "Electronics", "Resource", "Building", "Misc", "Literature", "Rarity", "Quality", "Theme", "Origin"]

def sync_sandbox_options() -> Dict[str, Any]:
    """
    Forcefully regenerates sandbox-options.txt and Sandbox.json 
    using the latest exported MS_PricingConfig_Data.lua AND MS_TagPriceAdditions_Data.lua.
    """
    base_lua_path = "/home/psychopatz/Zomboid/Workshop/MarketSense/Contents/mods/MarketSense/common/media/lua/shared/DT/MarketSense/Pricing/MS_PricingConfig_Data.lua"
    tag_lua_path = "/home/psychopatz/Zomboid/Workshop/MarketSense/Contents/mods/MarketSense/common/media/lua/shared/DT/MarketSense/Pricing/MS_TagPriceAdditions_Data.lua"
    target_dir = "/home/psychopatz/Zomboid/Workshop/MarketSense/Contents/mods/MarketSense/42.16/media"
    
    # 0. Path Resolution
    if not os.path.exists(base_lua_path):
        possible_roots = ["/home/psychopatz/Zomboid/Workshop/MarketSense", "/home/psychopatz/Zomboid/Workshop/DynamicTrading"]
        for root in possible_roots:
            p1 = os.path.join(root, "Contents/mods/MarketSense/common/media/lua/shared/DT/MarketSense/Pricing/MS_PricingConfig_Data.lua")
            if os.path.exists(p1):
                base_lua_path = p1
                tag_lua_path = os.path.join(root, "Contents/mods/MarketSense/common/media/lua/shared/DT/MarketSense/Pricing/MS_TagPriceAdditions_Data.lua")
                target_dir = os.path.join(root, "Contents/mods/MarketSense/42.16/media")
                break

    if not os.path.exists(base_lua_path):
        raise FileNotFoundError(f"Base pricing config not found at: {base_lua_path}")

    # 1. Parse BASE config (Global multipliers, Categories)
    with open(base_lua_path, "r", encoding="utf-8") as f:
        base_content = f.read()

    defaults = {}
    taxonomy: Dict[str, Set[str]] = {}

    match = re.search(r'\["base_multiplier"\]\s*=\s*([\d\.\-]+)', base_content)
    if match: defaults['PriceMultiplier'] = match.group(1)
    
    match_base = re.search(r'\["base_price"\]\s*=\s*([\d\.\-]+)', base_content)
    if match_base: defaults['PriceGlobalValue'] = str(int(float(match_base.group(1))))

    match_stock = re.search(r'\["stock_multiplier"\]\s*=\s*([\d\.\-]+)', base_content)
    if not match_stock: # Check nested in global
        match_stock = re.search(r'\["global"\]\s*=\s*\{[^\}]*?\["stock_multiplier"\]\s*=\s*([\d\.\-]+)', base_content, re.DOTALL)
    if match_stock: defaults['StockMultiplier'] = match_stock.group(1)

    # Parse Categories from base config
    cat_block_match = re.search(r'\["categories"\]\s*=\s*\{(.*?)\}\s*,\s*\["item_overrides"\]', base_content, re.DOTALL)
    if cat_block_match:
        cat_block = cat_block_match.group(1)
        cats = re.findall(r'\["(\w+)"\]\s*=\s*\{', cat_block)
        for cat in cats:
            if cat not in taxonomy: taxonomy[cat] = set(["General"])
            cat_inner = re.search(rf'\["{cat}"\]\s*=\s*\{{.*?\["stock_multiplier"\]\s*=\s*([\d\.\-]+)', cat_block, re.DOTALL)
            if cat_inner:
                defaults[f'Stock{cat}Mult'] = cat_inner.group(1)

    # 2. Parse TAG additions (Actual Tag prices from Tag Pricing menu)
    if os.path.exists(tag_lua_path):
        with open(tag_lua_path, "r", encoding="utf-8") as f:
            tag_content = f.read()
        
        # Look for tagAdditions block
        match_tag_block = re.search(r'tagAdditions\s*=\s*\{(.*?)\}', tag_content, re.DOTALL)
        if match_tag_block:
            tag_block = match_tag_block.group(1)
            entries = re.findall(r'\["([\w\.]+)"\]\s*=\s*([\d\.\-]+)', tag_block)
            for key, val in entries:
                clean_key = key.replace(".", "")
                defaults[f'Price{clean_key}Value'] = str(int(float(val)))
                
                # Update taxonomy
                parts = key.split('.')
                root = parts[0]
                if root not in taxonomy: taxonomy[root] = set()
                if len(parts) > 1:
                    taxonomy[root].add(".".join(parts[1:]))
                else:
                    taxonomy[root].add("General")

    # 3. Build sandbox-options.txt
    sandbox_txt = "VERSION = 1,\n\n"
    sandbox_json = {}
    options_list = []

    def add_global_option(key, page, name, tooltip, type="double", min="0.0", max="100.0"):
        nonlocal sandbox_txt
        default = defaults.get(key, "1.0" if type == "double" else "0")
        sandbox_txt += f"option MarketSense.{key}\n{{\n    type = {type},\n    default = {default},\n    min = {min},\n    max = {max},\n    page = {page},\n    translation = MarketSense.{key},\n}}\n\n"
        
        tab_key = f"Sandbox_{page}"
        if tab_key not in sandbox_json:
            clean_page = page.replace('MarketSense', '') or "Global"
            sandbox_json[tab_key] = f"Market Sense: {clean_page}"
        sandbox_json[f"Sandbox_MarketSense.{key}"] = name
        sandbox_json[f"Sandbox_MarketSense.{key}_tooltip"] = tooltip

    add_global_option("PriceMultiplier", "MarketSenseGlobal", "Price Multiplier: Global", "Secondary multiplier applied AFTER additive values.")
    add_global_option("PriceGlobalValue", "MarketSenseGlobal", "Price Addition: Global", "Flat price addition applied to ALL items.", type="integer", min="-1000000", max="1000000")
    add_global_option("StockMultiplier", "MarketSenseGlobal", "Stock: Global", "Base stock multiplier applied to ALL items.")

    for category in sorted(taxonomy.keys()):
        sub_paths = taxonomy[category]
        page = "MarketSenseGlobal" if category in ["Quality", "Rarity", "Origin", "Theme"] else f"MarketSense{category}"
        if category not in KNOWN_PAGES and category not in ["Quality", "Rarity", "Origin", "Theme"]:
            page = "MarketSenseMisc"
        
        nodes = set()
        for path in sub_paths:
            if path == "General":
                nodes.add(category)
            else:
                parts = path.split('.')
                current = category
                nodes.add(current)
                for part in parts:
                    current = current + "." + part
                    nodes.add(current)
        
        for node in sorted(nodes):
            clean_node = node.replace(".", "")
            
            p_opt = f"Price{clean_node}Value"
            p_default = defaults.get(p_opt, "0")
            options_list.extend([
                f'option MarketSense.{p_opt}\n{{',
                '    type = integer,',
                f'    default = {p_default},',
                '    min = -1000000,',
                '    max = 1000000,',
                f'    page = {page},',
                f'    translation = MarketSense.{p_opt},',
                '}\n'
            ])
            
            tab_key = f"Sandbox_{page}"
            if tab_key not in sandbox_json:
                clean_page = page.replace('MarketSense', '') or "Global"
                sandbox_json[tab_key] = f"Market Sense: {clean_page}"
            sandbox_json[f"Sandbox_MarketSense.{p_opt}"] = f"Price: {node.replace('.', ' > ')}"
            sandbox_json[f"Sandbox_MarketSense.{p_opt}_tooltip"] = f"Flat price addition for {node} items."

            s_opt = f"Stock{clean_node}Mult"
            s_default = defaults.get(s_opt, "1.0")
            options_list.extend([
                f'option MarketSense.{s_opt}\n{{',
                '    type = double,',
                f'    default = {s_default},',
                '    min = 0.0,',
                '    max = 100.0,',
                f'    page = {page},',
                f'    translation = MarketSense.{s_opt},',
                '}\n'
            ])
            sandbox_json[f"Sandbox_MarketSense.{s_opt}"] = f"Stock: {node.replace('.', ' > ')}"
            sandbox_json[f"Sandbox_MarketSense.{s_opt}_tooltip"] = f"Stock multiplier for {node} items."

    sandbox_txt += "\n".join(options_list)
    os.makedirs(os.path.join(target_dir, "lua/shared/Translate/EN"), exist_ok=True)
    with open(os.path.join(target_dir, "sandbox-options.txt"), "w") as f: f.write(sandbox_txt)
    with open(os.path.join(target_dir, "lua/shared/Translate/EN/Sandbox.json"), "w") as f: f.write(json.dumps(sandbox_json, indent=4))

    return {"status": "success", "options_count": len(options_list) // 8, "taxonomy_categories": list(taxonomy.keys())}
