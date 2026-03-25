import subprocess
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)

def get_git_changes(branch: str = None):
    """
    Returns a summary of uncommitted changes (git status and short diff) 
    and recent feature history from the specified branch.
    """
    repo_path = Path(os.getenv("DYNAMIC_TRADING_PATH", "/home/psychopatz/Zomboid/Workshop/DynamicTrading/"))
    try:
        # Get status
        status = subprocess.check_output(["git", "status", "--short"], cwd=repo_path).decode("utf-8")
        
        # Get diff summary (stat)
        diff_stat = subprocess.check_output(["git", "diff", "--stat"], cwd=repo_path).decode("utf-8")
        
        # Get actual diff of recently modified files (last 5)
        # We limit this to avoid hitting token limits later
        try:
            diff_detail = subprocess.check_output(["git", "diff", "HEAD", "--", ":!DynamicTradingManager"], cwd=repo_path).decode("utf-8")
        except:
            diff_detail = ""

        # Get recent commit history (last 150)
        target = branch if branch else "HEAD"
        commit_list = []
        log_output = ""
        try:
            # First try the target, if it fails, fallback to HEAD
            try:
                log_output = subprocess.check_output(["git", "log", target, "-n", "150", "--oneline"], cwd=repo_path).decode("utf-8")
            except:
                log_output = subprocess.check_output(["git", "log", "HEAD", "-n", "150", "--oneline"], cwd=repo_path).decode("utf-8")
            
            for line in log_output.split("\n"):
                if not line.strip(): continue
                parts = line.split(" ", 1)
                h = parts[0]
                msg = parts[1] if len(parts) > 1 else ""
                
                # Robust type parsing (feat, fix, refactor, etc.)
                msg_lower = msg.lower()
                ctype = "other"
                
                if msg_lower.startswith("feat"): ctype = "feat"
                elif msg_lower.startswith("fix"): ctype = "fix"
                elif msg_lower.startswith("refactor"): ctype = "refactor"
                elif msg_lower.startswith("chore"): ctype = "chore"
                elif msg_lower.startswith("docs"): ctype = "docs"
                # Check for bracket styles like [feat]
                elif "[" in msg_lower and "]" in msg_lower:
                    if "feat" in msg_lower.split("]")[0]: ctype = "feat"
                    elif "fix" in msg_lower.split("]")[0]: ctype = "fix"
                
                commit_list.append({
                    "hash": h,
                    "message": msg,
                    "type": ctype,
                    "raw": line
                })
        except Exception as e:
            logger.error(f"Error fetching log: {e}")
            commit_list = []
        except Exception as e:
            logger.error(f"Error fetching log: {e}")
            commit_list = []
        
        return {
            "status": status,
            "summary": diff_stat,
            "detail": diff_detail[:5000], # Limit size
            "history": log_output, # Keep raw for compatibility
            "commits": commit_list
        }
    except Exception as e:
        logger.error(f"Error getting git changes: {e}")
        return {"error": str(e)}

def get_git_branches():
    """
    Returns a list of local and remote branches.
    """
    repo_path = Path(os.getenv("DYNAMIC_TRADING_PATH", "/home/psychopatz/Zomboid/Workshop/DynamicTrading/"))
    try:
        raw_branches = subprocess.check_output(["git", "branch", "-a"], cwd=repo_path).decode("utf-8")
        branches = []
        for line in raw_branches.split("\n"):
            line = line.strip()
            if not line: continue
            # Remove leading * and 'remotes/origin/' for cleaner names
            name = line.replace("* ", "").replace("remotes/origin/", "").strip()
            if name not in branches and "->" not in name:
                branches.append(name)
        return branches
    except Exception as e:
        logger.error(f"Error getting branches: {e}")
        return []

def format_for_ai(changes: dict):
    """
    Formats git changes into a prompt-friendly string.
    """
    if "error" in changes:
        return f"Error fetching changes: {changes['error']}"
        
    prompt = "Project Changes Summary:\n\n"
    prompt += "Files Modified:\n" + changes["status"] + "\n"
    prompt += "Change Stats:\n" + changes["summary"] + "\n"
    prompt += "Code Diffs (Partial):\n" + changes["detail"]
    return prompt
