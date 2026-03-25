import os
from ..commons.helpers import sanitize_path

def write_mod_duplicates(output_dir, mod_dupes):
    if not mod_dupes: return
    print(f"[*] Writing Mod Duplicates results...")
    target_dir = os.path.join(output_dir, "Duplicates")
    os.makedirs(target_dir, exist_ok=True)
    
    file_reports = {}
    for obj_id, locations in mod_dupes.items():
        loc_str = "[" + ", ".join(f'"{loc}"' for loc in sorted(locations)) + "]"
        count = len(locations)
        line = f"{obj_id:<45} Count: {count:<2} Location: {loc_str}\n"
        
        for loc in locations:
            report_name = loc.replace(".lua", ".txt")
            if report_name not in file_reports:
                file_reports[report_name] = []
            file_reports[report_name].append(line)
            
    for report_name, lines in file_reports.items():
        report_path = os.path.join(target_dir, report_name)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            f.write(f"--- Duplicates found in or conflicting with {report_name.replace('.txt', '.lua')} ---\n")
            f.writelines(sorted(lines))

def write_hierarchical_files(output_dir, status_folder, ids_subset, vanilla_data, mod_data, simple=False, items_per_file=50):
    if not ids_subset: return
    print(f"[*] Writing {status_folder} results (Simple: {simple})...")
    
    # Store lines to write later (for simple splitting)
    file_buffers = {} # path -> [lines]

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
            # Redirect to UnsureItems if no tags
            if meta.get("tags") == "None" and status_folder in ["VanillaOnly", "AlreadyHas"]:
                current_root = "UnsureItems"
            
        origin = meta.get("origin", "Unknown.txt").replace(".lua", "").replace(".txt", "")
        path_parts = current_root.split('/')
        
        # Build the line
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
        
        if meta.get("hunger", 0) != 0:
            extra.append(f"Hung: {meta.get('hunger'):<3}")
        if meta.get("fresh", 0) > 0:
            extra.append(f"Fresh: {meta.get('fresh'):<3} Rot: {meta.get('rotten'):<3}")
        
        if meta.get("category") in ["Clothing", "ProtectiveGear"]:
            extra.append(f"Ins: {meta.get('insulation'):<3} Wind: {meta.get('wind_res'):<3}")
            extra.append(f"Def(B/S/P): {meta.get('bite_def'):.0f}/{meta.get('scratch_def'):.0f}/{meta.get('bullet_def'):.0f}")
            if meta.get("condition_max", 0) > 0:
                extra.append(f"Cond: {meta.get('condition_max'):<3}")
            
        extra_str = " | " + " | ".join(extra) if extra else ""
        line = f"{obj_id:<45} | Potential Worth: {worth:<8} | Weight: {weight:<6}{extra_str} | Tags: {meta.get('tags','N/A')}\n"

        target_base_dir = os.path.join(output_dir, *path_parts, sanitize_path(origin), category)
        file_key = os.path.join(target_base_dir, f"{subcat}")
        
        if file_key not in file_buffers:
            file_buffers[file_key] = []
        file_buffers[file_key].append(line)

    # Write buffers to files
    for file_key, lines in file_buffers.items():
        os.makedirs(os.path.dirname(file_key), exist_ok=True)
        
        if simple:
            # Split into multiple files
            for i in range(0, len(lines), items_per_file):
                chunk = lines[i:i + items_per_file]
                suffix = f"_{i // items_per_file + 1}" if len(lines) > items_per_file else ""
                file_path = f"{file_key}{suffix}.txt"
                with open(file_path, "w") as f:
                    f.writelines(chunk)
        else:
            file_path = f"{file_key}.txt"
            with open(file_path, "a") as f:
                f.writelines(lines)
