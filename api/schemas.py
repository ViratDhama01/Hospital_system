from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Any, Literal
from datetime import datetime, time
from decimal import Decimal

# --- Auth Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class StaffAccessUpdate(BaseModel):
    role: Literal["doctor", "nurse", "receptionist"]
    doctor_id: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_doctor(self):
        if (self.role == "doctor") != (self.doctor_id is not None):
            raise ValueError("A doctor account must be linked to a registered doctor")
        return self


class StaffCreate(StaffAccessUpdate):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def check_password_length(cls, password):
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password is too long when encoded as UTF-8")
        return password

class ProfileUpdate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=120)
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=128)

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

class PatientCureUpdate(BaseModel):
    cured: bool

class PatientArchiveUpdate(BaseModel):
    archived: bool

class PatientRead(BaseModel):
    patient_id: int
    name: str
    dob: str
    gender: str
    phone: str
    address: str
    blood_group: str
    is_cured: bool = False
    cured_at: Optional[Any] = None
    archived_at: Optional[Any] = None
    created_at: Optional[Any] = None # Changed to Any to avoid validation crashes with datetime objects

# --- Doctor Schemas ---
class DoctorCreate(BaseModel):
    name: str
    department: str
    specialization: str
    available_from: str = Field(..., description="Format HH:MM")
    available_to: str = Field(..., description="Format HH:MM")

    @model_validator(mode="after")
    def validate_shift(self):
        try:
            time.fromisoformat(self.available_from)
            time.fromisoformat(self.available_to)
        except ValueError:
            raise ValueError("Invalid time format. Please use HH:MM")
        return self

class DoctorRead(BaseModel):
    doctor_id: int
    name: str
    department: str
    specialization: str
    available_from: str
    available_to: str
    employment_status: str = "active"
    status_reason: Optional[str] = None
    status_updated_at: Optional[Any] = None

class DoctorStatusUpdate(BaseModel):
    employment_status: Literal["active", "suspended", "resigned", "duplicate"]

# --- Appointment Schemas ---
class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    start_time: datetime
    duration_minutes: int = Field(default=30, ge=5, le=120)
    category: Literal["routine", "emergency"] = "routine"
    timezone_offset_minutes: int = Field(default=0, ge=-840, le=840)

class AppointmentCompleteRequest(BaseModel):
    completed_at: Optional[datetime] = None

class AppointmentStaffUpdate(BaseModel):
    role: Literal["nurse", "receptionist"]
    user_id: Optional[int] = Field(gt=0)

class AppointmentRead(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    nurse_user_id: Optional[int] = None
    nurse_name: Optional[str] = None
    receptionist_user_id: Optional[int] = None
    receptionist_name: Optional[str] = None
    start_time: Any # Changed to Any to prevent datetime serialization crashes
    end_time: Any # Changed to Any to prevent datetime serialization crashes
    status: str
    priority: int
    category: str = "routine"
    completed_at: Optional[Any] = None
    rescheduled_for_emergency: bool = False

# --- Queue Schemas ---
class QueueAdd(BaseModel):
    patient_id: int
    priority: int = Field(..., ge=1, le=5, description="1: Emergency, 5: Routine")

class QueuePatient(BaseModel):
    priority: int
    patient: PatientRead
    assigned_doctor: Optional[DoctorRead] = None

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

class BillGenerateRequest(BaseModel):
    appointment_id: int = Field(..., gt=0)

class BillPaymentRequest(BaseModel):
    bill_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    method: Literal["Credit Card", "Debit Card", "UPI", "Cash"] = "Credit Card"

class BillStatusUpdate(BaseModel):
    payment_status: Literal["paid", "unpaid"]
    confirm_pending: bool = False

# --- Clinical Schemas ---
class HealthRecordCreate(BaseModel):
    patient_id: int
    doctor_id: int
    note: str
    category: Optional[str] = "Consultation"

class HealthRecordRead(BaseModel):
    record_id: int
    patient_id: int
    doctor_id: int
    note: str
    category: str
    created_at: Any # Changed to Any to prevent datetime serialization crashes

class PrescriptionCreate(BaseModel):
    patient_id: int
    doctor_id: int
    medication: str
    dosage: str
    frequency: str
    duration: str

class PrescriptionRead(BaseModel):
    prescription_id: int
    patient_id: int
    doctor_id: int
    medication: str
    dosage: str
    frequency: str
    duration: str
    date_issued: Any # Changed to Any to prevent datetime serialization crashes

class LabResultCreate(BaseModel):
    patient_id: int
    test_name: str
    result_value: str
    unit: Optional[str] = None
    status: Optional[str] = "final"

class LabResultRead(BaseModel):
    lab_id: int
    patient_id: int
    test_name: str
    result_value: str
    unit: Optional[str]
    status: str
    date_performed: Any # Changed to Any to prevent datetime serialization crashes
