from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from db.database import db

@dataclass
class Prescription:
    prescription_id: Optional[int]
    patient_id: int
    doctor_id: int
    medication: str
    dosage: str
    frequency: str
    duration: str
    date_issued: datetime

class PrescriptionManager:
    def issue_prescription(self, patient_id: int, doctor_id: int, medication: str, dosage: str, frequency: str, duration: str) -> int:
        query = "INSERT INTO prescriptions (patient_id, doctor_id, medication, dosage, frequency, duration) VALUES (?, ?, ?, ?, ?, ?)"
        cursor = db.execute(query, (patient_id, doctor_id, medication, dosage, frequency, duration))
        return cursor.lastrowid

    def get_patient_prescriptions(self, patient_id: int) -> List[Prescription]:
        query = "SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY date_issued DESC"
        rows = db.query(query, (patient_id,))
        return [
            Prescription(
                prescription_id=row['prescription_id'],
                patient_id=row['patient_id'],
                doctor_id=row['doctor_id'],
                medication=row['medication'],
                dosage=row['dosage'],
                frequency=row['frequency'],
                duration=row['duration'],
                date_issued=datetime.fromisoformat(row['date_issued']) if isinstance(row['date_issued'], str) else row['date_issued']
            ) for row in rows
        ]

prescription_manager = PrescriptionManager()
