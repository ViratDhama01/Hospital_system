from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, time

# --- Patient Schemas ---
class PatientCreate(BaseModel):
    name: str
    dob: str
    gender: str
    phone: str
    address: str
    blood_group: str

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None

class PatientRead(BaseModel):
    patient_id: int
    name: str
    dob: str
    gender: str
    phone: str
    address: str
    blood_group: str
    created_at: Optional[str] = None

# --- Doctor Schemas ---
class DoctorCreate(BaseModel):
    name: str
    department: str
    specialization: str
    available_from: str = Field(..., description="Format HH:MM")
    available_to: str = Field(..., description="Format HH:MM")

    @model_validator(mode="after")
    def validate_shift(self):
        if time.fromisoformat(self.available_from) >= time.fromisoformat(self.available_to):
            raise ValueError("available_to must be later than available_from")
        return self

class DoctorRead(BaseModel):
    doctor_id: int
    name: str
    department: str
    specialization: str
    available_from: str
    available_to: str

# --- Appointment Schemas ---
class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    start_time: datetime
    duration_minutes: int = Field(default=30, ge=5, le=120)

class AppointmentRead(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    status: str
    priority: int

# --- Queue Schemas ---
class QueueAdd(BaseModel):
    patient_id: int
    priority: int = Field(..., ge=1, le=5, description="1: Emergency, 5: Routine")

class QueuePatient(BaseModel):
    priority: int
    patient: PatientRead

# --- Report Schemas ---
class FinancialSummary(BaseModel):
    total_billed: float
    total_collected: float
    outstanding: float

class DoctorLoad(BaseModel):
    name: str
    appointment_count: int

class DeptFootfall(BaseModel):
    department: str
    total_visits: int
