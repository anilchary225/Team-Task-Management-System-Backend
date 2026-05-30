from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
import models, schemas
from auth import get_current_user

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])

def get_membership(db, project_id, user_id):
    return db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == user_id
    ).first()

@router.get("", response_model=List[schemas.TaskOut])
def list_tasks(project_id: int, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):
    membership = get_membership(db, project_id, current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    tasks = db.query(models.Task).filter(models.Task.project_id == project_id).all()
    if membership.role == models.RoleEnum.member:
        tasks = [t for t in tasks if t.assigned_to == current_user.id]
    return tasks

@router.post("", response_model=schemas.TaskOut)
def create_task(project_id: int, data: schemas.TaskCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    membership = get_membership(db, project_id, current_user.id)
    if not membership or membership.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Only admins can create tasks")
    task = models.Task(
        title=data.title, description=data.description, due_date=data.due_date,
        priority=data.priority, project_id=project_id,
        assigned_to=data.assigned_to, created_by=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(project_id: int, task_id: int, data: schemas.TaskUpdate,
                db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    membership = get_membership(db, project_id, current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if membership.role == models.RoleEnum.member and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own tasks")
    # Members can only update status
    if membership.role == models.RoleEnum.member:
        if data.status:
            task.status = data.status
    else:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}")
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    membership = get_membership(db, project_id, current_user.id)
    if not membership or membership.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Only admins can delete tasks")
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}