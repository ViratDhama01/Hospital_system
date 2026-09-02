from typing import Dict
from .models import Patient, Doctor, Appointment
from db.database import db

class BillingSystem:
    def __init__(self):
        # Default consultation fees by department
        self.dept_fees = {
            "Diagnostics": 500,
            "Neurology": 800,
            "General Medicine": 300,
            "Cardiology": 700,
            "Pediatrics": 400
        }
        self._init_billing_table()

    def _init_billing_table(self):
        """Creates a simple bills table if it doesn't exist."""
        query = """
            CREATE TABLE IF NOT EXISTS bills (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_status TEXT DEFAULT 'unpaid',
                bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments (appointment_id)
            )
        """
        db.execute(query)

    def generate_bill(self, appointment: Appointment) -> float:
        """
        Calculates and records a bill for an appointment based on the doctor's department.
        """
        fee = self.dept_fees.get(appointment.doctor.department, 200) # Default 200 if dept not found

        query = "INSERT INTO bills (appointment_id, amount) VALUES (?, ?)"
        cursor = db.execute(query, (appointment.appointment_id, fee))

        print(f"Bill generated for {appointment.patient.name}: ₹{fee}")
        return fee

    def mark_paid(self, bill_id: int):
        """Marks a bill as paid."""
        query = "UPDATE bills SET payment_status = 'paid' WHERE bill_id = ?"
        db.execute(query, (bill_id,))
        print(f"Bill {bill_id} marked as paid.")

    def get_total_revenue(self) -> float:
        """Calculates total revenue from paid bills."""
        row = db.query_one("SELECT SUM(amount) as total FROM bills WHERE payment_status = 'paid'")
        return row['total'] if row['total'] else 0.0
