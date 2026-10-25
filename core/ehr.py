from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List, Optional
from db.database import db

@dataclass
class HealthRecord:
    record_id: Optional[int]
    patient_id: int
    doctor_id: int
    note: str
    category: str
    created_at: datetime


@dataclass
class _HistoryNode:
    record: HealthRecord
    next: Optional["_HistoryNode"] = None


class PatientHistoryLinkedList:
    """Singly linked sequence for chronological traversal of one patient's EHR."""

    def __init__(self):
        self.head: Optional[_HistoryNode] = None
        self.tail: Optional[_HistoryNode] = None
        self.length = 0

    def append(self, record: HealthRecord):
        node = _HistoryNode(record)
        if self.tail:
            self.tail.next = node
        else:
            self.head = node
        self.tail = node
        self.length += 1

    def __iter__(self) -> Iterator[HealthRecord]:
        current = self.head
        while current:
            yield current.record
            current = current.next

    def __len__(self):
        return self.length

class EHRManager:
    def __init__(self):
        # Hash patient IDs to their linked histories for fast repeated access.
        self._histories_by_patient = {}

    def add_record(self, patient_id: int, doctor_id: int, note: str, category: str = "Consultation") -> int:
        query = "INSERT INTO health_records (patient_id, doctor_id, note, category) VALUES (?, ?, ?, ?)"
        cursor = db.execute(query, (patient_id, doctor_id, note, category))
        self._histories_by_patient.pop(patient_id, None)
        return cursor.lastrowid

    def get_patient_history(self, patient_id: int) -> List[HealthRecord]:
        cached_history = self._histories_by_patient.get(patient_id)
        if cached_history is not None:
            return list(cached_history)

        query = "SELECT * FROM health_records WHERE patient_id = ? ORDER BY created_at DESC"
        rows = db.query(query, (patient_id,))
        history = PatientHistoryLinkedList()
        for row in rows:
            history.append(HealthRecord(
                record_id=row['record_id'],
                patient_id=row['patient_id'],
                doctor_id=row['doctor_id'],
                note=row['note'],
                category=row['category'],
                created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at']
            ))
        self._histories_by_patient[patient_id] = history
        return list(history)

ehr_manager = EHRManager()
