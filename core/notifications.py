from typing import Optional
from datetime import datetime
from db.database import db

class NotificationManager:
    def send_notification(self, patient_id: int, message: str, channel: str = "email"):
        """
        Sends a notification to the patient.
        In a real system, this would integrate with Twilio (SMS) or SendGrid (Email).
        """
        # Persist the notification
        query = "INSERT INTO notifications (patient_id, message, channel, status) VALUES (?, ?, ?, ?)"
        db.execute(query, (patient_id, message, channel, "sent"))

        # Mocking the actual delivery
        print(f"[MOCK NOTIFICATION] Sending {channel} to Patient {patient_id}: {message}")
        return True

notification_manager = NotificationManager()
