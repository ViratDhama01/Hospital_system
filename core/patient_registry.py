from typing import Optional, List
from .models import Patient
from db.database import db

class PatientRegistry:
    def __init__(self):
        # Persistence is now handled by db.py, so we don't need in-memory dicts
        pass

    def register_patient(self, name: str, dob: str, gender: str, phone: str, address: str, blood_group: str) -> Patient:
        """
        Registers a new patient. If the phone already exists, it returns the existing patient.
        """
        # Check for existing patient by phone
        existing = self.get_by_phone(phone)
        if existing:
            print(f"Patient with phone {phone} already exists. Returning existing record.")
            return existing

        # Insert into DB
        query = """
            INSERT INTO patients (name, dob, gender, phone, address, blood_group)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = db.execute(query, (name, dob, gender, phone, address, blood_group))
        patient_id = cursor.lastrowid

        return Patient(
            patient_id=patient_id,
            name=name,
            dob=dob,
            gender=gender,
            phone=phone,
            address=address,
            blood_group=blood_group
        )

    def get_by_id(self, patient_id: int) -> Optional[Patient]:
        """O(1) lookup by patient ID via SQL Index."""
        row = db.query_one("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
        if row:
            return Patient(**dict(row))
        return None

    def get_by_phone(self, phone: str) -> Optional[Patient]:
        """O(1) lookup by phone number via SQL Index."""
        row = db.query_one("SELECT * FROM patients WHERE phone = ?", (phone,))
        if row:
            return Patient(**dict(row))
        return None

    def update_patient(self, patient_id: int, **kwargs) -> bool:
        """
        Updates patient fields.
        """
        patient = self.get_by_id(patient_id)
        if not patient:
            return False

        # Handle phone update separately to check for uniqueness
        if 'phone' in kwargs:
            new_phone = kwargs['phone']
            if new_phone != patient.phone:
                existing = self.get_by_phone(new_phone)
                if existing and existing.patient_id != patient_id:
                    print("Update failed: New phone number is already registered to another patient.")
                    return False

        # Build dynamic update query
        fields = []
        values = []
        for key, value in kwargs.items():
            if hasattr(patient, key):
                fields.append(f"{key} = ?")
                values.append(value)

        if not fields:
            return False

        values.append(patient_id)
        query = f"UPDATE patients SET {', '.join(fields)} WHERE patient_id = ?"
        db.execute(query, tuple(values))
        return True

    def list_all_patients(self) -> List[Patient]:
        """Returns a list of all registered patients."""
        rows = db.query("SELECT * FROM patients")
        return [Patient(**dict(row)) for row in rows]
