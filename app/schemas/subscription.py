# app/schemas/subscription.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PaymentHistory(BaseModel):
    created_at: datetime

class Subscription(BaseModel):
    plan: str
    max_students: int
    max_teachers: int
    max_courses: int
    ai_credits: int
    storage_gb: int
    price_per_month: float
    billing_cycle: str
    status: str
    expiry_date: datetime
    payment_history: Optional[List[PaymentHistory]] = []
    tenantId: str
