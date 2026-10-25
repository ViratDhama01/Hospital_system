from typing import List, Dict
from db.database import db

class ReportingSystem:
    def __init__(self):
        pass

    def get_doctor_load(self) -> List[Dict]:
        """
        Calculates how many appointments each doctor has.
        """
        query = """
            SELECT d.name, COUNT(a.appointment_id) as appointment_count
            FROM doctors d
            LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
                AND a.status != 'cancelled'
            GROUP BY d.doctor_id
            ORDER BY appointment_count DESC
        """
        rows = db.query(query)
        return [dict(row) for row in rows]

    def get_departmental_footfall(self) -> List[Dict]:
        """
        Calculates the number of appointments per department.
        """
        query = """
            SELECT d.department, COUNT(a.appointment_id) as total_visits
            FROM doctors d
            JOIN appointments a ON d.doctor_id = a.doctor_id
                AND a.status != 'cancelled'
            GROUP BY d.department
            ORDER BY total_visits DESC
        """
        rows = db.query(query)
        return [dict(row) for row in rows]

    def get_financial_summary(self) -> Dict:
        """
        Returns total billed amount vs total collected revenue.
        """
        billed = db.query_one("SELECT SUM(amount) as total FROM bills")['total'] or 0.0
        collection_row = db.query_one(
            "SELECT SUM(CASE WHEN b.payment_status = 'paid' THEN b.amount "
            "ELSE COALESCE(p.amount_paid, 0) END) AS total "
            "FROM bills b LEFT JOIN (SELECT bill_id, SUM(amount) AS amount_paid "
            "FROM payments WHERE status = 'completed' GROUP BY bill_id) p ON p.bill_id = b.bill_id"
        )
        collected = collection_row['total'] or 0.0

        return {
            "total_billed": billed,
            "total_collected": collected,
            "outstanding": billed - collected
        }

    def get_peak_hours(self) -> List[Dict]:
        """
        Analyzes appointments to find the busiest hours of the day.
        """
        if db.engine == "postgres":
            hour_expression = "EXTRACT(HOUR FROM start_time)::int"
        else:
            hour_expression = "CAST(strftime('%H', start_time) AS INTEGER)"
        query = f"""
            SELECT {hour_expression} AS hour, COUNT(*) AS appointment_count
            FROM appointments
            WHERE status != 'cancelled'
            GROUP BY hour
            ORDER BY appointment_count DESC
        """
        return [dict(row) for row in db.query(query)]

    def get_patient_demographics(self) -> List[Dict]:
        """
        Analyzes patient gender distribution.
        """
        query = """
            SELECT gender, COUNT(*) as count
            FROM patients
            GROUP BY gender
        """
        rows = db.query(query)
        return [dict(row) for row in rows]
