from typing import Optional
from pathlib import Path

from fastapi import APIRouter

from api.routers.common import get_workshop_project_or_404
from GitManagement.diff_handler import get_git_branches, get_git_changes

router = APIRouter(tags=["git"])


@router.get("/api/git/changes")
async def get_project_changes(branch: Optional[str] = None, target: Optional[str] = None, since: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    return get_git_changes(branch, project["path"], since=since)


@router.get("/api/git/branches")
async def get_project_branches(target: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    return get_git_branches(project["path"])


@router.get("/api/git/suite/log")
async def get_suite_git_log(branch: str = "develop", limit: int = 100):
    """
    Returns detailed history across all mod repositories.
    """
    from config.server_settings import get_server_settings
    settings = get_server_settings()
    
    repos = {
        "DynamicTrading": settings.dynamic_trading_path,
        "DynamicColonies": settings.dynamic_colonies_path,
        "CurrencyExpanded": settings.dynamic_currency_path,
        "DynamicObjectives": settings.dynamic_trading_path.parent / "DynamicObjectives" 
    }
    
    suite_history = {}
    for repo_name, path in repos.items():
        if not path or not Path(path).exists():
            continue
        changes = get_git_changes(branch, Path(path), limit)
        if "commits" in changes:
            suite_history[repo_name] = changes["commits"]
            
    return suite_history


@router.get("/api/git/suite/branches")
async def get_suite_branches():
    """
    Returns unique branches found across all mod repositories.
    """
    from config.server_settings import get_server_settings
    settings = get_server_settings()
    
    repos = [
        settings.dynamic_trading_path,
        settings.dynamic_colonies_path,
        settings.dynamic_currency_path,
        settings.dynamic_trading_path.parent / "DynamicObjectives"
    ]
    
    all_branches = set()
    for path in repos:
        if path and Path(path).exists():
            branches = get_git_branches(Path(path))
            all_branches.update(branches)
            
    return sorted(list(all_branches))
