from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional

@dataclass
class Patient:
    patient_id: Optional[int]
    name: str
    dob: str  # Simplified as string for now
    gender: str
    phone: str
    address: str
    blood_group: str
    is_cured: int = 0
    cured_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    archived_at: Optional[datetime] = None

    def __str__(self):
        return f"Patient[{self.patient_id}]: {self.name} ({self.phone})"

@dataclass
class Doctor:
    doctor_id: Optional[int]
    name: str
    department: str
    specialization: str
    available_from: time
    available_to: time
    employment_status: str = "active"
    status_reason: Optional[str] = None
    status_updated_at: Optional[datetime] = None

    def __str__(self):
        return f"Doctor[{self.doctor_id}]: Dr. {self.name} - {self.department} ({self.specialization})"

@dataclass
class Appointment:
    appointment_id: Optional[int]
    patient: Patient
    doctor: Doctor
    start_time: datetime
    end_time: datetime
    status: str = "booked"  # booked/completed/cancelled/no-show
    priority: int = 0
    category: str = "routine"
    completed_at: Optional[datetime] = None

    def __str__(self):
        return f"Appointment[{self.appointment_id}]: {self.patient.name} with Dr. {self.doctor.name} from {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')} (Priority: {self.priority})"

class SchedulingError(Exception):
    """Base exception for scheduling errors."""
    pass

class SlotOutsideAvailabilityError(SchedulingError):
    """Raised when a requested slot is outside the doctor's shift."""
    pass

class SlotOverlapError(SchedulingError):
    """Raised when a requested slot overlaps an existing appointment."""
    pass

class PastAppointmentError(SchedulingError):
    """Raised when attempting to book a routine appointment in the past."""
    pass
