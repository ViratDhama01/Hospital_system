from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from db.database import db

@dataclass
class Payment:
    payment_id: Optional[int]
    bill_id: int
    amount: float
    payment_method: str
    transaction_id: str
    status: str
    timestamp: datetime

class PaymentManager:
    def process_payment(self, bill_id: int, amount: float, method: str) -> Optional[Payment]:
        """
        Processes a payment through a mock gateway.
        """
        # Mock: Transaction ID generation
        import uuid
        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"

        # Persist payment
        query = "INSERT INTO payments (bill_id, amount, payment_method, transaction_id, status) VALUES (?, ?, ?, ?, ?)"
        payment_status = "completed" if method == "Cash" else "processing"
        cursor = db.execute(query, (bill_id, amount, method, transaction_id, payment_status))

        payment_id = cursor.lastrowid

        return Payment(
            payment_id=payment_id,
            bill_id=bill_id,
            amount=amount,
            payment_method=method,
            transaction_id=transaction_id,
            status=payment_status,
            timestamp=datetime.now()
        )

payment_manager = PaymentManager()
