"""
Report generation and file output system
"""
import os
from .helpers import sanitize_path


def write_hierarchical_files(output_dir, status_folder, ids_subset, vanilla_data, mod_data):
    """
    Write item data to hierarchical folder structure
    
    Args:
        output_dir: Base output directory
        status_folder: Status category (VanillaOnly, AlreadyHas, etc.)
        ids_subset: List of item IDs to process
        vanilla_data: Vanilla item data dictionary
        mod_data: Mod item data dictionary
    """
    if not ids_subset:
        return
    
    print(f"[*] Writing {status_folder} results...")
    
    for obj_id in ids_subset:
        meta = vanilla_data.get(obj_id)
        current_root = status_folder
        
        if not meta:
            meta = mod_data.get(obj_id, {"origin": "Unknown.txt"})
            category, subcat, worth, weight = "Invalid", "General", 0.0, 0.1
        else:
            category = meta.get("category", "Uncategorized")
            subcat = meta.get("subcat", "General")
            worth = meta.get("worth", 1.0)
            weight = meta.get("weight", 0.1)
            
            # Redirect unsure items
            if meta.get("tags") == "None" and status_folder in ["VanillaOnly", "AlreadyHas"]:
                current_root = "UnsureItems"
        
        origin = meta.get("origin", "Unknown.txt").replace(".lua", "").replace(".txt", "")
        
        # Create directory structure
        path_parts = current_root.split('/')
        target_dir = os.path.join(output_dir, *path_parts, sanitize_path(origin), category)
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = os.path.join(target_dir, f"{subcat}.txt")
        
        # Build extra stats string
        extra = []
        if meta.get("capacity", 0) > 0:
            extra.append(f"Cap: {meta.get('capacity'):<4} WR: {meta.get('weight_reduction'):<3}")
        if meta.get("total_uses", 1) > 1:
            extra.append(f"Uses: {meta.get('total_uses'):<3}")
        if meta.get("recipes", 0) > 0:
            extra.append(f"Recipes: {meta.get('recipes'):<2}")
        if meta.get("fire_fuel", 0) > 0:
            extra.append(f"Fuel: {meta.get('fire_fuel'):<4}")
        if meta.get("unhappy", 0) != 0:
            extra.append(f"Unhappy: {meta.get('unhappy'):<3}")
        
        # Food stats
        if meta.get("hunger", 0) != 0:
            extra.append(f"Hunger: {meta.get('hunger'):<3}")
        if meta.get("fresh", 0) > 0:
            extra.append(f"Fresh: {meta.get('fresh'):<3} Rotten: {meta.get('rotten'):<3}")
        
        # Clothing stats
        if meta.get("category") in ["Clothing", "ProtectiveGear"]:
            extra.append(f"Insulation: {meta.get('insulation'):<3} Wind: {meta.get('wind_res'):<3}")
            extra.append(f"Defense(Bite/Scratch/Bullet): {meta.get('bite_def'):.0f}/{meta.get('scratch_def'):.0f}/{meta.get('bullet_def'):.0f}")
            if meta.get("condition_max", 0) > 0:
                extra.append(f"Condition: {meta.get('condition_max'):<3}")
        
        extra_str = " | " + " | ".join(extra) if extra else ""
        
        # Write to file
        with open(file_path, "a") as f:
            f.write(f"{obj_id:<45} | Worth: {worth:<8} | Weight: {weight:<6}{extra_str} | Tags: {meta.get('tags','N/A')}\n")
            
            # Write Lua snippet if available
            if "lua" in meta:
                f.write(f"  LUA: {meta['lua']}\n")


def write_mod_duplicates(output_dir, mod_dupes):
    """
    Write mod duplicate registrations to organized files
    
    Args:
        output_dir: Base output directory
        mod_dupes: Dictionary of item_id -> list of origins
    """
    if not mod_dupes:
        return
    
    print(f"[*] Writing Mod Duplicates results...")
    
    target_dir = os.path.join(output_dir, "Duplicates")
    os.makedirs(target_dir, exist_ok=True)
    
    # Organize duplicates by source file
    file_reports = {}
    
    for obj_id, locations in mod_dupes.items():
        loc_str = "[" + ", ".join(f'"{loc}"' for loc in sorted(locations)) + "]"
        count = len(locations)
        line = f"{obj_id:<45} Count: {count:<2} Locations: {loc_str}\n"
        
        for loc in locations:
            report_name = loc.replace(".lua", ".txt")
            
            if report_name not in file_reports:
                file_reports[report_name] = []
            
            file_reports[report_name].append(line)
    
    # Write organized reports
    for report_name, lines in file_reports.items():
        report_path = os.path.join(target_dir, report_name)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, "w") as f:
            f.write(f"--- Duplicates found in or conflicting with {report_name.replace('.txt', '.lua')} ---\n")
            f.writelines(sorted(lines))


def write_confidence_report(output_dir, report_content, filename="confidence.txt"):
    """
    Write confidence report to file
    
    Args:
        output_dir: Output directory
        report_content: Report text content
        filename: Output filename
    """
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, filename)
    
    with open(report_path, "w") as f:
        f.write(report_content)
    
    print(f"[✓] Confidence report written to: {report_path}")


def write_summary_report(output_dir, summary_data, filename="summary.txt"):
    """
    Write verification summary report
    
    Args:
        output_dir: Output directory
        summary_data: Dictionary with summary statistics
        filename: Output filename
    """
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, filename)
    
    lines = [
        "\n" + "=" * 80,
        "VERIFICATION SUMMARY REPORT",
        "=" * 80 + "\n"
    ]
    
    for key, value in summary_data.items():
        if isinstance(value, dict):
            lines.append(f"\n{key}:")
            for subkey, subvalue in value.items():
                lines.append(f"  {subkey:<40} {subvalue}")
        else:
            lines.append(f"{key:<40} {value}")
    
    lines.append("\n" + "=" * 80)
    
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    
    print(f"[✓] Summary report written to: {report_path}")


def write_chunk_output(items_list, output_type="lua"):
    """
    Format chunk of items for console or file output
    
    Args:
        items_list: List of items to output
        output_type: Format type ('lua', 'debug', 'csv')
    
    Returns:
        str: Formatted output
    """
    if not items_list:
        return "No items to output.\n"
    
    lines = []
    
    if output_type == "lua":
        lines.append("-- Lua output:\n")
        for item_id, meta in items_list:
            if "lua" in meta:
                lines.append(meta["lua"])
            else:
                lines.append(f"-- [NO LUA] {item_id} (origin: {meta.get('origin', 'Unknown')})")
    
    elif output_type == "debug":
        lines.append("-- Debug output:\n")
        for item_id, meta in items_list:
            lines.append(f"[{item_id}] (Origin: {meta.get('origin', 'Unknown')})")
            
            # Extract key stats
            props = meta.get("props", "")
            stats = {
                "Category": meta.get("category"),
                "Subcat": meta.get("subcat"),
                "Tags": meta.get("tags"),
            }
            
            active_stats = [f"{k}: {v}" for k, v in stats.items() if v and v != "None"]
            lines.append(f"  {' | '.join(active_stats)}")
    
    elif output_type == "csv":
        lines.append("item_id,category,subcategory,tags,origin,worth\n")
        for item_id, meta in items_list:
            csv_line = (
                f'{item_id},{meta.get("category","Unknown")},'
                f'{meta.get("subcat","General")},'
                f'{meta.get("tags","None")},'
                f'{meta.get("origin","Unknown")},'
                f'{meta.get("worth",1.0)}'
            )
            lines.append(csv_line)
    
    return "\n".join(lines)
