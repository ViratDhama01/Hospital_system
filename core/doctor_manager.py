from typing import Optional, List
from .models import Doctor
from db.database import db

class DoctorManager:
    def __init__(self):
        # Persistence is now handled by db.py
        pass

    def register_doctor(self, name: str, department: str, specialization: str, available_from: any, available_to: any) -> Doctor:
        """
        Registers a new doctor in the system.
        """
        # Convert time objects to string for storage
        from_str = available_from.strftime('%H:%M') if hasattr(available_from, 'strftime') else str(available_from)
        to_str = available_to.strftime('%H:%M') if hasattr(available_to, 'strftime') else str(available_to)

        query = """
            INSERT INTO doctors (name, department, specialization, available_from, available_to)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = db.execute(query, (name, department, specialization, from_str, to_str))
        doctor_id = cursor.lastrowid

        from datetime import time
        return Doctor(
            doctor_id=doctor_id,
            name=name,
            department=department,
            specialization=specialization,
            available_from=time.fromisoformat(from_str),
            available_to=time.fromisoformat(to_str)
        )

    def get_by_id(self, doctor_id: int) -> Optional[Doctor]:
        """O(1) lookup by doctor ID."""
        row = db.query_one("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,))
        if row:
            from datetime import time
            d = dict(row)
            return Doctor(
                doctor_id=d['doctor_id'],
                name=d['name'],
                department=d['department'],
                specialization=d['specialization'],
                available_from=time.fromisoformat(d['available_from']),
                available_to=time.fromisoformat(d['available_to'])
            )
        return None

    def get_doctors_by_department(self, department: str) -> List[Doctor]:
        """Returns all doctors in a specific department."""
        from datetime import time
        rows = db.query("SELECT * FROM doctors WHERE department = ?", (department,))
        return [
            Doctor(
                doctor_id=r['doctor_id'],
                name=r['name'],
                department=r['department'],
                specialization=r['specialization'],
                available_from=time.fromisoformat(r['available_from']),
                available_to=time.fromisoformat(r['available_to'])
            ) for r in rows
        ]

    def get_doctors_by_specialization(self, specialization: str) -> List[Doctor]:
        """Returns all doctors with a specific specialization."""
        from datetime import time
        rows = db.query("SELECT * FROM doctors WHERE specialization = ?", (specialization,))
        return [
            Doctor(
                doctor_id=r['doctor_id'],
                name=r['name'],
                department=r['department'],
                specialization=r['specialization'],
                available_from=time.fromisoformat(r['available_from']),
                available_to=time.fromisoformat(r['available_to'])
            ) for r in rows
        ]

    def update_doctor(self, doctor_id: int, **kwargs) -> bool:
        """
        Updates doctor details.
        """
        doctor = self.get_by_id(doctor_id)
        if not doctor:
            return False

        fields = []
        values = []
        for key, value in kwargs.items():
            if hasattr(doctor, key):
                if key in ['available_from', 'available_to']:
                    value = value.strftime('%H:%M') if hasattr(value, 'strftime') else str(value)
                fields.append(f"{key} = ?")
                values.append(value)

        if not fields:
            return False

        values.append(doctor_id)
        query = f"UPDATE doctors SET {', '.join(fields)} WHERE doctor_id = ?"
        db.execute(query, tuple(values))
        return True

    def list_all_doctors(self) -> List[Doctor]:
        """Returns a list of all registered doctors."""
        from datetime import time
        rows = db.query("SELECT * FROM doctors")
        return [
            Doctor(
                doctor_id=r['doctor_id'],
                name=r['name'],
                department=r['department'],
                specialization=r['specialization'],
                available_from=time.fromisoformat(r['available_from']),
                available_to=time.fromisoformat(r['available_to'])
            ) for r in rows
        ]
