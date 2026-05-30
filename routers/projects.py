from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models, schemas
from auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])

def get_member_role(db, project_id, user_id):
    return db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == user_id
    ).first()

@router.post("", response_model=schemas.ProjectOut)
def create_project(data: schemas.ProjectCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    project = models.Project(name=data.name, description=data.description, created_by=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    member = models.ProjectMember(project_id=project.id, user_id=current_user.id, role=models.RoleEnum.admin)
    db.add(member)
    db.commit()
    return project

@router.get("", response_model=List[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    memberships = db.query(models.ProjectMember).filter(models.ProjectMember.user_id == current_user.id).all()
    project_ids = [m.project_id for m in memberships]
    return db.query(models.Project).filter(models.Project.id.in_(project_ids)).all()

@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    membership = get_member_role(db, project_id, current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    creater_name=db.query(models.User).filter(models.User.id == project.created_by).first().name
    members = db.query(models.ProjectMember).filter(models.ProjectMember.project_id == project_id).all()
    members_data = [{"id": m.user_id, "name": m.user.name, "email": m.user.email, "role": m.role} for m in members]
    return {"project": project, "members": members_data, "your_role": membership.role, 'created_by': creater_name}

@router.post("/{project_id}/members")
def add_member(project_id: int, data: schemas.MemberAdd, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):
    role = get_member_role(db, project_id, current_user.id)
    if not role or role.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Only admins can add members")
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = get_member_role(db, project_id, user.id)
    if existing:
        raise HTTPException(status_code=400, detail="User already a member")
    member = models.ProjectMember(project_id=project_id, user_id=user.id, role=data.role)
    db.add(member)
    db.commit()
    return {"message": "Member added successfully"}

@router.delete("/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    role = get_member_role(db, project_id, current_user.id)
    if not role or role.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Only admins can remove members")
    member = get_member_role(db, project_id, user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    return {"message": "Member removed"}

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    role = get_member_role(db, project_id, current_user.id)
    if not role or role.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Only admins can delete projects")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}