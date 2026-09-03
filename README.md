# Hospital Management System
1. **Patient registration & records** — create/search/update patient profiles (demographics, medical history, ID proof)
2. **Appointment & queue management** — book, reschedule, cancel; manage walk-in queues per department
3. **Doctor/department management** — availability, specialization, schedules
4. **Billing & insurance** — consultation fees, tests, packages, insurance claims
5. **Admin/reporting** — occupancy, daily footfall, doctor load, revenue

## 2. Architecture

| Stage | What you build | Tech |
|---|---|---|
| Stage 1 | Pure Python, in-memory (lists/dicts), terminal menu | Python only |
| Stage 2 | Add persistence | SQLite + `sqlite3` |
| Stage 3 | Add a real API | FastAPI |
| Stage 4 | Add a UI | React (or just Jinja2 templates first — simpler) |
| Stage 5 | Add AI features | scikit-learn / Ollama / a hosted LLM API |

folder structure
```
hospital-system/
├── core/
│   ├── models.py          # Patient, Doctor, Appointment classes
│   ├── patient_registry.py    # hashing/BST-backed patient store
│   ├── queue_manager.py       # priority queue for walk-ins
│   ├── scheduler.py           # interval scheduling for appointments
│   └── billing.py
├── api/                     # FastAPI routes (Stage 3+)
├── ai/
│   ├── triage_classifier.py
│   ├── no_show_predictor.py
│   └── chat_assistant.py
├── db/
│   └── schema.sql
└── tests/
```
