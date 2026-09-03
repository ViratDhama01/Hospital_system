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
        collected = db.query_one("SELECT SUM(amount) as total FROM bills WHERE payment_status = 'paid'")['total'] or 0.0

        return {
            "total_billed": billed,
            "total_collected": collected,
            "outstanding": billed - collected
        }
