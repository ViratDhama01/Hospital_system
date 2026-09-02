from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
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
from api.schemas import (
    PatientCreate, PatientRead, PatientUpdate,
    DoctorCreate, DoctorRead,
    AppointmentCreate, AppointmentRead,
    QueueAdd, QueuePatient,
    FinancialSummary, DoctorLoad, DeptFootfall
)

app = FastAPI(title="Hospital Registration System API")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Static Files & Templates ---
static_dir = PROJECT_ROOT / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

# --- Singleton Core Systems ---
registry = PatientRegistry()
doc_manager = DoctorManager()
scheduler = Scheduler()
billing = BillingSystem()
reporting = ReportingSystem()
queue_manager = QueueManager(registry)

# --- Auth Dependency ---
def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = auth_manager.decode_access_token(token)
    return payload if payload else None

def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

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

# --- Auth Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse(request=request, name="login.html")
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@app.post("/login")
async def login(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")

    user = auth_manager.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    token = auth_manager.create_access_token(user)
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return response

@app.get("/logout")
async def logout(request: Request):
    # Build a redirect AND delete the cookie on the same response object
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

# --- Patient Routes ---

@app.get("/patients/", response_model=List[PatientRead], tags=["Patients"])
def list_patients(user: dict = Depends(require_auth)):
    return registry.list_all_patients()

@app.post("/patients/", response_model=PatientRead, tags=["Patients"])
def register_patient(patient: PatientCreate, user: dict = Depends(require_auth)):
    if registry.get_by_phone(patient.phone):
        raise HTTPException(status_code=409, detail="A patient with this phone number already exists")
    p = registry.register_patient(
        patient.name, patient.dob, patient.gender,
        patient.phone, patient.address, patient.blood_group
    )
    # Re-read the saved record so response fields (including created_at) have
    # the same serialized representation as every other patient endpoint.
    return registry.get_by_id(p.patient_id)

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

@app.get("/patients/phone/{phone}", response_model=PatientRead, tags=["Patients"])
def get_patient_by_phone(phone: str, user: dict = Depends(require_auth)):
    p = registry.get_by_phone(phone)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return p

# --- Doctor Routes ---

@app.get("/doctors/", response_model=List[DoctorRead], tags=["Doctors"])
def list_doctors(user: dict = Depends(require_auth)):
    docs = doc_manager.list_all_doctors()
    return [
        DoctorRead(
            doctor_id=d.doctor_id,
            name=d.name,
            department=d.department,
            specialization=d.specialization,
            available_from=d.available_from.strftime('%H:%M'),
            available_to=d.available_to.strftime('%H:%M')
        ) for d in docs
    ]

@app.post("/doctors/", response_model=DoctorRead, tags=["Doctors"])
def register_doctor(doctor: DoctorCreate, user: dict = Depends(require_auth)):
    start = time.fromisoformat(doctor.available_from)
    end = time.fromisoformat(doctor.available_to)
    d = doc_manager.register_doctor(doctor.name, doctor.department, doctor.specialization, start, end)
    return DoctorRead(
        doctor_id=d.doctor_id,
        name=d.name,
        department=d.department,
        specialization=d.specialization,
        available_from=d.available_from.strftime('%H:%M'),
        available_to=d.available_to.strftime('%H:%M')
    )

# --- Appointment Routes ---

@app.get("/appointments/", response_model=List[AppointmentRead], tags=["Appointments"])
def list_appointments(user: dict = Depends(require_auth)):
    """List all booked appointments."""
    from db.database import db
    rows = db.query("SELECT * FROM appointments ORDER BY start_time ASC")
    result = []
    for row in rows:
        result.append(AppointmentRead(
            appointment_id=row['appointment_id'],
            patient_id=row['patient_id'],
            doctor_id=row['doctor_id'],
            start_time=datetime.fromisoformat(row['start_time']),
            end_time=datetime.fromisoformat(row['end_time']),
            status=row['status'],
            priority=row['priority']
        ))
    return result

@app.post("/appointments/", response_model=AppointmentRead, tags=["Appointments"])
def book_appointment(apt_req: AppointmentCreate, user: dict = Depends(require_auth)):
    patient = registry.get_by_id(apt_req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = doc_manager.get_by_id(apt_req.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    apt = scheduler.book_appointment(patient, doctor, apt_req.start_time, apt_req.duration_minutes)
    if not apt:
        raise HTTPException(status_code=400, detail="Doctor unavailable at that time or slot overlaps an existing appointment")

    return AppointmentRead(
        appointment_id=apt.appointment_id,
        patient_id=apt.patient.patient_id,
        doctor_id=apt.doctor.doctor_id,
        start_time=apt.start_time,
        end_time=apt.end_time,
        status=apt.status,
        priority=apt.priority
    )

@app.patch("/appointments/{appointment_id}/cancel", tags=["Appointments"])
def cancel_appointment(appointment_id: int, user: dict = Depends(require_auth)):
    """Cancel an appointment by ID."""
    success = scheduler.cancel_appointment(appointment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": "Appointment cancelled"}

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
        )
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

# --- Reports ---

@app.get("/reports/financials", response_model=FinancialSummary, tags=["Reports"])
def get_financials(user: dict = Depends(require_auth)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        fin = reporting.get_financial_summary()
    except Exception:
        # bills table may not exist yet
        fin = {"total_billed": 0.0, "total_collected": 0.0, "outstanding": 0.0}
    return FinancialSummary(**fin)

@app.get("/reports/doctor-load", response_model=List[DoctorLoad], tags=["Reports"])
def get_doctor_load(user: dict = Depends(require_auth)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return reporting.get_doctor_load()

@app.get("/reports/department-footfall", response_model=List[DeptFootfall], tags=["Reports"])
def get_dept_footfall(user: dict = Depends(require_auth)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return reporting.get_departmental_footfall()
