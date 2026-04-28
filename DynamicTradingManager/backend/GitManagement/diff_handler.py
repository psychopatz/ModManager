import subprocess
import logging
from pathlib import Path
import os
from config.server_settings import get_server_settings

logger = logging.getLogger(__name__)

def get_git_changes(branch: str = "develop", repo_path: Path = None, limit: int = 150, since: str = None):
    """
    Returns a summary of uncommitted changes and detailed recent history.
    """
    repo_path = repo_path or get_server_settings().dynamic_trading_path
    try:
        # Get status
        status = subprocess.check_output(["git", "status", "--short"], cwd=repo_path, encoding="utf-8")
        
        # Get diff summary
        diff_stat = subprocess.check_output(["git", "diff", "--stat"], cwd=repo_path, encoding="utf-8")
        
        try:
            diff_detail = subprocess.check_output(["git", "diff", "HEAD", "--", ":!DynamicTradingManager"], cwd=repo_path, encoding="utf-8")
        except:
            diff_detail = ""

        # Get detailed commit history (with bodies)
        # Format: HASH|DATE|SUBJECT|BODY (with markers)
        target = branch if branch else "HEAD"
        commit_list = []
        try:
            log_cmd = [
                "git", "log", target, "-n", str(limit),
                "--format=COMMIT_START%h|%as|%s|%b|COMMIT_END"
            ]
            if since:
                log_cmd.insert(2, f"--since={since}")
            
            log_output = subprocess.check_output(log_cmd, cwd=repo_path, encoding="utf-8")
            
            parts = log_output.split("COMMIT_START")
            for part in parts:
                if "COMMIT_END" not in part: continue
                content = part.split("COMMIT_END")[0].strip()
                if not content: continue
                
                fields = content.split("|", 3)
                if len(fields) < 3: continue
                
                h = fields[0]
                date = fields[1]
                msg = fields[2]
                body = fields[3].strip() if len(fields) > 3 else ""
                
                # Robust type parsing
                msg_lower = msg.lower()
                ctype = "other"
                if msg_lower.startswith("feat"): ctype = "feat"
                elif msg_lower.startswith("fix"): ctype = "fix"
                elif msg_lower.startswith("refactor"): ctype = "refactor"
                elif msg_lower.startswith("chore"): ctype = "chore"
                elif msg_lower.startswith("docs"): ctype = "docs"
                
                commit_list.append({
                    "hash": h,
                    "date": date,
                    "message": msg,
                    "body": body,
                    "type": ctype,
                    "raw": f"{h} {msg}"
                })
        except Exception as e:
            logger.error(f"Error fetching detailed log: {e}")
        
        return {
            "status": status,
            "summary": diff_stat,
            "detail": diff_detail[:5000],
            "commits": commit_list
        }
    except Exception as e:
        logger.error(f"Error getting git changes: {e}")
        return {"error": str(e)}

def get_git_branches(repo_path: Path = None):
    """
    Returns a list of local and remote branches.
    """
    repo_path = repo_path or get_server_settings().dynamic_trading_path
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

def get_batched_git_log(since_date: str, branch: str = "develop"):
    """
    Fetches and groups commits by date across all mod repositories.
    """
    from config.server_settings import get_server_settings
    settings = get_server_settings()
    
    # We should detect all repos, but for now we follow the confirmed list
    repos = {
        "DynamicTrading": settings.dynamic_trading_path,
        "DynamicColonies": settings.dynamic_colonies_path,
        "CurrencyExpanded": settings.dynamic_currency_path,
        "DynamicObjectives": settings.dynamic_trading_path.parent / "DynamicObjectives" 
    }
    
    batched = {} # date -> repo -> [commits]
    
    for repo_name, path in repos.items():
        if not path or not Path(path).exists():
            continue
            
        try:
            # Format: DATE|SUBJECT|BODY (with markers to avoid parsing issues)
            # We use %as for author date (YYYY-MM-DD), %s subject, %b body
            log_cmd = [
                "git", "log", branch, 
                f"--since={since_date} 00:00:00", 
                "--format=COMMIT_START%as|%s|%b|COMMIT_END"
            ]
            
            output = subprocess.check_output(log_cmd, cwd=path, encoding="utf-8")
            parts = output.split("COMMIT_START")
            
            for part in parts:
                if "COMMIT_END" not in part:
                    continue
                content = part.split("COMMIT_END")[0].strip()
                if not content:
                    continue
                
                fields = content.split("|", 2)
                if len(fields) < 2:
                    continue
                    
                date = fields[0]
                subject = fields[1]
                body = fields[2] if len(fields) > 2 else ""
                
                if date not in batched:
                    batched[date] = {}
                if repo_name not in batched[date]:
                    batched[date][repo_name] = []
                    
                batched[date][repo_name].append({
                    "subject": subject,
                    "body": body.strip()
                })
        except Exception as e:
            logger.warning(f"Error reading git log for {repo_name} on {branch}: {e}")
            continue
            
    return batched
