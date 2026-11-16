from typing import Dict, Tuple
from .models import Patient, Doctor, Appointment
from db.database import db
from .insurance import insurance_manager
from .payments import payment_manager

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
        from db.database import db

        # PostgreSQL doesn't use AUTOINCREMENT. We use SERIAL or just omit it for PRIMARY KEY.
        if db.engine == "postgres":
            pk_syntax = "SERIAL PRIMARY KEY"
        else:
            pk_syntax = "INTEGER PRIMARY KEY AUTOINCREMENT"

        query = f"""
            CREATE TABLE IF NOT EXISTS bills (
                bill_id {pk_syntax},
                appointment_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_status TEXT DEFAULT 'unpaid',
                bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments (appointment_id)
            )
        """
        db.execute(query)

    def generate_bill(self, appointment: Appointment) -> Tuple[float, float]:
        """
        Calculates and records a bill for an appointment.
        Returns (total_amount, patient_share).
        """
        total_fee = self.dept_fees.get(appointment.doctor.department, 200)

        # Check for insurance
        patient_share = total_fee
        insurance_share = 0.0

        policy = insurance_manager.get_policy(appointment.patient.patient_id)
        if policy:
            insurance_share = insurance_manager.verify_coverage(policy.policy_id, total_fee)
            patient_share = total_fee - insurance_share

        query = "INSERT INTO bills (appointment_id, amount) VALUES (?, ?)"
        cursor = db.execute(query, (appointment.appointment_id, total_fee))

        print(f"Bill generated for {appointment.patient.name}: Total ₹{total_fee}, Patient Share ₹{patient_share}, Insurance ₹{insurance_share}")
        return total_fee, patient_share

    def process_patient_payment(self, bill_id: int, amount: float, method: str):
        """Processes a payment and updates bill status if fully paid."""
        payment = payment_manager.process_payment(bill_id, amount, method)
        if not payment:
            return False

        if payment.status == "processing":
            db.execute("UPDATE bills SET payment_status = 'processing' WHERE bill_id = ?", (bill_id,))
            return True

        # Check if bill is now fully paid
        row = db.query_one("SELECT amount FROM bills WHERE bill_id = ?", (bill_id,))
        total_due = row['amount']

        # Sum all payments for this bill
        payments_rows = db.query(
            "SELECT amount FROM payments WHERE bill_id = ? AND status = 'completed'",
            (bill_id,),
        )
        total_paid = sum(p['amount'] for p in payments_rows)

        if round(total_due - total_paid, 2) <= 0:
            self.mark_paid(bill_id)
        else:
            db.execute("UPDATE bills SET payment_status = 'unpaid' WHERE bill_id = ?", (bill_id,))

        return True

    def mark_paid(self, bill_id: int):
        """Marks a bill as paid."""
        query = "UPDATE bills SET payment_status = 'paid' WHERE bill_id = ?"
        db.execute(query, (bill_id,))
        print(f"Bill {bill_id} marked as paid.")

    def get_total_revenue(self) -> float:
        """Calculates total revenue from paid bills."""
        row = db.query_one("SELECT SUM(amount) as total FROM bills WHERE payment_status = 'paid'")
        return row['total'] if row['total'] else 0.0
