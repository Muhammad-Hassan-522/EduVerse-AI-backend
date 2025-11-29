from fastapi import FastAPI
from app.routers import  students, assignments, assignment_submissions

app = FastAPI(title="EduVerse AI Backend")

@app.get("/")
def root():
    return {"message" : "Success !"}

app.include_router(students.router)
app.include_router(assignments.router)
app.include_router(assignment_submissions.router)