from typing import Optional

from fastapi import APIRouter

from api.routers.common import get_workshop_project_or_404
from GitManagement.diff_handler import get_git_branches, get_git_changes

router = APIRouter(tags=["git"])


@router.get("/api/git/changes")
async def get_project_changes(branch: Optional[str] = None, target: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    return get_git_changes(branch, project["path"])


@router.get("/api/git/branches")
async def get_project_branches(target: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    return get_git_branches(project["path"])
