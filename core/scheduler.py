from datetime import datetime, timedelta, time
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

    def book_appointment(self, patient: Patient, doctor: Doctor, start_time: datetime, duration_minutes: int, category: str = "routine", current_time: Optional[datetime] = None) -> Optional[Appointment]:
        """
        Books an appointment if the doctor is available and the slot doesn't overlap.
        """
        # Appointment inputs from datetime-local are clinic wall-clock times;
        # normalize optional client offsets before comparing against clinic shifts.
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if duration_minutes <= 0:
            return None
        if category not in {"routine", "emergency"}:
            return None

        def as_datetime(value):
            parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed

        rows = db.query(
            "SELECT start_time, end_time FROM appointments "
            "WHERE doctor_id = ? AND status = 'booked'",
            (doctor.doctor_id,),
        )
        occupied = sorted(
            [(as_datetime(row["start_time"]), as_datetime(row["end_time"])) for row in rows],
            key=lambda slot: slot[0],
        )
        crosses_midnight = doctor.available_to <= doctor.available_from

        if category == "emergency":
            requested = max(start_time, (current_time or datetime.now()).replace(second=0, microsecond=0))
            first_shift_date = requested.date()
            if crosses_midnight and requested.time() < doctor.available_to:
                first_shift_date -= timedelta(days=1)
            for day_offset in range(61):
                shift_date = first_shift_date + timedelta(days=day_offset)
                shift_start = datetime.combine(shift_date, doctor.available_from)
                if day_offset == 0:
                    shift_start = max(shift_start, requested)
                shift_end_date = shift_date + (timedelta(days=1) if crosses_midnight else timedelta())
                shift_end = datetime.combine(shift_end_date, doctor.available_to)
                candidate = shift_start
                for existing_start, existing_end in occupied:
                    if existing_end <= candidate or existing_start >= shift_end:
                        continue
                    if candidate + timedelta(minutes=duration_minutes) <= existing_start:
                        break
                    if candidate < existing_end:
                        candidate = existing_end
                if candidate + timedelta(minutes=duration_minutes) <= shift_end:
                    start_time = candidate
                    break
            else:
                print(f"No emergency appointment slot is available for Dr. {doctor.name} in the next 60 days.")
                return None
        else:
            shift_date = start_time.date()
            if crosses_midnight and start_time.time() < doctor.available_to:
                shift_date -= timedelta(days=1)
            shift_start = datetime.combine(shift_date, doctor.available_from)
            shift_end_date = shift_date + (timedelta(days=1) if crosses_midnight else timedelta())
            shift_end = datetime.combine(shift_end_date, doctor.available_to)
            if start_time < shift_start or start_time + timedelta(minutes=duration_minutes) > shift_end:
                print(
                    f"Error: Requested slot is outside Dr. {doctor.name}'s availability "
                    f"({doctor.available_from} - {doctor.available_to})."
                )
                return None
            for existing_start, existing_end in occupied:
                if self._is_overlapping(start_time, start_time + timedelta(minutes=duration_minutes), existing_start, existing_end):
                    print(
                        f"Error: Dr. {doctor.name} is already booked from "
                        f"{existing_start.strftime('%H:%M')} to {existing_end.strftime('%H:%M')}."
                    )
                    return None

        end_time = start_time + timedelta(minutes=duration_minutes)
        priority = 1 if category == "emergency" else 5

        # 3. Book the appointment
        # To truly prevent race conditions in SQLite, we'd need a BEGIN IMMEDIATE transaction.
        # For now, the optimized SQL check significantly reduces the window.
        query = """
            INSERT INTO appointments (patient_id, doctor_id, start_time, end_time, priority, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = db.execute(query, (patient.patient_id, doctor.doctor_id, start_time.isoformat(), end_time.isoformat(), priority, category))
        appointment_id = cursor.lastrowid

        new_appointment = Appointment(
            appointment_id=appointment_id,
            patient=patient,
            doctor=doctor,
            start_time=start_time,
            end_time=end_time,
            priority=priority,
            category=category,
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
        """Returns all booked appointments for a specific doctor."""
        # Filter out cancelled appointments to keep the schedule clean
        rows = db.query("SELECT * FROM appointments WHERE doctor_id = ? AND status = 'booked'", (doctor_id,))

        appointments = []
        for row in rows:
            # Rebuild the Appointment object to maintain type safety
            # Note: This requires fetching Patient/Doctor if full objects are needed,
            # but for a schedule view, we usually just need the IDs and times.
            appointments.append(Appointment(
                appointment_id=row['appointment_id'],
                patient=None, # API layer can hydrate if needed
                doctor=None,
                start_time=datetime.fromisoformat(row['start_time']),
                end_time=datetime.fromisoformat(row['end_time'])
            ))
        return appointments

    def recommend_doctor_for_urgent_case(self) -> Optional[int]:
        """Choose the active doctor with the lightest booked appointment load."""
        row = db.query_one(
            "SELECT d.doctor_id, COUNT(a.appointment_id) AS booked_load "
            "FROM doctors d LEFT JOIN appointments a "
            "ON a.doctor_id = d.doctor_id AND a.status = 'booked' "
            "WHERE d.employment_status = 'active' "
            "GROUP BY d.doctor_id ORDER BY booked_load ASC, d.doctor_id ASC LIMIT 1"
        )
        return row["doctor_id"] if row else None
