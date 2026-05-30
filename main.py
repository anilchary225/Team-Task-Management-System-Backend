from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine , Base
from routers import auth, projects, tasks, dashboard

# Avoid crashing the app startup when DB isn't reachable.
# Migrations should be run separately (e.g., alembic).
try:
    models.Base.metadata.create_all(bind=engine)
    print('DB connected Succesfully')
except Exception as e:
    print("DB connection failed")
    print(e)

app = FastAPI(title="Team Task Manager API", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://team-task-management-system-fronten.vercel.app"],  # In production: specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)

@app.get("/")
def root():
    return {"message": "Team Task Manager API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}