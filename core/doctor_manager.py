from dataclasses import replace
from typing import Optional, List

from .models import Doctor
from db.database import db


class DoctorManager:
    def __init__(self):
        # A dictionary is a hash table keyed by doctor ID for repeated exact lookups.
        self._doctors_by_id = {}

    @staticmethod
    def _doctor_from_row(row) -> Doctor:
        from datetime import time
        data = dict(row)
        return Doctor(
            doctor_id=data["doctor_id"],
            name=data["name"],
            department=data["department"],
            specialization=data["specialization"],
            available_from=time.fromisoformat(data["available_from"]),
            available_to=time.fromisoformat(data["available_to"]),
            employment_status=data.get("employment_status", "active"),
            status_reason=data.get("status_reason"),
            status_updated_at=data.get("status_updated_at"),
        )

    def _cache_doctor(self, doctor: Doctor) -> Doctor:
        self._doctors_by_id[doctor.doctor_id] = doctor
        return doctor

    def register_doctor(self, name: str, department: str, specialization: str, available_from: any, available_to: any) -> Doctor:
        """Register a doctor and add them to the ID hash table."""
        from_str = available_from.strftime("%H:%M") if hasattr(available_from, "strftime") else str(available_from)
        to_str = available_to.strftime("%H:%M") if hasattr(available_to, "strftime") else str(available_to)
        cursor = db.execute(
            "INSERT INTO doctors (name, department, specialization, available_from, available_to) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, department, specialization, from_str, to_str),
        )
        from datetime import time
        return self._cache_doctor(Doctor(
            doctor_id=cursor.lastrowid,
            name=name,
            department=department,
            specialization=specialization,
            available_from=time.fromisoformat(from_str),
            available_to=time.fromisoformat(to_str),
        ))

    def get_by_id(self, doctor_id: int) -> Optional[Doctor]:
        """Use the doctor ID hash table before querying persistent storage."""
        if doctor_id in self._doctors_by_id:
            return self._doctors_by_id[doctor_id]
        row = db.query_one("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,))
        return self._cache_doctor(self._doctor_from_row(row)) if row else None

    def get_doctors_by_department(self, department: str) -> List[Doctor]:
        rows = db.query(
            "SELECT * FROM doctors WHERE department = ? AND employment_status = 'active'",
            (department,),
        )
        return [self._cache_doctor(self._doctor_from_row(row)) for row in rows]

    def get_doctors_by_specialization(self, specialization: str) -> List[Doctor]:
        rows = db.query(
            "SELECT * FROM doctors WHERE specialization = ? AND employment_status = 'active'",
            (specialization,),
        )
        return [self._cache_doctor(self._doctor_from_row(row)) for row in rows]

    def update_doctor(self, doctor_id: int, **kwargs) -> bool:
        doctor = self.get_by_id(doctor_id)
        if not doctor:
            return False
        editable_fields = {"name", "department", "specialization", "available_from", "available_to"}
        updates = {key: value for key, value in kwargs.items() if key in editable_fields}
        if not updates:
            return False

        values = []
        fields = []
        normalized_updates = {}
        for key, value in updates.items():
            if key in {"available_from", "available_to"}:
                value = value.strftime("%H:%M") if hasattr(value, "strftime") else str(value)
                from datetime import time
                normalized_updates[key] = time.fromisoformat(value)
            else:
                normalized_updates[key] = value
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(doctor_id)
        db.execute(f"UPDATE doctors SET {', '.join(fields)} WHERE doctor_id = ?", tuple(values))
        self._cache_doctor(replace(doctor, **normalized_updates))
        return True

    def list_all_doctors(self, status: str = "active") -> List[Doctor]:
        """List active doctors, archived doctors, or the complete directory."""
        if status == "active":
            rows = db.query("SELECT * FROM doctors WHERE employment_status = 'active' ORDER BY doctor_id DESC")
        elif status == "archived":
            rows = db.query("SELECT * FROM doctors WHERE employment_status != 'active' ORDER BY status_updated_at DESC")
        elif status == "all":
            rows = db.query("SELECT * FROM doctors ORDER BY doctor_id DESC")
        else:
            raise ValueError("status must be 'active', 'archived', or 'all'")
        return [self._cache_doctor(self._doctor_from_row(row)) for row in rows]

    def update_employment_status(self, doctor_id: int, status: str) -> bool:
        """Archive or restore a doctor while preserving appointment history."""
        if status not in {"active", "suspended", "resigned", "duplicate"}:
            raise ValueError("Unsupported doctor employment status")
        doctor = self.get_by_id(doctor_id)
        if not doctor:
            return False
        result = db.execute(
            "UPDATE doctors SET employment_status = ?, status_reason = ?, "
            "status_updated_at = CURRENT_TIMESTAMP WHERE doctor_id = ?",
            (status, None if status == "active" else status, doctor_id),
        )
        if result.rowcount > 0:
            updated = db.query_one("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,))
            if updated:
                self._cache_doctor(self._doctor_from_row(updated))
            return True
        return False
