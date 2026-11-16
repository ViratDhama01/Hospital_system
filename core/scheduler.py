from datetime import datetime, timedelta, time
from typing import List, Optional
from .models import Patient, Doctor, Appointment, SlotOutsideAvailabilityError, SlotOverlapError, PastAppointmentError
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
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if duration_minutes <= 0:
            return None
        if category not in {"routine", "emergency"}:
            return None

        # Prevent routine appointments in the past
        print(f"DEBUG: category={category}, current_time={current_time}, start_time={start_time}")
        if category == "routine" and current_time and start_time < current_time:
            print("DEBUG: Past appointment detected!")
            raise PastAppointmentError(f"Cannot book routine appointment for {start_time} (current time: {current_time})")

        def as_datetime(value):
            parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed

        with db.write_transaction():
            if db.engine == "postgres":
                # Serialize bookings for this doctor even when no appointments exist yet.
                db.query_one(
                    "SELECT doctor_id FROM doctors WHERE doctor_id = ? FOR NO KEY UPDATE",
                    (doctor.doctor_id,),
                )
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
                    raise SlotOutsideAvailabilityError(f"No emergency slot available for Dr. {doctor.name} in next 60 days")
            else:
                shift_date = start_time.date()
                if crosses_midnight and start_time.time() < doctor.available_to:
                    shift_date -= timedelta(days=1)
                shift_start = datetime.combine(shift_date, doctor.available_from)
                shift_end_date = shift_date + (timedelta(days=1) if crosses_midnight else timedelta())
                shift_end = datetime.combine(shift_end_date, doctor.available_to)
                if start_time < shift_start or start_time + timedelta(minutes=duration_minutes) > shift_end:
                    raise SlotOutsideAvailabilityError(f"Requested slot is outside Dr. {doctor.name}'s availability")
                for existing_start, existing_end in occupied:
                    if self._is_overlapping(start_time, start_time + timedelta(minutes=duration_minutes), existing_start, existing_end):
                        raise SlotOverlapError(f"Dr. {doctor.name} is already booked from {existing_start.strftime('%H:%M')} to {existing_end.strftime('%H:%M')}")

            end_time = start_time + timedelta(minutes=duration_minutes)
            priority = 1 if category == "emergency" else 5

            query = """
                INSERT INTO appointments (patient_id, doctor_id, start_time, end_time, priority, category)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor = db.execute(query, (patient.patient_id, doctor.doctor_id, start_time.isoformat(), end_time.isoformat(), priority, category))
            appointment_id = cursor.lastrowid

            return Appointment(
                appointment_id=appointment_id,
                patient=patient,
                doctor=doctor,
                start_time=start_time,
                end_time=end_time,
                priority=priority,
                category=category,
            )
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
        rows = db.query("SELECT * FROM appointments WHERE doctor_id = ? AND status = 'booked'", (doctor_id,))

        appointments = []
        for row in rows:
            appointments.append(Appointment(
                appointment_id=row['appointment_id'],
                patient=None,
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
