import re
from dataclasses import replace
from typing import Optional, List

from .models import Patient
from db.database import db


class PatientRegistry:
    def __init__(self):
        # Hash maps keep repeated ID and phone lookups O(1) within this process.
        # PostgreSQL remains the source of truth; successful writes refresh these maps.
        self._patients_by_id = {}
        self._patients_by_phone = {}

    def _normalize_phone(self, phone: str) -> str:
        """Strip non-numeric characters so phone lookups use a stable hash key."""
        return re.sub(r"\D", "", phone)

    def _cache_patient(self, patient: Patient) -> Patient:
        previous = self._patients_by_id.get(patient.patient_id)
        if previous and previous.phone != patient.phone:
            self._patients_by_phone.pop(previous.phone, None)
        self._patients_by_id[patient.patient_id] = patient
        self._patients_by_phone[patient.phone] = patient
        return patient

    @staticmethod
    def _patient_from_row(row) -> Patient:
        return Patient(**dict(row))

    def register_patient(self, name: str, dob: str, gender: str, phone: str, address: str, blood_group: str) -> Patient:
        """Register a patient, returning the existing record for a duplicate phone."""
        normalized_phone = self._normalize_phone(phone)
        existing = self.get_by_phone(normalized_phone)
        if existing:
            print(f"Patient with phone {normalized_phone} already exists. Returning existing record.")
            return existing

        query = """
            INSERT INTO patients (name, dob, gender, phone, address, blood_group)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = db.execute(query, (name, dob, gender, normalized_phone, address, blood_group))
        return self._cache_patient(Patient(
            patient_id=cursor.lastrowid,
            name=name,
            dob=dob,
            gender=gender,
            phone=normalized_phone,
            address=address,
            blood_group=blood_group,
        ))

    def get_by_id(self, patient_id: int) -> Optional[Patient]:
        """Use the hash index first, then hydrate the index from PostgreSQL on a miss."""
        if patient_id in self._patients_by_id:
            return self._patients_by_id[patient_id]
        row = db.query_one("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
        return self._cache_patient(self._patient_from_row(row)) if row else None

    def get_by_phone(self, phone: str) -> Optional[Patient]:
        normalized_phone = self._normalize_phone(phone)
        if normalized_phone in self._patients_by_phone:
            return self._patients_by_phone[normalized_phone]
        row = db.query_one("SELECT * FROM patients WHERE phone = ?", (normalized_phone,))
        return self._cache_patient(self._patient_from_row(row)) if row else None

    def update_patient(self, patient_id: int, **kwargs) -> bool:
        patient = self.get_by_id(patient_id)
        if not patient or patient.archived_at:
            return False

        editable_fields = {"name", "dob", "gender", "phone", "address", "blood_group"}
        updates = {key: value for key, value in kwargs.items() if key in editable_fields}
        if "phone" in updates:
            normalized_phone = self._normalize_phone(updates["phone"])
            if normalized_phone != patient.phone:
                existing = self.get_by_phone(normalized_phone)
                if existing and existing.patient_id != patient_id:
                    return False
            updates["phone"] = normalized_phone
        if not updates:
            return False

        fields = [f"{field} = ?" for field in updates]
        values = [*updates.values(), patient_id]
        result = db.execute(f"UPDATE patients SET {', '.join(fields)} WHERE patient_id = ? AND archived_at IS NULL", tuple(values))
        if not result.rowcount:
            return False
        self._cache_patient(replace(patient, **updates))
        return True

    def list_all_patients(self, status: str = "active") -> List[Patient]:
        """List patients for the selected registry view and refresh the hash maps."""
        if status == "active":
            rows = db.query("SELECT * FROM patients WHERE is_cured = 0 AND archived_at IS NULL ORDER BY patient_id DESC")
        elif status == "cured":
            rows = db.query("SELECT * FROM patients WHERE is_cured = 1 AND archived_at IS NULL ORDER BY cured_at DESC")
        elif status == "all":
            rows = db.query("SELECT * FROM patients WHERE archived_at IS NULL ORDER BY patient_id DESC")
        elif status == "archived":
            rows = db.query("SELECT * FROM patients WHERE archived_at IS NOT NULL ORDER BY archived_at DESC")
        else:
            raise ValueError("Unknown patient registry status")
        return [self._cache_patient(self._patient_from_row(row)) for row in rows]

    def set_cured(self, patient_id: int, cured: bool, changed_by: int) -> Optional[Patient]:
        """Move a patient between the active registry and cured history."""
        timestamp = "CURRENT_TIMESTAMP" if cured else "NULL"
        with db.write_transaction():
            result = db.execute(
                f"UPDATE patients SET is_cured = ?, cured_at = {timestamp} "
                "WHERE patient_id = ? AND archived_at IS NULL AND is_cured <> ?",
                (int(cured), patient_id, int(cured)),
            )
            if result.rowcount:
                self._log_status_change(patient_id, changed_by, "cured" if cured else "reactivated")
            row = db.query_one("SELECT * FROM patients WHERE patient_id = ? AND archived_at IS NULL", (patient_id,))
        return self._cache_patient(self._patient_from_row(row)) if row else None

    def set_archived(self, patient_id: int, archived: bool, changed_by: int) -> Optional[Patient]:
        """Remove a patient from the working registry or restore their original status."""
        timestamp = "CURRENT_TIMESTAMP" if archived else "NULL"
        condition = "IS NULL" if archived else "IS NOT NULL"
        with db.write_transaction():
            result = db.execute(
                f"UPDATE patients SET archived_at = {timestamp} WHERE patient_id = ? AND archived_at {condition}",
                (patient_id,),
            )
            if result.rowcount:
                self._log_status_change(patient_id, changed_by, "archived" if archived else "unarchived")
                if archived:
                    db.execute("DELETE FROM walk_in_queue WHERE patient_id = ?", (patient_id,))
            row = db.query_one("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
        return self._cache_patient(self._patient_from_row(row)) if row else None

    @staticmethod
    def _log_status_change(patient_id: int, changed_by: int, action: str):
        db.execute(
            "INSERT INTO patient_status_events (patient_id, changed_by, action) VALUES (?, ?, ?)",
            (patient_id, changed_by, action),
        )
