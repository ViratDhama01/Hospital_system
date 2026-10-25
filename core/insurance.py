from dataclasses import dataclass
from typing import Optional, List
from db.database import db

@dataclass
class InsurancePolicy:
    policy_id: Optional[int]
    patient_id: int
    provider_name: str
    policy_number: str
    coverage_details: str

class InsuranceManager:
    def add_policy(self, patient_id: int, provider: str, policy_num: str, coverage: str) -> int:
        query = "INSERT INTO insurance_policies (patient_id, provider_name, policy_number, coverage_details) VALUES (?, ?, ?, ?)"
        cursor = db.execute(query, (patient_id, provider, policy_num, coverage))
        return cursor.lastrowid

    def get_policy(self, patient_id: int) -> Optional[InsurancePolicy]:
        query = "SELECT * FROM insurance_policies WHERE patient_id = ? LIMIT 1"
        row = db.query_one(query, (patient_id,))
        if not row:
            return None
        return InsurancePolicy(
            policy_id=row['policy_id'],
            patient_id=row['patient_id'],
            provider_name=row['provider_name'],
            policy_number=row['policy_number'],
            coverage_details=row['coverage_details']
        )

    def verify_coverage(self, policy_id: int, amount: float) -> float:
        """
        Mocks an insurance verification call.
        Returns the amount covered by insurance.
        """
        # In a real system, this would call an external API.
        # Mock: Insurance covers 80% of the amount.
        return amount * 0.8

insurance_manager = InsuranceManager()
