from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
import models
from auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("")
def get_dashboard(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    memberships = db.query(models.ProjectMember).filter(models.ProjectMember.user_id == current_user.id).all()
    project_ids = [m.project_id for m in memberships]
    is_admin = any(m.role == models.RoleEnum.admin for m in memberships)

    all_tasks = db.query(models.Task).filter(models.Task.project_id.in_(project_ids)).all()
    if not is_admin:
        all_tasks = [t for t in all_tasks if t.assigned_to == current_user.id]

    now = datetime.utcnow()
    return {
        "total_tasks": len(all_tasks),
        "by_status": {
            "todo": sum(1 for t in all_tasks if t.status == models.StatusEnum.todo),
            "in_progress": sum(1 for t in all_tasks if t.status == models.StatusEnum.in_progress),
            "done": sum(1 for t in all_tasks if t.status == models.StatusEnum.done),
        },
        "overdue": sum(1 for t in all_tasks if t.due_date and t.due_date < now and t.status != models.StatusEnum.done),
        "total_projects": len(project_ids),
        "tasks_per_user": _tasks_per_user(all_tasks, db),
    }

def _tasks_per_user(tasks, db):
    user_map = {}
    for t in tasks:
        if t.assigned_to:
            user = db.query(models.User).filter(models.User.id == t.assigned_to).first()
            name = user.name if user else "Unknown"
            user_map[name] = user_map.get(name, 0) + 1
    return user_map