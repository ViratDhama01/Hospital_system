from typing import Tuple, Dict
from db.database import db

class TriageAgent:
    """
    An AI Triage Agent that suggests a priority level based on patient symptoms.
    In a real system, this would use an LLM or a complex medical decision tree.
    """

    SYMPTOM_MAP = {
        "chest pain": 1,
        "difficulty breathing": 1,
        "severe bleeding": 1,
        "unconscious": 1,
        "high fever": 2,
        "severe pain": 2,
        "fracture": 2,
        "mild fever": 3,
        "cough": 3,
        "routine checkup": 5,
        "follow-up": 5,
    }

    def analyze_symptoms(self, symptoms: str) -> Tuple[int, str]:
        symptoms_lower = symptoms.lower()

        # Find the highest priority symptom
        suggested_priority = 5
        found_symptom = "General"

        for symptom, priority in self.SYMPTOM_MAP.items():
            if symptom in symptoms_lower:
                if priority < suggested_priority:
                    suggested_priority = priority
                    found_symptom = symptom

        return suggested_priority, found_symptom

    def triage_patient(self, patient_id: int, symptoms: str) -> int:
        priority, reason = self.analyze_symptoms(symptoms)

        # Log the triage result
        query = "INSERT INTO triage_logs (patient_id, symptoms, assigned_priority, agent_id) VALUES (?, ?, ?, ?)"
        db.execute(query, (patient_id, symptoms, priority, "AI-Triage-v1"))

        return priority

triage_agent = TriageAgent()
