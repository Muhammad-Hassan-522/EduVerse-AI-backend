from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = AsyncIOMotorClient(MONGO_URI)
db = client["LMS"]


# Tayyaba
def get_courses_collection():
    return db["courses"]

def get_students_collection():
    return db["students"]

# Eman
student_performance_collection = db["studentPerformance"]
students_collection = db["students"]
courses_collection = db["courses"]
assignments_collection = db["assignments"]              
assignment_submissions_collection = db["assignmentSubmissions"]
quizzes_collection = db["quizzes"]
quiz_submissions_collection = db["quizSubmissions"]
users_collection = db["users"]
