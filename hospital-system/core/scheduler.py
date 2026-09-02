from datetime import datetime, timedelta
from typing import List, Optional
from .models import Patient, Doctor, Appointment
from db.database import db

class Scheduler:
    def __init__(self):
        # Persistence is now handled by db.py
        pass

    def _is_overlapping(self, start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        """
        Checks if two time intervals overlap.
        """
        return start1 < end2 and start2 < end1

    def book_appointment(self, patient: Patient, doctor: Doctor, start_time: datetime, duration_minutes: int) -> Optional[Appointment]:
        """
        Books an appointment if the doctor is available and the slot doesn't overlap.
        """
        end_time = start_time + timedelta(minutes=duration_minutes)

        # 1. Verify appointment is within doctor's available shift hours
        shift_start = datetime.combine(start_time.date(), doctor.available_from)
        shift_end = datetime.combine(start_time.date(), doctor.available_to)

        if start_time < shift_start or end_time > shift_end:
            print(f"Error: Requested slot is outside Dr. {doctor.name}'s availability ({doctor.available_from} - {doctor.available_to}).")
            return None

        # 2. Check for overlaps with existing appointments for this doctor
        # Use a broad query and filter in Python to avoid SQLite date formatting issues
        query = "SELECT * FROM appointments WHERE doctor_id = ? AND status = 'booked'"
        rows = db.query(query, (doctor.doctor_id,))

        for row in rows:
            apt_start = datetime.fromisoformat(row['start_time'])
            apt_end = datetime.fromisoformat(row['end_time'])
            if self._is_overlapping(start_time, end_time, apt_start, apt_end):
                print(f"Error: Dr. {doctor.name} is already booked from {apt_start.strftime('%H:%M')} to {apt_end.strftime('%H:%M')}.")
                return None

        # 3. Book the appointment
        query = """
            INSERT INTO appointments (patient_id, doctor_id, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """
        cursor = db.execute(query, (patient.patient_id, doctor.doctor_id, start_time.isoformat(), end_time.isoformat()))
        appointment_id = cursor.lastrowid

        new_appointment = Appointment(
            appointment_id=appointment_id,
            patient=patient,
            doctor=doctor,
            start_time=start_time,
            end_time=end_time
        )

        print(f"Successfully booked: {patient.name} with Dr. {doctor.name} at {start_time.strftime('%H:%M')}")
        return new_appointment

    def cancel_appointment(self, appointment_id: int) -> bool:
        """Cancels an appointment by ID."""
        query = "UPDATE appointments SET status = 'cancelled' WHERE appointment_id = ?"
        cursor = db.execute(query, (appointment_id,))
        if cursor.rowcount > 0:
            print(f"Appointment {appointment_id} cancelled.")
            return True
        print(f"Error: Appointment {appointment_id} not found.")
        return False

    def get_doctor_schedule(self, doctor_id: int) -> List[Appointment]:
        """Returns all appointments for a specific doctor."""
        rows = db.query("SELECT * FROM appointments WHERE doctor_id = ?", (doctor_id,))
        # This would require joining with patients and doctors tables to rebuild full Appointment objects
        # For now, we return the raw rows or minimal objects
        return rows
