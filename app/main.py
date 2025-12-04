from fastapi import FastAPI
from app.routers import students, assignments, assignment_submissions, superAdmin, tenants, quizzes, quiz_submissions
from fastapi.middleware.cors import CORSMiddleware
from app.routers import  students, assignments, assignment_submissions, superAdmin, admins, teachers, subscription

app = FastAPI(title="EduVerse AI Backend")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ['http://localhost:4200'] for Angular dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message" : "Success !"}

app.include_router(superAdmin.router)
app.include_router(students.router)
app.include_router(assignments.router)
app.include_router(assignment_submissions.router)


# Hassan
app.include_router(tenants.router)
app.include_router(quizzes.router)
app.include_router(quiz_submissions.router)
app.include_router(admins.router)
app.include_router(subscription.router)
app.include_router(teachers.router)
