from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from db.database import db

@dataclass
class LabResult:
    lab_id: Optional[int]
    patient_id: int
    test_name: str
    result_value: str
    unit: str
    status: str
    date_performed: datetime

class LabManager:
    def add_result(self, patient_id: int, test_name: str, result_value: str, unit: str, status: str = "final") -> int:
        query = "INSERT INTO lab_results (patient_id, test_name, result_value, unit, status) VALUES (?, ?, ?, ?, ?)"
        cursor = db.execute(query, (patient_id, test_name, result_value, unit, status))
        return cursor.lastrowid

    def get_patient_labs(self, patient_id: int) -> List[LabResult]:
        query = "SELECT * FROM lab_results WHERE patient_id = ? ORDER BY date_performed DESC"
        rows = db.query(query, (patient_id,))
        return [
            LabResult(
                lab_id=row['lab_id'],
                patient_id=row['patient_id'],
                test_name=row['test_name'],
                result_value=row['result_value'],
                unit=row['unit'],
                status=row['status'],
                date_performed=datetime.fromisoformat(row['date_performed']) if isinstance(row['date_performed'], str) else row['date_performed']
            ) for row in rows
        ]

lab_manager = LabManager()
