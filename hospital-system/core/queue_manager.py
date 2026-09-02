import heapq
from datetime import datetime
from typing import List, Tuple, Optional
from .models import Patient
from db.database import db

class QueueManager:
    def __init__(self, patient_registry):
        self.registry = patient_registry
        # The heap stores tuples of (priority, arrival_time, patient_id)
        self._queue = []
        self._load_queue_from_db()

    def _load_queue_from_db(self):
        """Loads existing walk-in queue from the database on startup."""
        rows = db.query("SELECT patient_id, priority, arrival_time FROM walk_in_queue ORDER BY arrival_time ASC")
        for row in rows:
            patient = self.registry.get_by_id(row['patient_id'])
            if patient:
                # arrival_time from DB is ISO string, we use it as the tie-breaker
                heapq.heappush(self._queue, (row['priority'], row['arrival_time'], patient))
        if self._queue:
            print(f"Loaded {len(self._queue)} patients from persistent queue.")

    def add_patient(self, patient: Patient, priority: int):
        """
        Adds a patient to the walk-in queue and persists it.
        :param patient: The Patient object.
        :param priority: Urgency level (1 = Highest, 5 = Lowest).
        """
        # A patient can have only one active walk-in entry.  Re-triage updates
        # their priority while preserving their original arrival time for fair
        # ordering among equal priorities.
        existing = db.query_one(
            "SELECT priority, arrival_time FROM walk_in_queue WHERE patient_id = ? ORDER BY queue_id LIMIT 1",
            (patient.patient_id,)
        )
        if existing:
            old_entry = (existing['priority'], existing['arrival_time'], patient)
            try:
                self._queue.remove(old_entry)
                heapq.heapify(self._queue)
            except ValueError:
                # Keep the database correct even if an in-memory entry was
                # removed by another request between the two operations.
                pass
            db.execute(
                "UPDATE walk_in_queue SET priority = ? WHERE patient_id = ?",
                (priority, patient.patient_id),
            )
            heapq.heappush(self._queue, (priority, existing['arrival_time'], patient))
            return

        arrival_time = datetime.now().isoformat()

        # Persist to DB
        query = "INSERT INTO walk_in_queue (patient_id, priority, arrival_time) VALUES (?, ?, ?)"
        db.execute(query, (patient.patient_id, priority, arrival_time))

        # Add to in-memory heap for fast O(log n) priority access
        heapq.heappush(self._queue, (priority, arrival_time, patient))
        print(f"Added {patient.name} to queue with priority {priority}.")

    def pop_next_patient(self) -> Optional[Tuple[int, Patient]]:
        """
        Retrieves the next patient and removes them from the DB.
        """
        if not self._queue:
            return None

        priority, arrival_time, patient = heapq.heappop(self._queue)

        # Remove from DB: find the specific entry for this patient with this priority/time
        # Since queue_id is PK, we could have stored it in the heap, but let's use the combined identity
        query = "DELETE FROM walk_in_queue WHERE patient_id = ? AND priority = ? AND arrival_time = ?"
        db.execute(query, (patient.patient_id, priority, arrival_time))

        return priority, patient

    def peek_next_patient(self):
        """Looks at the next patient without removing them."""
        if not self._queue:
            return None
        priority, _, patient = self._queue[0]
        return priority, patient

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def get_queue(self) -> List[Tuple[int, Patient]]:
        """Returns a sorted list of the queue without modifying it."""
        return sorted(self._queue)

    def __len__(self):
        return len(self._queue)
