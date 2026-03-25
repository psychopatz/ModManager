import subprocess
from pathlib import Path
import logging
import urllib.request
import json
import urllib.parse
import shutil

logger = logging.getLogger(__name__)

# Constants
APP_ID = "108600"
WORKSHOP_ID = "3635333613"

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
            f'\t"publishedfileid" "{WORKSHOP_ID}"',
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
        "id": WORKSHOP_ID
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
