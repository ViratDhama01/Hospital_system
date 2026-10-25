import heapq
from collections import deque
from datetime import datetime
from typing import List, Tuple, Optional

from .models import Patient
from db.database import db
from .notifications import notification_manager


class QueueManager:
    """FIFO service for routine patients plus a heap for urgent triage cases."""

    ROUTINE_PRIORITY = 5

    def __init__(self, patient_registry, notifier=None):
        self.registry = patient_registry
        self.notifier = notifier
        self._routine_queue = deque()  # FIFO: (arrival_time, patient_id, patient)
        self._urgent_heap = []  # min-heap: (priority, arrival_time, patient_id, patient)
        self._load_queue_from_db()

    @staticmethod
    def _arrival_key(value):
        if isinstance(value, datetime):
            return value.isoformat(sep=" ")
        return str(value)

    def _push(self, priority: int, arrival_time: str, patient: Patient):
        if priority == self.ROUTINE_PRIORITY:
            entry = (arrival_time, patient.patient_id, patient)
            insert_at = len(self._routine_queue)
            for index, queued in enumerate(self._routine_queue):
                if (queued[0], queued[1]) > (arrival_time, patient.patient_id):
                    insert_at = index
                    break
            self._routine_queue.insert(insert_at, entry)
        else:
            heapq.heappush(
                self._urgent_heap,
                (priority, arrival_time, patient.patient_id, patient),
            )

    def _remove(self, patient_id: int):
        for index, entry in enumerate(self._routine_queue):
            if entry[1] == patient_id:
                del self._routine_queue[index]
                return
        for index, entry in enumerate(self._urgent_heap):
            if entry[2] == patient_id:
                del self._urgent_heap[index]
                heapq.heapify(self._urgent_heap)
                return

    def _load_queue_from_db(self):
        """Restore both FIFO routine entries and urgent heap entries at startup."""
        rows = db.query(
            "SELECT patient_id, priority, arrival_time FROM walk_in_queue ORDER BY arrival_time ASC"
        )
        for row in rows:
            patient = self.registry.get_by_id(row["patient_id"])
            if patient:
                self._push(
                    int(row["priority"]),
                    self._arrival_key(row["arrival_time"]),
                    patient,
                )
        if self._routine_queue or self._urgent_heap:
            print(f"Loaded {len(self)} patients from persistent queue.")

    def add_patient(self, patient: Patient, priority: int):
        """Add or retriage a patient; same-priority patients retain arrival order."""
        existing = db.query_one(
            "SELECT priority, arrival_time FROM walk_in_queue WHERE patient_id = ? ORDER BY queue_id LIMIT 1",
            (patient.patient_id,),
        )
        if existing:
            arrival_time = self._arrival_key(existing["arrival_time"])
            self._remove(patient.patient_id)
            db.execute(
                "UPDATE walk_in_queue SET priority = ? WHERE patient_id = ?",
                (priority, patient.patient_id),
            )
            self._push(priority, arrival_time, patient)
            if self.notifier:
                self.notifier({"event": "queue_updated", "action": "update", "patient_id": patient.patient_id})
            return

        arrival_time = datetime.now().isoformat(sep=" ")
        db.execute(
            "INSERT INTO walk_in_queue (patient_id, priority, arrival_time) VALUES (?, ?, ?)",
            (patient.patient_id, priority, arrival_time),
        )
        self._push(priority, arrival_time, patient)
        if self.notifier:
            self.notifier({"event": "queue_updated", "action": "add", "patient_id": patient.patient_id})
        notification_manager.send_notification(
            patient.patient_id,
            f"You have been added to the queue. Your priority is {priority}.",
        )
        print(f"Added {patient.name} to the queue with priority {priority}.")

    def pop_next_patient(self) -> Optional[Tuple[int, Patient]]:
        """Serve the most urgent patient, or the oldest routine patient."""
        if self._urgent_heap:
            priority, arrival_time, patient_id, patient = heapq.heappop(self._urgent_heap)
        elif self._routine_queue:
            arrival_time, patient_id, patient = self._routine_queue.popleft()
            priority = self.ROUTINE_PRIORITY
        else:
            return None

        db.execute(
            "DELETE FROM walk_in_queue WHERE patient_id = ? AND priority = ? AND arrival_time = ?",
            (patient_id, priority, arrival_time),
        )
        if self.notifier:
            self.notifier({"event": "queue_updated", "action": "pop", "patient_id": patient_id})
        return priority, patient

    def peek_next_patient(self):
        """Return the next patient without removing them."""
        if self._urgent_heap:
            priority, _, _, patient = self._urgent_heap[0]
            return priority, patient
        if self._routine_queue:
            return self.ROUTINE_PRIORITY, self._routine_queue[0][2]
        return None

    def is_empty(self) -> bool:
        return not self._urgent_heap and not self._routine_queue

    def get_queue(self) -> List[Tuple[int, str, Patient]]:
        """Return a sorted snapshot while retaining FIFO order within priority."""
        entries = [
            (priority, arrival_time, patient_id, patient)
            for priority, arrival_time, patient_id, patient in self._urgent_heap
        ]
        entries.extend(
            (self.ROUTINE_PRIORITY, arrival_time, patient_id, patient)
            for arrival_time, patient_id, patient in self._routine_queue
        )
        entries.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
        return [(priority, arrival_time, patient) for priority, arrival_time, _, patient in entries]

    def __len__(self):
        return len(self._urgent_heap) + len(self._routine_queue)
