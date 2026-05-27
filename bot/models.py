from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class Training(BaseModel):
    day_of_week: int
    time: str
    location: str
    poll_create_days_before: int
    reminder_days_before: int
    enabled: bool = True


class Debtor(BaseModel):
    name: str
    balance: float


class PollRecord(BaseModel):
    poll_id: str
    message_id: int
    date: str
    time: str
    location: str
    thread_id: Optional[int] = None
    status: str = "active"


class PaymentMethod(BaseModel):
    name: str
    details: str


class PaymentConfig(BaseModel):
    methods: list[PaymentMethod] = []
    contact_user_id: Optional[int] = None
    contact_name: str = "капитан"
