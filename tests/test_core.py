import unittest
import os
from core.patient_registry import PatientRegistry
from core.queue_manager import QueueManager
from core.models import Patient
from db.database import db

class TestHospitalCore(unittest.TestCase):
    def setUp(self):
        # Clear tables before each test to ensure isolation
        db.execute("DELETE FROM walk_in_queue")
        db.execute("DELETE FROM patients")

    def test_patient_registration(self):
        registry = PatientRegistry()
        p = registry.register_patient("Test User", "1990-01-01", "Male", "1234567890", "Test Address", "O+")
        self.assertIsNotNone(p.patient_id)
        self.assertEqual(p.name, "Test User")

        # Test duplicate phone: should return the existing patient
        p_dup = registry.register_patient("Other User", "1990-01-01", "Male", "1234567890", "Other Address", "O+")
        self.assertEqual(p_dup.patient_id, p.patient_id)

    def test_queue_priority(self):
        registry = PatientRegistry()
        qm = QueueManager(registry)

        p1 = registry.register_patient("P1", "1990-01-01", "Male", "111", "Add 1", "O+")
        p2 = registry.register_patient("P2", "1990-01-01", "Male", "222", "Add 2", "O+")

        # P1: Routine (Priority 3), P2: Emergency (Priority 1)
        qm.add_patient(p1, 3)
        qm.add_patient(p2, 1)

        priority, next_patient = qm.pop_next_patient()
        self.assertEqual(priority, 1)
        self.assertEqual(next_patient.name, "P2")

if __name__ == "__main__":
    unittest.main()
