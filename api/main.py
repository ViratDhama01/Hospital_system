import asyncio
import json
from fastapi import FastAPI, HTTPException, Depends, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, time
from pathlib import Path

from core.patient_registry import PatientRegistry
from core.doctor_manager import DoctorManager
from core.scheduler import Scheduler
from core.queue_manager import QueueManager
from core.billing import BillingSystem
from core.reporting import ReportingSystem
from core.auth import auth_manager
from core.ehr import ehr_manager
from core.prescriptions import prescription_manager
from core.lab import lab_manager
from core.triage_agent import triage_agent
from api.websocket import queue_notifier
from api.schemas import (
    LoginRequest,
    ProfileUpdate,
    PatientCreate, PatientRead, PatientUpdate, PatientCureUpdate,
    DoctorCreate, DoctorRead, DoctorStatusUpdate,
    AppointmentCreate, AppointmentRead,
    AppointmentCompleteRequest,
    QueueAdd, QueuePatient,
    FinancialSummary, DoctorLoad, DeptFootfall, BillGenerateRequest,
    BillPaymentRequest, BillStatusUpdate,
    HealthRecordCreate, HealthRecordRead,
    PrescriptionCreate, PrescriptionRead,
    LabResultCreate, LabResultRead
)

app = FastAPI(title="Hospital Registration System API")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend is alive and responding!"}

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Singleton Core Systems ---
def async_notifier(message):
    """Wrapper to call async broadcast from sync core logic."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(queue_notifier.broadcast(message))
        else:
            asyncio.run(queue_notifier.broadcast(message))
    except RuntimeError:
        # In some environments, get_event_loop might fail if no loop is set
        pass

registry = PatientRegistry()
doc_manager = DoctorManager()
scheduler = Scheduler()
billing = BillingSystem()
reporting = ReportingSystem()
queue_manager = QueueManager(registry, notifier=async_notifier)

# --- Auth Dependency ---
def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        return None

    # Remove 'Bearer ' prefix
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    payload = auth_manager.decode_access_token(token)
    return payload if payload else None

def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

@app.get("/search", tags=["Search"])
def global_search(q: str, user: dict = Depends(require_auth)):
    """Search active patients and doctors for the global navigation bar."""
    term = q.strip()
    if len(term) < 2:
        return {"patients": [], "doctors": []}

    from db.database import db
    pattern = f"%{term}%"
    patients = db.query(
        "SELECT patient_id, name, phone FROM patients "
        "WHERE is_cured = 0 AND (LOWER(name) LIKE LOWER(?) OR phone LIKE ? "
        "OR CAST(patient_id AS TEXT) LIKE ?) "
        "ORDER BY name LIMIT 6",
        (pattern, pattern, pattern),
    )
    doctors = db.query(
        "SELECT doctor_id, name, department, specialization FROM doctors "
        "WHERE employment_status = 'active' AND (LOWER(name) LIKE LOWER(?) "
        "OR LOWER(department) LIKE LOWER(?) OR LOWER(specialization) LIKE LOWER(?) "
        "OR CAST(doctor_id AS TEXT) LIKE ?) "
        "ORDER BY name LIMIT 6",
        (pattern, pattern, pattern, pattern),
    )
    patient_rows = [dict(row) for row in patients]
    doctor_rows = [dict(row) for row in doctors]
    if term.isdigit() and len(term) <= 18:
        # Exact ID lookups go through the managers' hash maps and take priority
        # over partial text matches from the database.
        patient = registry.get_by_id(int(term))
        if patient and not patient.is_cured:
            exact_patient = {"patient_id": patient.patient_id, "name": patient.name, "phone": patient.phone}
            patient_rows = [exact_patient] + [row for row in patient_rows if row["patient_id"] != patient.patient_id]
        doctor = doc_manager.get_by_id(int(term))
        if doctor and doctor.employment_status == "active":
            exact_doctor = {
                "doctor_id": doctor.doctor_id,
                "name": doctor.name,
                "department": doctor.department,
                "specialization": doctor.specialization,
            }
            doctor_rows = [exact_doctor] + [row for row in doctor_rows if row["doctor_id"] != doctor.doctor_id]
    return {
        "patients": patient_rows[:6],
        "doctors": doctor_rows[:6],
    }

# --- Initialization ---
@app.on_event("startup")
def startup_event():
    from db.database import db
    user = db.query_one("SELECT * FROM users WHERE username = 'admin'")
    if not user:
        auth_manager.create_user("admin", "admin123", role="admin")
        print("Default admin user created: admin / admin123")
    elif not user['hashed_password']:
        hashed_pw = auth_manager.get_password_hash("admin123")
        db.execute("UPDATE users SET hashed_password = ? WHERE username = 'admin'", (hashed_pw,))
        print("Default admin password reset: admin / admin123")

@app.post("/signup", tags=["Auth"])
async def signup(user_data: dict, request: Request):
    username = user_data.get("username")
    password = user_data.get("password")
    role = user_data.get("role", "receptionist")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    # Check if user already exists
    existing = auth_manager.authenticate_user(username, "dummy_password") # This is a bit hacky, should have a dedicated check
    # Better: use db.query_one
    from db.database import db
    if db.query_one("SELECT * FROM users WHERE username = ?", (username,)):
        raise HTTPException(status_code=400, detail="Username already taken")

    user_id = auth_manager.create_user(username, password, role, user_data.get("display_name"))
    return {"message": "User created successfully", "user_id": user_id}

@app.get("/auth/status", tags=["Auth"])
async def get_auth_status(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"message": "Not authenticated"})
    return {"user": user}

@app.get("/auth/profile", tags=["Auth"])
def get_profile(user: dict = Depends(require_auth)):
    from db.database import db
    profile = db.query_one(
        "SELECT user_id, username, display_name, role FROM users WHERE user_id = ?",
        (user.get("user_id"),),
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Account not found")
    return dict(profile)

@app.put("/auth/profile", tags=["Auth"])
def update_profile(update: ProfileUpdate, user: dict = Depends(require_auth)):
    from db.database import db
    account = db.query_one("SELECT * FROM users WHERE user_id = ?", (user.get("user_id"),))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    username = update.username.strip()
    display_name = update.display_name.strip()
    if not username or not display_name:
        raise HTTPException(status_code=400, detail="Username and display name cannot be empty")
    if username != account["username"]:
        duplicate = db.query_one(
            "SELECT user_id FROM users WHERE LOWER(username) = LOWER(?) AND user_id != ?",
            (username, account["user_id"]),
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="That username is already in use")

    password_hash = account["hashed_password"]
    if update.new_password:
        if not update.current_password or not auth_manager.verify_password(update.current_password, password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        password_hash = auth_manager.get_password_hash(update.new_password)

    db.execute(
        "UPDATE users SET username = ?, display_name = ?, hashed_password = ? WHERE user_id = ?",
        (username, display_name, password_hash, account["user_id"]),
    )
    updated_profile = {
        "user_id": account["user_id"],
        "username": username,
        "display_name": display_name,
        "role": account["role"],
    }
    return {
        **updated_profile,
        "access_token": auth_manager.create_access_token(updated_profile),
    }

@app.post("/login", tags=["Auth"])
async def login(login_data: LoginRequest):
    username = login_data.username
    password = login_data.password

    user = auth_manager.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    token = auth_manager.create_access_token(user)
    return {"message": "Login successful", "access_token": token, "user": user}

@app.get("/logout")
async def logout(request: Request):
    # Build a redirect AND delete the cookie on the same response object
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

# --- Patient Routes ---

@app.get("/patients/", response_model=List[PatientRead], tags=["Patients"])
def list_patients(status: str = "active", user: dict = Depends(require_auth)):
    try:
        patients = registry.list_all_patients(status)
        # Explicitly convert datetime objects to strings to avoid Pydantic validation crashes
        serialized_patients = []
        for p in patients:
            p_dict = p.__dict__.copy() if hasattr(p, '__dict__') else dict(p)
            if 'created_at' in p_dict and p_dict['created_at']:
                if not isinstance(p_dict['created_at'], str):
                    p_dict['created_at'] = p_dict['created_at'].isoformat()
            if 'cured_at' in p_dict and p_dict['cured_at'] and not isinstance(p_dict['cured_at'], str):
                p_dict['cured_at'] = p_dict['cured_at'].isoformat()
            serialized_patients.append(p_dict)
        return serialized_patients
    except Exception as e:
        print(f"Error in list_patients: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/patients/", response_model=PatientRead, tags=["Patients"])
def register_patient(patient: PatientCreate, user: dict = Depends(require_auth)):
    if registry.get_by_phone(patient.phone):
        raise HTTPException(status_code=409, detail="A patient with this phone number already exists")
    try:
        p = registry.register_patient(
            patient.name, patient.dob, patient.gender,
            patient.phone, patient.address, patient.blood_group
        )
        # Explicitly convert the response to avoid Pydantic crashes
        res = registry.get_by_id(p.patient_id)
        res_dict = res.__dict__.copy() if hasattr(res, '__dict__') else dict(res)
        if 'created_at' in res_dict and res_dict['created_at']:
            if not isinstance(res_dict['created_at'], str):
                res_dict['created_at'] = res_dict['created_at'].isoformat()
        return res_dict
    except Exception as e:
        print(f"Error in register_patient: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/patients/{patient_id}", response_model=PatientRead, tags=["Patients"])
def get_patient(patient_id: int, user: dict = Depends(require_auth)):
    p = registry.get_by_id(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return p

@app.patch("/patients/{patient_id}", response_model=PatientRead, tags=["Patients"])
def update_patient(patient_id: int, updates: PatientUpdate, user: dict = Depends(require_auth)):
    """Update one or more fields of an existing patient."""
    p = registry.get_by_id(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    success = registry.update_patient(patient_id, **update_data)
    if not success:
        raise HTTPException(status_code=400, detail="Update failed (phone may already be in use)")
    return registry.get_by_id(patient_id)

@app.patch("/patients/{patient_id}/cure", response_model=PatientRead, tags=["Patients"])
def update_patient_cure_status(
    patient_id: int,
    update: PatientCureUpdate,
    user: dict = Depends(require_auth),
):
    if user.get("role") not in {"doctor", "admin"}:
        raise HTTPException(status_code=403, detail="Only doctors or admins can update cure status")
    if not registry.get_by_id(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    if not registry.set_cured(patient_id, update.cured):
        raise HTTPException(status_code=400, detail="Unable to update patient status")
    patient = registry.get_by_id(patient_id)
    result = patient.__dict__.copy()
    for field in ("created_at", "cured_at"):
        if result.get(field) and not isinstance(result[field], str):
            result[field] = result[field].isoformat()
    return result

@app.get("/patients/phone/{phone}", response_model=PatientRead, tags=["Patients"])
def get_patient_by_phone(phone: str, user: dict = Depends(require_auth)):
    p = registry.get_by_phone(phone)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return p

# --- Doctor Routes ---

@app.get("/doctors/", response_model=List[DoctorRead], tags=["Doctors"])
def list_doctors(status: str = "active", user: dict = Depends(require_auth)):
    if status not in {"active", "archived", "all"}:
        raise HTTPException(status_code=400, detail="status must be active, archived, or all")
    docs = doc_manager.list_all_doctors(status)
    return [
        DoctorRead(
            doctor_id=d.doctor_id,
            name=d.name,
            department=d.department,
            specialization=d.specialization,
            available_from=d.available_from.strftime('%H:%M'),
            available_to=d.available_to.strftime('%H:%M'),
            employment_status=d.employment_status,
            status_reason=d.status_reason,
            status_updated_at=d.status_updated_at
        ) for d in docs
    ]

@app.get("/doctors/{doctor_id}", response_model=DoctorRead, tags=["Doctors"])
def get_doctor(doctor_id: int, user: dict = Depends(require_auth)):
    d = doc_manager.get_by_id(doctor_id)
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return DoctorRead(
        doctor_id=d.doctor_id,
        name=d.name,
        department=d.department,
        specialization=d.specialization,
        available_from=d.available_from.strftime('%H:%M'),
        available_to=d.available_to.strftime('%H:%M'),
        employment_status=d.employment_status,
        status_reason=d.status_reason,
        status_updated_at=d.status_updated_at
    )

@app.post("/doctors/", response_model=DoctorRead, tags=["Doctors"])
def register_doctor(doctor: DoctorCreate, user: dict = Depends(require_auth)):
    from db.database import db
    duplicate = db.query_one(
        "SELECT doctor_id FROM doctors WHERE employment_status = 'active' "
        "AND LOWER(TRIM(name)) = LOWER(TRIM(?)) "
        "AND LOWER(TRIM(department)) = LOWER(TRIM(?)) "
        "AND LOWER(TRIM(specialization)) = LOWER(TRIM(?)) LIMIT 1",
        (doctor.name, doctor.department, doctor.specialization),
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"A matching active doctor already exists (ID {duplicate['doctor_id']}).",
        )
    start = time.fromisoformat(doctor.available_from)
    end = time.fromisoformat(doctor.available_to)
    d = doc_manager.register_doctor(doctor.name, doctor.department, doctor.specialization, start, end)
    return DoctorRead(
        doctor_id=d.doctor_id,
        name=d.name,
        department=d.department,
        specialization=d.specialization,
        available_from=d.available_from.strftime('%H:%M'),
        available_to=d.available_to.strftime('%H:%M'),
        employment_status=d.employment_status,
        status_reason=d.status_reason,
        status_updated_at=d.status_updated_at
    )

@app.patch("/doctors/{doctor_id}", tags=["Doctors"])
def update_doctor(doctor_id: int, updates: dict, user: dict = Depends(require_auth)):
    # Handle time conversion for available_from/to
    if 'available_from' in updates:
        updates['available_from'] = time.fromisoformat(updates['available_from'])
    if 'available_to' in updates:
        updates['available_to'] = time.fromisoformat(updates['available_to'])

    success = doc_manager.update_doctor(doctor_id, **updates)
    if not success:
        raise HTTPException(status_code=400, detail="Update failed")

    d = doc_manager.get_by_id(doctor_id)
    return DoctorRead(
        doctor_id=d.doctor_id,
        name=d.name,
        department=d.department,
        specialization=d.specialization,
        available_from=d.available_from.strftime('%H:%M'),
        available_to=d.available_to.strftime('%H:%M'),
        employment_status=d.employment_status,
        status_reason=d.status_reason,
        status_updated_at=d.status_updated_at
    )

@app.patch("/doctors/{doctor_id}/status", response_model=DoctorRead, tags=["Doctors"])
def update_doctor_status(
    doctor_id: int,
    update: DoctorStatusUpdate,
    user: dict = Depends(require_auth),
):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to update doctor status")
    doctor = doc_manager.get_by_id(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doc_manager.update_employment_status(doctor_id, update.employment_status)
    updated = doc_manager.get_by_id(doctor_id)
    return DoctorRead(
        doctor_id=updated.doctor_id,
        name=updated.name,
        department=updated.department,
        specialization=updated.specialization,
        available_from=updated.available_from.strftime('%H:%M'),
        available_to=updated.available_to.strftime('%H:%M'),
        employment_status=updated.employment_status,
        status_reason=updated.status_reason,
        status_updated_at=updated.status_updated_at,
    )

# --- Appointment Routes ---

@app.get("/appointments/", response_model=List[AppointmentRead], tags=["Appointments"])
def list_appointments(user: dict = Depends(require_auth)):
    """List all booked appointments."""
    try:
        from db.database import db
        rows = db.query("SELECT * FROM appointments ORDER BY start_time ASC")
        result = []
        for row in rows:
            # Explicitly ensure start_time and end_time are handled as strings or formatted objects
            st = row['start_time']
            et = row['end_time']
            if isinstance(st, datetime): st = st.isoformat()
            if isinstance(et, datetime): et = et.isoformat()

            result.append({
                "appointment_id": row['appointment_id'],
                "patient_id": row['patient_id'],
                "doctor_id": row['doctor_id'],
                "start_time": st,
                "end_time": et,
                "status": row['status'],
                "priority": row['priority'],
                "category": row['category'] or "routine",
                "completed_at": row['completed_at'].isoformat() if isinstance(row['completed_at'], datetime) else row['completed_at'],
            })
        return result
    except Exception as e:
        print(f"Error in list_appointments: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/appointments/available-slots", tags=["Appointments"])
def get_available_appointment_slots(
    doctor_id: int,
    date: str,
    duration_minutes: int = 30,
    timezone_offset_minutes: int = 0,
    user: dict = Depends(require_auth),
):
    """Offer only appointment starts that fit the doctor's shift and current bookings."""
    from db.database import db
    from datetime import date as date_type, datetime, timedelta, timezone

    try:
        target_date = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must use YYYY-MM-DD format")
    if not 5 <= duration_minutes <= 120:
        raise HTTPException(status_code=400, detail="Duration must be between 5 and 120 minutes")

    doctor = doc_manager.get_by_id(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if doctor.employment_status != "active":
        raise HTTPException(status_code=409, detail="This doctor is not accepting new appointments")

    clinic_now = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=timezone_offset_minutes)
    target_start = datetime.combine(target_date, time.min)
    target_end = target_start + timedelta(days=1)
    crosses_midnight = doctor.available_to <= doctor.available_from
    if crosses_midnight:
        windows = [
            (datetime.combine(target_date - timedelta(days=1), doctor.available_from),
             datetime.combine(target_date, doctor.available_to)),
            (datetime.combine(target_date, doctor.available_from),
             datetime.combine(target_date + timedelta(days=1), doctor.available_to)),
        ]
    else:
        windows = [(
            datetime.combine(target_date, doctor.available_from),
            datetime.combine(target_date, doctor.available_to),
        )]

    def as_datetime(value):
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed

    booked_rows = db.query(
        "SELECT start_time, end_time FROM appointments "
        "WHERE doctor_id = ? AND status = 'booked'",
        (doctor_id,),
    )
    booked = [(as_datetime(row["start_time"]), as_datetime(row["end_time"])) for row in booked_rows]
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=15)
    slots = []
    for window_start, window_end in windows:
        candidate = max(window_start, target_start, clinic_now)
        # Keep starts aligned to the 15-minute grid based on the doctor's shift start.
        elapsed = max(0, int((candidate - window_start).total_seconds() // step.total_seconds()))
        candidate = window_start + elapsed * step
        if candidate < max(window_start, target_start, clinic_now):
            candidate += step
        while candidate.date() < target_end.date() and candidate + duration <= window_end:
            if not any(candidate < booked_end and booked_start < candidate + duration for booked_start, booked_end in booked):
                slots.append(candidate.isoformat(timespec="minutes"))
            candidate += step

    return {
        "doctor_id": doctor_id,
        "date": target_date.isoformat(),
        "duration_minutes": duration_minutes,
        "slots": slots,
    }

@app.post("/appointments/", response_model=AppointmentRead, tags=["Appointments"])
def book_appointment(apt_req: AppointmentCreate, user: dict = Depends(require_auth)):
    patient = registry.get_by_id(apt_req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = doc_manager.get_by_id(apt_req.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if doctor.employment_status != "active":
        raise HTTPException(status_code=409, detail="This doctor is no longer available for new appointments")

    try:
        from datetime import timedelta, timezone
        clinic_now = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=apt_req.timezone_offset_minutes)
        apt = scheduler.book_appointment(
            patient, doctor, apt_req.start_time, apt_req.duration_minutes,
            apt_req.category, clinic_now,
        )
        if not apt:
            raise HTTPException(status_code=400, detail="Doctor unavailable at that time or slot overlaps an existing appointment")

        res = {
            "appointment_id": apt.appointment_id,
            "patient_id": apt.patient.patient_id,
            "doctor_id": apt.doctor.doctor_id,
            "start_time": apt.start_time.isoformat() if hasattr(apt.start_time, 'isoformat') else apt.start_time,
            "end_time": apt.end_time.isoformat() if hasattr(apt.end_time, 'isoformat') else apt.end_time,
            "status": apt.status,
            "priority": apt.priority,
            "category": apt.category,
            "completed_at": None,
            "rescheduled_for_emergency": apt_req.category == "emergency" and apt.start_time != apt_req.start_time.replace(tzinfo=None),
        }
        return res
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in book_appointment: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.patch("/appointments/{appointment_id}/cancel", tags=["Appointments"])
def cancel_appointment(appointment_id: int, user: dict = Depends(require_auth)):
    """Cancel an appointment by ID."""
    success = scheduler.cancel_appointment(appointment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": "Appointment cancelled"}

@app.patch("/appointments/{appointment_id}/complete", tags=["Appointments"])
def complete_appointment(appointment_id: int, completion: Optional[AppointmentCompleteRequest] = None, user: dict = Depends(require_auth)):
    """Complete a visit and advance that doctor's remaining schedule if it finished early."""
    if user.get("role") not in {"doctor", "admin"}:
        raise HTTPException(status_code=403, detail="Only doctors or admins can complete appointments")

    from db.database import db
    from datetime import datetime, timedelta

    row = db.query_one("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if row["status"] != "booked":
        raise HTTPException(status_code=409, detail="Only booked appointments can be completed")

    def as_datetime(value):
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed

    now = (completion.completed_at if completion and completion.completed_at else datetime.now()).replace(microsecond=0)
    if now.tzinfo:
        now = now.astimezone().replace(tzinfo=None)
    scheduled_start = as_datetime(row["start_time"])
    scheduled_end = as_datetime(row["end_time"])
    if now < scheduled_start:
        raise HTTPException(status_code=409, detail="An appointment cannot be completed before its scheduled start")

    early_by = max(timedelta(0), scheduled_end - now)
    completion_result = db.execute(
        "UPDATE appointments SET status = 'completed', completed_at = ? "
        "WHERE appointment_id = ? AND status = 'booked'",
        (now.isoformat(), appointment_id),
    )
    if completion_result.rowcount == 0:
        raise HTTPException(status_code=409, detail="This appointment has already changed")

    shifted = []
    if early_by.total_seconds() > 0:
        upcoming = db.query(
            "SELECT a.appointment_id, a.patient_id, a.start_time, a.end_time, p.name AS patient_name "
            "FROM appointments a JOIN patients p ON p.patient_id = a.patient_id "
            "WHERE a.doctor_id = ? AND a.status = 'booked' ORDER BY a.start_time ASC",
            (row["doctor_id"],),
        )
        cursor_time = now
        for next_appointment in upcoming:
            old_start = as_datetime(next_appointment["start_time"])
            old_end = as_datetime(next_appointment["end_time"])
            if old_start <= now:
                cursor_time = max(cursor_time, old_end)
                continue
            duration = old_end - old_start
            doctor = doc_manager.get_by_id(row["doctor_id"])
            crosses_midnight = doctor.available_to <= doctor.available_from
            shift_date = old_start.date()
            if crosses_midnight and old_start.time() < doctor.available_to:
                shift_date -= timedelta(days=1)
            shift_start = datetime.combine(shift_date, doctor.available_from)
            shift_end_date = shift_date + (timedelta(days=1) if crosses_midnight else timedelta())
            shift_end = datetime.combine(shift_end_date, doctor.available_to)
            new_start = max(old_start - early_by, cursor_time, shift_start)
            new_end = new_start + duration
            if new_start >= old_start or new_end > shift_end:
                cursor_time = max(cursor_time, old_end)
                continue
            cursor_time = new_end
            db.execute(
                "UPDATE appointments SET start_time = ?, end_time = ? WHERE appointment_id = ?",
                (new_start.isoformat(), new_end.isoformat(), next_appointment["appointment_id"]),
            )
            db.execute(
                "INSERT INTO appointment_schedule_history "
                "(appointment_id, previous_start, previous_end, new_start, new_end, reason, changed_by) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (next_appointment["appointment_id"], old_start.isoformat(), old_end.isoformat(),
                 new_start.isoformat(), new_end.isoformat(),
                 f"Moved earlier by {int(early_by.total_seconds() // 60)} minutes after an early completion",
                 user.get("user_id")),
            )
            shifted.append({
                "appointment_id": next_appointment["appointment_id"],
                "patient_id": next_appointment["patient_id"],
                "patient_name": next_appointment["patient_name"],
                "start_time": new_start.isoformat(),
                "end_time": new_end.isoformat(),
            })

    return {
        "message": "Appointment completed",
        "appointment_id": appointment_id,
        "completed_at": now.isoformat(),
        "early_by_minutes": round(early_by.total_seconds() / 60, 1),
        "shifted_appointments": shifted,
    }

# --- Queue Routes ---

@app.post("/queue/add", response_model=dict, tags=["Queue"])
def add_to_queue(req: QueueAdd, user: dict = Depends(require_auth)):
    patient = registry.get_by_id(req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    queue_manager.add_patient(patient, req.priority)
    return {"message": f"Patient {patient.name} added to queue with priority {req.priority}"}

@app.get("/queue/next", response_model=Optional[QueuePatient], tags=["Queue"])
def pop_next_patient(user: dict = Depends(require_auth)):
    result = queue_manager.pop_next_patient()
    if not result:
        return None
    priority, patient = result
    assigned_doctor = None
    if priority <= 2:
        doctor_id = scheduler.recommend_doctor_for_urgent_case()
        doctor = doc_manager.get_by_id(doctor_id) if doctor_id is not None else None
        if doctor and doctor.employment_status == "active":
            assigned_doctor = DoctorRead(
                doctor_id=doctor.doctor_id,
                name=doctor.name,
                department=doctor.department,
                specialization=doctor.specialization,
                available_from=doctor.available_from.strftime('%H:%M'),
                available_to=doctor.available_to.strftime('%H:%M'),
                employment_status=doctor.employment_status,
            )
    return QueuePatient(
        priority=priority,
        patient=PatientRead(
            patient_id=patient.patient_id,
            name=patient.name,
            dob=patient.dob,
            gender=patient.gender,
            phone=patient.phone,
            address=patient.address,
            blood_group=patient.blood_group,
            created_at=patient.created_at
        ),
        assigned_doctor=assigned_doctor,
    )

@app.get("/queue/list", response_model=List[QueuePatient], tags=["Queue"])
def list_queue(user: dict = Depends(require_auth)):
    queue = queue_manager.get_queue()
    return [
        QueuePatient(
            priority=p,
            patient=PatientRead(
                patient_id=pat.patient_id,
                name=pat.name,
                dob=pat.dob,
                gender=pat.gender,
                phone=pat.phone,
                address=pat.address,
                blood_group=pat.blood_group,
                created_at=pat.created_at
            )
        ) for p, _, pat in queue
    ]

@app.post("/queue/triage", tags=["Queue"])
def triage_and_add(patient_id: int, symptoms: str, user: dict = Depends(require_auth)):
    patient = registry.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not symptoms.strip():
        raise HTTPException(status_code=400, detail="Symptoms are required")

    priority = triage_agent.triage_patient(patient_id, symptoms)

    queue_manager.add_patient(patient, priority)
    return {"message": f"Triage complete. Assigned priority {priority} based on symptoms.", "priority": priority}

# --- Reports ---

@app.get("/reports/financials", response_model=FinancialSummary, tags=["Reports"])
def get_financials(user: dict = Depends(require_auth)):
    try:
        fin = reporting.get_financial_summary()
    except Exception:
        # bills table may not exist yet
        fin = {"total_billed": 0.0, "total_collected": 0.0, "outstanding": 0.0}
    return FinancialSummary(**fin)

@app.get("/dashboard/summary", tags=["Dashboard"])
def get_dashboard_summary(timezone_offset_minutes: int = 0, user: dict = Depends(require_auth)):
    """Return current dashboard figures and today's real appointment schedule."""
    from db.database import db
    from datetime import date, datetime, timedelta, timezone

    def parse_datetime(value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    now = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=timezone_offset_minutes)
    today = now.date()
    appointments = db.query(
        "SELECT a.appointment_id, a.patient_id, a.doctor_id, a.start_time, a.end_time, "
        "a.status, a.priority, a.category, p.name AS patient_name, d.name AS doctor_name, "
        "d.department AS department FROM appointments a "
        "JOIN patients p ON p.patient_id = a.patient_id "
        "JOIN doctors d ON d.doctor_id = a.doctor_id ORDER BY a.start_time ASC"
    )
    todays_appointments = []
    for row in appointments:
        start = parse_datetime(row["start_time"])
        if start.date() != today:
            continue
        todays_appointments.append({
            "appointment_id": row["appointment_id"],
            "patient_id": row["patient_id"],
            "doctor_id": row["doctor_id"],
            "patient_name": row["patient_name"],
            "doctor_name": row["doctor_name"],
            "department": row["department"],
            "start_time": start.isoformat(),
            "end_time": parse_datetime(row["end_time"]).isoformat(),
            "status": row["status"],
            "priority": row["priority"],
            "category": row["category"] or "routine",
        })

    queue_rows = db.query("SELECT arrival_time FROM walk_in_queue")
    wait_minutes = []
    for row in queue_rows:
        arrived = parse_datetime(row["arrival_time"])
        if arrived.tzinfo is None:
            arrived -= timedelta(minutes=timezone_offset_minutes)
        if arrived.tzinfo and now.tzinfo is None:
            arrived = arrived.replace(tzinfo=None)
        wait_minutes.append(max(0, (now - arrived).total_seconds() / 60))

    financials = reporting.get_financial_summary()
    active_patients = db.query_one("SELECT COUNT(*) AS total FROM patients WHERE is_cured = 0")["total"]
    total_doctors = db.query_one("SELECT COUNT(*) AS total FROM doctors WHERE employment_status = 'active'")["total"]
    recent_patients = db.query(
        "SELECT patient_id, name, is_cured, created_at FROM patients "
        "WHERE is_cured = 0 ORDER BY created_at DESC LIMIT 4"
    )
    recent = []
    for row in recent_patients:
        created = parse_datetime(row["created_at"])
        if created.tzinfo is None:
            created -= timedelta(minutes=timezone_offset_minutes)
        recent.append({
            "patient_id": row["patient_id"], "name": row["name"],
            "is_cured": bool(row["is_cured"]), "created_at": created.isoformat(),
        })

    return {
        "as_of": now.isoformat(),
        "active_patients": active_patients,
        "active_doctors": total_doctors,
        "appointments_today": len([a for a in todays_appointments if a["status"] != "cancelled"]),
        "average_current_wait_minutes": round(sum(wait_minutes) / len(wait_minutes)) if wait_minutes else None,
        "patients_waiting": len(wait_minutes),
        "total_billed": financials["total_billed"],
        "total_collected": financials["total_collected"],
        "outstanding": financials["outstanding"],
        "recent_patients": recent,
        "today_schedule": todays_appointments,
    }

@app.get("/history/", tags=["History"])
def get_history(user: dict = Depends(require_auth)):
    """Return a unified, newest-first view of persisted hospital records."""
    from db.database import db

    events = []

    def add_events(category, rows, timestamp_key, title_key, detail_builder, id_key, patient_key=None):
        for row in rows:
            value = row[timestamp_key]
            if value is None:
                continue
            happened = value.isoformat() if hasattr(value, "isoformat") else str(value)
            events.append({
                "category": category,
                "record_id": row[id_key],
                "occurred_at": happened,
                "title": str(row[title_key]),
                "detail": detail_builder(row),
                "patient_id": row[patient_key] if patient_key else None,
            })

    add_events("Patients", db.query("SELECT patient_id, name, created_at FROM patients"), "created_at", "name", lambda r: f"Patient registered · #{r['patient_id']}", "patient_id", "patient_id")
    add_events("Patients", db.query("SELECT patient_id, name, cured_at FROM patients WHERE is_cured = 1 AND cured_at IS NOT NULL"), "cured_at", "name", lambda r: f"Patient marked cured · #{r['patient_id']}", "patient_id", "patient_id")
    add_events("Doctors", db.query("SELECT doctor_id, name, department, employment_status, status_updated_at FROM doctors"), "status_updated_at", "name", lambda r: f"{r['employment_status'].title()} · {r['department']} · Doctor #{r['doctor_id']}", "doctor_id")
    add_events("Appointments", db.query("SELECT a.appointment_id, a.patient_id, a.start_time, a.status, a.category, p.name AS patient_name, d.name AS doctor_name FROM appointments a JOIN patients p ON p.patient_id = a.patient_id JOIN doctors d ON d.doctor_id = a.doctor_id"), "start_time", "patient_name", lambda r: f"Appointment #{r['appointment_id']} · Dr. {r['doctor_name']} · {r['status']} · {r['category'] or 'routine'}", "appointment_id", "patient_id")
    add_events("Appointments", db.query("SELECT a.appointment_id, a.patient_id, a.completed_at, p.name AS patient_name, d.name AS doctor_name FROM appointments a JOIN patients p ON p.patient_id = a.patient_id JOIN doctors d ON d.doctor_id = a.doctor_id WHERE a.completed_at IS NOT NULL"), "completed_at", "patient_name", lambda r: f"Appointment #{r['appointment_id']} completed · Dr. {r['doctor_name']}", "appointment_id", "patient_id")
    add_events("Appointments", db.query("SELECT h.history_id, h.appointment_id, h.previous_start, h.new_start, h.reason, h.changed_at, a.patient_id, p.name AS patient_name FROM appointment_schedule_history h JOIN appointments a ON a.appointment_id = h.appointment_id JOIN patients p ON p.patient_id = a.patient_id"), "changed_at", "patient_name", lambda r: f"Appointment #{r['appointment_id']} moved from {r['previous_start']} to {r['new_start']} · {r['reason']}", "history_id", "patient_id")
    add_events("Billing", db.query("SELECT b.bill_id, b.appointment_id, b.amount, b.payment_status, b.bill_date, a.patient_id, p.name AS patient_name FROM bills b JOIN appointments a ON a.appointment_id = b.appointment_id JOIN patients p ON p.patient_id = a.patient_id"), "bill_date", "patient_name", lambda r: f"Invoice #{r['bill_id']} · ₹{r['amount']} · {r['payment_status']}", "bill_id", "patient_id")
    add_events("Billing", db.query("SELECT pay.payment_id, pay.bill_id, pay.amount, pay.payment_method, pay.payment_date, pay.status, a.patient_id, p.name AS patient_name FROM payments pay JOIN bills b ON b.bill_id = pay.bill_id JOIN appointments a ON a.appointment_id = b.appointment_id JOIN patients p ON p.patient_id = a.patient_id"), "payment_date", "patient_name", lambda r: f"Payment #{r['payment_id']} · ₹{r['amount']} · {r['payment_method'] or 'Payment'} · {r['status']}", "payment_id", "patient_id")
    add_events("EHR", db.query("SELECT h.record_id, h.patient_id, h.note, h.category, h.created_at, p.name AS patient_name, d.name AS doctor_name FROM health_records h JOIN patients p ON p.patient_id = h.patient_id JOIN doctors d ON d.doctor_id = h.doctor_id"), "created_at", "patient_name", lambda r: f"{r['category'] or 'Clinical note'} · Dr. {r['doctor_name']} · {r['note']}", "record_id", "patient_id")
    add_events("Prescriptions", db.query("SELECT pr.prescription_id, pr.patient_id, pr.medication, pr.dosage, pr.date_issued, p.name AS patient_name FROM prescriptions pr JOIN patients p ON p.patient_id = pr.patient_id"), "date_issued", "patient_name", lambda r: f"Prescription #{r['prescription_id']} · {r['medication']} · {r['dosage']}", "prescription_id", "patient_id")
    add_events("Lab Results", db.query("SELECT l.lab_id, l.patient_id, l.test_name, l.result_value, l.status, l.date_performed, p.name AS patient_name FROM lab_results l JOIN patients p ON p.patient_id = l.patient_id"), "date_performed", "patient_name", lambda r: f"Lab #{r['lab_id']} · {r['test_name']}: {r['result_value']} · {r['status']}", "lab_id", "patient_id")
    add_events("Notifications", db.query("SELECT n.notification_id, n.patient_id, n.message, n.channel, n.status, n.created_at, p.name AS patient_name FROM notifications n JOIN patients p ON p.patient_id = n.patient_id"), "created_at", "patient_name", lambda r: f"{r['channel']} notification · {r['status']} · {r['message']}", "notification_id", "patient_id")
    add_events("Triage", db.query("SELECT t.triage_id, t.patient_id, t.symptoms, t.assigned_priority, t.agent_id, t.assessed_at, p.name AS patient_name FROM triage_logs t JOIN patients p ON p.patient_id = t.patient_id"), "assessed_at", "patient_name", lambda r: f"Priority {r['assigned_priority']} assessment · {r['symptoms']} · {r['agent_id']}", "triage_id", "patient_id")
    add_events("Reports", db.query("SELECT snapshot_id, report_name, generated_at FROM report_snapshots"), "generated_at", "report_name", lambda r: "Saved financial, appointment, department, and clinician metrics", "snapshot_id")
    events.sort(key=lambda event: event["occurred_at"], reverse=True)
    return {"events": events[:500], "count": len(events), "as_of": datetime.now().isoformat()}

@app.post("/reports/snapshot", tags=["Reports"])
def save_report_snapshot(user: dict = Depends(require_auth)):
    """Save the currently calculated reports as a timestamped history record."""
    from db.database import db
    from datetime import datetime
    snapshot = {
        "financials": reporting.get_financial_summary(),
        "department_footfall": reporting.get_departmental_footfall(),
        "peak_hours": reporting.get_peak_hours(),
        "doctor_load": reporting.get_doctor_load(),
        "demographics": reporting.get_patient_demographics(),
    }
    cursor = db.execute(
        "INSERT INTO report_snapshots (report_name, generated_by, payload) VALUES (?, ?, ?)",
        ("Hospital performance report", user.get("user_id"), json.dumps(snapshot, default=str)),
    )
    return {"snapshot_id": cursor.lastrowid, "generated_at": datetime.now().isoformat()}

@app.get("/reports/doctor-load", response_model=List[DoctorLoad], tags=["Reports"])
def get_doctor_load(user: dict = Depends(require_auth)):
    return reporting.get_doctor_load()

@app.get("/reports/department-footfall", response_model=List[DeptFootfall], tags=["Reports"])
def get_dept_footfall(user: dict = Depends(require_auth)):
    return reporting.get_departmental_footfall()

@app.get("/reports/peak-hours", tags=["Reports"])
def get_peak_hours(user: dict = Depends(require_auth)):
    return reporting.get_peak_hours()

@app.get("/reports/demographics", tags=["Reports"])
def get_demographics(user: dict = Depends(require_auth)):
    return reporting.get_patient_demographics()

@app.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket):
    await queue_notifier.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        queue_notifier.disconnect(websocket)

# --- Billing Routes ---

@app.get("/billing/", response_model=List[dict], tags=["Billing"])
def list_bills(user: dict = Depends(require_auth)):
    from db.database import db
    rows = db.query(
        "SELECT b.*, "
        "COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.bill_id = b.bill_id AND p.status = 'completed'), 0) AS amount_paid, "
        "COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.bill_id = b.bill_id AND p.status = 'processing'), 0) AS pending_amount "
        "FROM bills b ORDER BY b.bill_date DESC, b.bill_id DESC"
    )
    result = []
    for row in rows:
        bill = dict(row)
        bill["amount_paid"] = float(bill.get("amount_paid") or 0)
        bill["pending_amount"] = float(bill.get("pending_amount") or 0)
        if bill["payment_status"] != "paid" and bill["pending_amount"] > 0:
            bill["payment_status"] = "processing"
        bill["remaining_amount"] = max(0, float(bill["amount"]) - bill["amount_paid"])
        bill["collected_amount"] = float(bill["amount"]) if bill["payment_status"] == "paid" else bill["amount_paid"]
        bill["outstanding_amount"] = 0 if bill["payment_status"] == "paid" else bill["remaining_amount"]
        result.append(bill)
    return result

@app.get("/billing/{bill_id}", response_model=dict, tags=["Billing"])
def get_bill(bill_id: int, user: dict = Depends(require_auth)):
    from db.database import db
    row = db.query_one("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Bill not found")
    return row

@app.post("/billing/generate", tags=["Billing"])
def generate_bill(req: BillGenerateRequest, user: dict = Depends(require_auth)):
    appointment_id = req.appointment_id
    from db.database import db
    row = db.query_one("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Appointment not found")

    existing_bill = db.query_one(
        "SELECT bill_id, amount, payment_status FROM bills WHERE appointment_id = ? ORDER BY bill_id DESC LIMIT 1",
        (appointment_id,),
    )
    if existing_bill:
        return {
            "message": "An invoice already exists for this appointment",
            "bill_id": existing_bill["bill_id"],
            "total": existing_bill["amount"],
            "payment_status": existing_bill["payment_status"],
            "already_exists": True,
        }

    # Reconstruct Appointment object for billing system
    from core.models import Appointment, Patient, Doctor
    from datetime import datetime

    patient = registry.get_by_id(row['patient_id'])
    doctor = doc_manager.get_by_id(row['doctor_id'])
    if not patient or not doctor:
        raise HTTPException(status_code=404, detail="The patient or doctor for this appointment no longer exists")

    def parse_db_datetime(value):
        return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))

    apt = Appointment(
        appointment_id=row['appointment_id'],
        patient=patient,
        doctor=doctor,
        start_time=parse_db_datetime(row['start_time']),
        end_time=parse_db_datetime(row['end_time']),
        status=row['status'],
        priority=row['priority']
    )

    total, patient_share = billing.generate_bill(apt)
    created_bill = db.query_one(
        "SELECT bill_id FROM bills WHERE appointment_id = ? ORDER BY bill_id DESC LIMIT 1",
        (appointment_id,),
    )
    return {
        "message": "Bill generated",
        "bill_id": created_bill["bill_id"] if created_bill else None,
        "total": total,
        "patient_share": patient_share,
        "already_exists": False,
    }

@app.post("/billing/pay", tags=["Billing"])
def pay_bill(req: BillPaymentRequest, user: dict = Depends(require_auth)):
    from db.database import db
    bill_id = req.bill_id
    bill = db.query_one("SELECT bill_id, amount, payment_status FROM bills WHERE bill_id = ?", (bill_id,))
    if not bill:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if bill["payment_status"] == "paid":
        raise HTTPException(status_code=409, detail="This invoice is already marked paid")
    pending = db.query_one("SELECT COUNT(*) AS total FROM payments WHERE bill_id = ? AND status = 'processing'", (bill_id,))
    if pending["total"]:
        raise HTTPException(status_code=409, detail="A payment for this invoice is already in process")
    paid_row = db.query_one("SELECT COALESCE(SUM(amount), 0) AS amount_paid FROM payments WHERE bill_id = ? AND status = 'completed'", (bill_id,))
    remaining = max(0, float(bill["amount"]) - float(paid_row["amount_paid"] or 0))
    if req.amount > remaining + 0.00001:
        raise HTTPException(status_code=400, detail=f"Payment exceeds the remaining balance of ₹{remaining:.2f}")

    success = billing.process_patient_payment(bill_id, req.amount, req.method)
    if not success:
        raise HTTPException(status_code=400, detail="Payment processing failed")

    updated = db.query_one("SELECT payment_status FROM bills WHERE bill_id = ?", (bill_id,))
    payment = db.query_one("SELECT payment_id, transaction_id, status FROM payments WHERE bill_id = ? ORDER BY payment_id DESC LIMIT 1", (bill_id,))
    return {
        "message": "Payment processed successfully",
        "bill_id": bill_id,
        "payment_id": payment["payment_id"] if payment else None,
        "transaction_id": payment["transaction_id"] if payment else None,
        "payment_status": payment["status"] if payment else "processing",
        "invoice_status": updated["payment_status"],
    }

@app.patch("/billing/{bill_id}/status", tags=["Billing"])
def update_bill_status(bill_id: int, update: BillStatusUpdate, user: dict = Depends(require_auth)):
    from db.database import db
    if not db.query_one("SELECT bill_id FROM bills WHERE bill_id = ?", (bill_id,)):
        raise HTTPException(status_code=404, detail="Invoice not found")
    next_payment_status = "completed" if update.payment_status == "paid" else "failed"
    db.execute(
        "UPDATE payments SET status = ? WHERE bill_id = ? AND status = 'processing'",
        (next_payment_status, bill_id),
    )
    db.execute("UPDATE bills SET payment_status = ? WHERE bill_id = ?", (update.payment_status, bill_id))
    return {"bill_id": bill_id, "payment_status": update.payment_status}

# --- Clinical Routes ---


@app.post("/clinical/ehr", response_model=HealthRecordRead, tags=["Clinical"])
def add_health_record(rec: HealthRecordCreate, user: dict = Depends(require_auth)):
    try:
        record_id = ehr_manager.add_record(rec.patient_id, rec.doctor_id, rec.note, rec.category)
        # Return as HealthRecordRead by fetching the created record
        history = ehr_manager.get_patient_history(rec.patient_id)
        record = next(r for r in history if r.record_id == record_id)

        # Explicitly convert datetime objects to strings to avoid Pydantic validation crashes
        res = record.__dict__.copy() if hasattr(record, '__dict__') else dict(record)
        if 'created_at' in res and res['created_at']:
            if not isinstance(res['created_at'], str):
                res['created_at'] = res['created_at'].isoformat()
        return res
    except Exception as e:
        print(f"Error in add_health_record: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/clinical/ehr/{patient_id}", response_model=List[HealthRecordRead], tags=["Clinical"])
def get_ehr(patient_id: int, user: dict = Depends(require_auth)):
    try:
        history = ehr_manager.get_patient_history(patient_id)
        serialized_history = []
        for r in history:
            r_dict = r.__dict__.copy() if hasattr(r, '__dict__') else dict(r)
            if 'created_at' in r_dict and r_dict['created_at']:
                if not isinstance(r_dict['created_at'], str):
                    r_dict['created_at'] = r_dict['created_at'].isoformat()
            serialized_history.append(r_dict)
        return serialized_history
    except Exception as e:
        print(f"Error in get_ehr: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/clinical/prescriptions", response_model=PrescriptionRead, tags=["Clinical"])
def issue_prescription(pres: PrescriptionCreate, user: dict = Depends(require_auth)):
    p_id = prescription_manager.issue_prescription(
        pres.patient_id, pres.doctor_id, pres.medication, pres.dosage, pres.frequency, pres.duration
    )
    prescriptions = prescription_manager.get_patient_prescriptions(pres.patient_id)
    return next(p for p in prescriptions if p.prescription_id == p_id)

@app.get("/clinical/prescriptions/{patient_id}", response_model=List[PrescriptionRead], tags=["Clinical"])
def get_prescriptions(patient_id: int, user: dict = Depends(require_auth)):
    return prescription_manager.get_patient_prescriptions(patient_id)

@app.post("/clinical/labs", response_model=LabResultRead, tags=["Clinical"])
def add_lab_result(lab: LabResultCreate, user: dict = Depends(require_auth)):
    lab_id = lab_manager.add_result(lab.patient_id, lab.test_name, lab.result_value, lab.unit, lab.status)
    labs = lab_manager.get_patient_labs(lab.patient_id)
    return next(l for l in labs if l.lab_id == lab_id)

@app.get("/clinical/labs/{patient_id}", response_model=List[LabResultRead], tags=["Clinical"])
def get_labs(patient_id: int, user: dict = Depends(require_auth)):
    return lab_manager.get_patient_labs(patient_id)
