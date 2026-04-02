import subprocess
from pathlib import Path
import logging
import urllib.request
import json
import urllib.parse
import shutil
import re

logger = logging.getLogger(__name__)

# Constants
APP_ID = "108600"
SEMVER_PATTERN = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def resolve_workshop_id(mod_root: Path) -> str:
    workshop_txt = mod_root / "workshop.txt"
    if workshop_txt.exists():
        try:
            with open(workshop_txt, "r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if line.startswith("id="):
                        return line.split("=", 1)[1].strip()
        except Exception as exc:
            logger.debug(f"Unable to read workshop.txt at {workshop_txt}: {exc}")

    vdf_path = mod_root / "workshop_update.vdf"
    if vdf_path.exists():
        try:
            content = vdf_path.read_text(encoding="utf-8")
            match = re.search(r'"publishedfileid"\s+"([^"]+)"', content)
            if match:
                return match.group(1).strip()
        except Exception as exc:
            logger.debug(f"Unable to read workshop_update.vdf at {vdf_path}: {exc}")

    return ""

def prepare_staging(mod_root: Path, staging_dir: Path):
    """
    Prepares a clean staging directory with only the necessary mod files.
    """
    try:
        if staging_dir.exists():
            logger.info(f"Cleaning existing staging directory: {staging_dir}")
            shutil.rmtree(staging_dir)
        
        staging_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the contents OF the Contents/ directory into the staging root
        contents_src = mod_root / "Contents"
        if contents_src.exists():
            print(f"Staging files from {contents_src}...") # Visible in TaskConsole
            logger.info(f"Flattening Contents from {contents_src} to staging root")
            for item in contents_src.iterdir():
                s = item
                d = staging_dir / item.name
                if s.is_dir():
                    print(f"  [DIR] {item.name}/")
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    print(f"  [FILE] {item.name}")
                    shutil.copy2(s, d)
        else:
            logger.warning(f"Contents directory not found at {contents_src}")
            print(f"[WARNING] Contents directory not found at {contents_src}")
            
        # Copy workshop.txt
        workshop_txt = mod_root / "workshop.txt"
        if workshop_txt.exists():
            logger.info(f"Copying workshop.txt")
            shutil.copyfile(workshop_txt, staging_dir / "workshop.txt")
            
        # Copy preview.png
        preview_png = mod_root / "preview.png"
        if preview_png.exists():
            logger.info(f"Copying preview.png")
            shutil.copyfile(preview_png, staging_dir / "preview.png")
            
        logger.info("Staging preparation complete.")
        return True
    except Exception as e:
        logger.error(f"Error preparing staging: {e}")
        print(f"Error preparing staging: {e}")
        return False

def generate_vdf(
    staging_dir: Path, 
    vdf_path: Path, 
    workshop_id: str,
    changenote: str = "Update pushed via SteamCMD",
    title: str = None,
    description: str = None,
    previewfile: str = None,
    visibility: int = None,
    tags: str = None
):
    """
    Generates the VDF script for SteamCMD with full metadata support.
    """
    try:
        lines = [
            '"workshopitem"',
            '{',
            f'\t"appid" "{APP_ID}"',
            f'\t"publishedfileid" "{workshop_id}"',
            f'\t"contentfolder" "{staging_dir.absolute()}"',
            f'\t"changenote" "{changenote}"'
        ]
        
        if title:
            lines.append(f'\t"title" "{title}"')
        if description:
            # Escape double quotes for VDF
            escaped_desc = description.replace('"', '\\"')
            lines.append(f'\t"description" "{escaped_desc}"')
        if previewfile:
            lines.append(f'\t"previewfile" "{previewfile}"')
        if visibility is not None:
            lines.append(f'\t"visibility" "{visibility}"')
        if tags:
            lines.append(f'\t"tags" "{tags}"')
            
        lines.append('}')
        
        vdf_content = "\n".join(lines)
        with open(vdf_path, "w") as f:
            f.write(vdf_content)
        logger.info(f"VDF script generated at {vdf_path}")
        return True
    except Exception as e:
        logger.error(f"Error generating VDF: {e}")
        print(f"Error generating VDF: {e}")
        return False

def parse_workshop_txt(workshop_txt_path: Path):
    """
    Parses the Project Zomboid workshop.txt file to extract current metadata.
    """
    metadata = {
        "title": "",
        "description": [],
        "tags": "",
        "visibility": 0,
        "id": resolve_workshop_id(workshop_txt_path.parent)
    }
    
    if not workshop_txt_path.exists():
        return metadata
        
    try:
        with open(workshop_txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                if line.startswith("title="):
                    metadata["title"] = line.split("=", 1)[1]
                elif line.startswith("description="):
                    desc_line = line.split("=", 1)[1]
                    metadata["description"].append(desc_line)
                elif line.startswith("tags="):
                    metadata["tags"] = line.split("=", 1)[1]
                elif line.startswith("visibility="):
                    vis = line.split("=", 1)[1].lower()
                    if vis == "public": metadata["visibility"] = 0
                    elif vis == "friends": metadata["visibility"] = 1
                    elif vis == "private": metadata["visibility"] = 2
                    else: metadata["visibility"] = int(vis) if vis.isdigit() else 0
                    
        # Join description lines
        metadata["description"] = "\n".join(metadata["description"])
        return metadata
    except Exception as e:
        logger.error(f"Error parsing workshop.txt: {e}")
        return metadata


def _read_mod_info_fields(mod_info_path: Path) -> dict:
    fields = {
        "name": "",
        "id": "",
        "version": "",
    }
    try:
        with open(mod_info_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if key in fields:
                    fields[key] = value
    except Exception as exc:
        logger.error("Failed reading mod.info %s: %s", mod_info_path, exc)
    return fields


def list_mod_versions(mod_root: Path) -> list[dict]:
    mod_info_files = sorted((mod_root / "Contents/mods").glob("*/42.13/mod.info"))
    versions: list[dict] = []

    for mod_info_path in mod_info_files:
        fields = _read_mod_info_fields(mod_info_path)
        mod_folder = mod_info_path.parents[1].name
        versions.append(
            {
                "mod_folder": mod_folder,
                "mod_id": fields["id"] or mod_folder,
                "name": fields["name"] or mod_folder,
                "version": fields["version"] or "",
                "has_version": bool(fields["version"]),
                "path": str(mod_info_path),
            }
        )

    return versions


def _increment_version_string(current_version: str, bump: str = "patch") -> str:
    value = str(current_version or "").strip()
    match = SEMVER_PATTERN.match(value)
    if not match:
        base = [0, 0, 0]
    else:
        base = [
            int(match.group(1) or 0),
            int(match.group(2) or 0),
            int(match.group(3) or 0),
        ]

    bump = str(bump or "patch").strip().lower()
    if bump == "major":
        base[0] += 1
        base[1] = 0
        base[2] = 0
    elif bump == "minor":
        base[1] += 1
        base[2] = 0
    else:
        base[2] += 1

    return f"{base[0]}.{base[1]}.{base[2]}"


def increment_mod_version(mod_root: Path, mod_id: str, bump: str = "patch") -> dict:
    target_mod = str(mod_id or "").strip().lower()
    if not target_mod:
        raise ValueError("mod_id is required.")

    candidates = list_mod_versions(mod_root)
    selected = None
    for row in candidates:
        if row["mod_id"].lower() == target_mod or row["mod_folder"].lower() == target_mod:
            selected = row
            break

    if not selected:
        raise FileNotFoundError(f'Unable to find mod.info for module "{mod_id}".')

    mod_info_path = Path(selected["path"])
    lines = mod_info_path.read_text(encoding="utf-8").splitlines()

    old_version = selected.get("version") or ""
    new_version = _increment_version_string(old_version, bump)
    next_lines = []
    found_version = False

    for line in lines:
        if line.strip().lower().startswith("version="):
            next_lines.append(f"version={new_version}")
            found_version = True
        else:
            next_lines.append(line)

    if not found_version:
        insert_at = len(next_lines)
        for index, line in enumerate(next_lines):
            if line.strip().lower().startswith("versionmin="):
                insert_at = index
                break
        next_lines.insert(insert_at, f"version={new_version}")

    mod_info_path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")

    return {
        "mod_id": selected["mod_id"],
        "mod_folder": selected["mod_folder"],
        "name": selected["name"],
        "old_version": old_version,
        "new_version": new_version,
        "path": str(mod_info_path),
    }

def fetch_steam_metadata(item_id: str):
    """
    Fetches live metadata from the Steam Web API for the given workshop item.
    """
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    data = urllib.parse.urlencode({
        "itemcount": 1,
        "publishedfileids[0]": item_id
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            if "publishedfiledetails" in res_data.get("response", {}):
                details = res_data["response"]["publishedfiledetails"][0]
                if details.get("result") == 1: # Success
                    return {
                        "title": details.get("title", ""),
                        "description": details.get("description", ""),
                        "tags": ";".join([t["tag"] for t in details.get("tags", [])]),
                        "visibility": details.get("visibility", 0),
                        "id": item_id,
                        "preview_url": details.get("preview_url", ""),
                        "views": details.get("views", 0),
                        "subscriptions": details.get("subscriptions", 0)
                    }
        return None
    except Exception as e:
        logger.error(f"Error fetching Steam metadata: {e}")
        return None

def run_steamcmd_upload(steamcmd_path: str, vdf_path: Path, username: str, password: str = None):
    """
    Executes SteamCMD to upload the workshop item.
    Note: This is intended to be run within the TaskManager to capture output.
    """
    try:
        # Pre-step: Kill any running Steam client to avoid conflicts
        try:
            print("Checking for running Steam processes...")
            subprocess.run(["pkill", "steam"], check=False)
            logger.info("Attempted to terminate Steam client.")
        except Exception as e:
            logger.debug(f"Pkill steam failed (maybe already closed): {e}")

        cmd = [steamcmd_path]
        if password:
            # Note: Passing password via CLI is generally insecure but requested here for basic GUI integration.
            cmd.extend(["+login", username, password])
        else:
            cmd.extend(["+login", username])
            
        cmd.extend(["+workshop_build_item", str(vdf_path.absolute()), "+quit"])
        
        logger.info(f"Executing SteamCMD: {' '.join([arg if arg != password else '********' for arg in cmd])}")
        
        # Use subprocess.Popen to stream output to stdout (captured by TaskManager)
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        for line in process.stdout:
            print(line, end="") # Captured by TaskManager
            
        process.wait()
        
        if process.returncode == 0:
            logger.info("SteamCMD upload successful.")
            print("\n[SUCCESS] SteamCMD upload completed successfully.")
            return True
        else:
            logger.error(f"SteamCMD failed with return code {process.returncode}")
            print(f"\n[ERROR] SteamCMD failed with return code {process.returncode}")
            return False
            
    except Exception as e:
        logger.error(f"Error running SteamCMD: {e}")
        print(f"\n[ERROR] Internal error running SteamCMD: {e}")
        return False

def run_full_workshop_push(
    mod_root: Path, 
    staging_dir: Path, 
    vdf_path: Path, 
    steamcmd_path: str,
    username: str, 
    password: str,
    request_data: dict
):
    """
    Unified task to prepare files, generate VDF, and upload to Steam.
    Provides full visibility in the TaskConsole.
    """
    print("=== STARTING WORKSHOP PUSH WORKFLOW ===")
    workshop_id = request_data.get("workshop_id") or resolve_workshop_id(mod_root)
    if not workshop_id:
        print("[ERROR] No workshop ID was found for this project.")
        return False
    
    # 1. Prepare Staging
    if request_data.get("update_files"):
        print("\n[STEP 1/3] Preparing staging directory...")
        if not prepare_staging(mod_root, staging_dir):
            print("[ERROR] Staging preparation failed.")
            return False
    else:
        print("\n[STEP 1/3] Skipping file update as requested.")

    # 2. Generate VDF
    print("\n[STEP 2/3] Generating VDF script...")
    success = generate_vdf(
        staging_dir=staging_dir, 
        vdf_path=vdf_path, 
        workshop_id=workshop_id,
        changenote=request_data.get("changenote", ""),
        title=request_data.get("title") if request_data.get("update_metadata") else None,
        description=request_data.get("description") if request_data.get("update_metadata") else None,
        previewfile=str((mod_root / "preview.png").absolute()) if request_data.get("update_preview") else None,
        visibility=request_data.get("visibility") if request_data.get("update_metadata") else None,
        tags=request_data.get("tags") if request_data.get("update_metadata") else None
    )
    if not success:
        print("[ERROR] VDF generation failed.")
        return False

    # 3. Upload
    print("\n[STEP 3/3] Running SteamCMD upload...")
    return run_steamcmd_upload(steamcmd_path, vdf_path, username, password)
