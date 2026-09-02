from core.models import Patient, Doctor, Appointment
from core.queue_manager import QueueManager
from core.patient_registry import PatientRegistry
from core.scheduler import Scheduler
from core.doctor_manager import DoctorManager
from core.billing import BillingSystem
from core.reporting import ReportingSystem
from datetime import time, datetime, date
import os

def main():
    print("--- Hospital Registration System: Full Core & Billing Demo ---")

    # Initialize Components
    registry = PatientRegistry()
    doc_manager = DoctorManager()
    qm = QueueManager(registry)
    scheduler = Scheduler()
    billing = BillingSystem()
    reporting = ReportingSystem()

    # 1. Setup Indian Data
    print("\n--- Setting up Data ---")
    p1 = registry.get_by_phone("9876543210") or registry.register_patient("Aarav Sharma", "1990-01-01", "Male", "9876543210", "MG Road, Bangalore", "O+")
    p2 = registry.get_by_phone("9876543211") or registry.register_patient("Ishani Gupta", "1985-05-12", "Female", "9876543211", "Powai, Mumbai", "A-")

    # Register Doctors
    all_docs = doc_manager.list_all_doctors()
    dr_kapoor = next((d for d in all_docs if d.name == "Kapoor"), None)
    if not dr_kapoor:
        dr_kapoor = doc_manager.register_doctor("Kapoor", "Diagnostics", "Infectious Diseases", time(9, 0), time(17, 0))

    print(f"Using Doctor: {dr_kapoor.name} (ID: {dr_kapoor.doctor_id})")

    # 2. Demonstrate Appointment & Billing
    print("\n--- Testing Appointment & Billing ---")
    today = date.today()
    slot_start = datetime.combine(today, time(10, 0))

    # Book appointment
    apt = scheduler.book_appointment(p1, dr_kapoor, slot_start, 30)
    if apt:
        # Generate bill
        fee = billing.generate_bill(apt)
        # Simulate payment
        from db.database import db
        bill_row = db.query_one("SELECT bill_id FROM bills WHERE appointment_id = ?", (apt.appointment_id,))
        if bill_row:
            billing.mark_paid(bill_row['bill_id'])

    # 3. Demonstrate Admin Reporting
    print("\n--- Admin Reports ---")

    print("\nDoctor Load:")
    for load in reporting.get_doctor_load():
        print(f"Dr. {load['name']}: {load['appointment_count']} appointments")

    print("\nDepartmental Footfall:")
    for footfall in reporting.get_departmental_footfall():
        print(f"{footfall['department']}: {footfall['total_visits']} visits")

    fin = reporting.get_financial_summary()
    print(f"\nFinancial Summary:")
    print(f"Total Billed:    ₹{fin['total_billed']:.2f}")
    print(f"Total Collected:  ₹{fin['total_collected']:.2f}")
    print(f"Outstanding:     ₹{fin['outstanding']:.2f}")

    # 4. Demonstrate Queue
    print("\n--- Testing Queue ---")
    qm.add_patient(p1, 3) # Routine
    qm.add_patient(p2, 1) # Emergency

    print("\n--- Processing Queue ---")
    while not qm.is_empty():
        priority, patient = qm.pop_next_patient()
        print(f"Now seeing: {patient.name} | Priority: {priority}")

    print("\nDemo complete. Data is now saved in 'hospital_system.db'.")

if __name__ == "__main__":
    main()
