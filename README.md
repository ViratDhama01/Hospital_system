# Hospital Management System
1. **Patient registration & records** — create/search/update patient profiles (demographics, medical history, ID proof)
2. **Appointment & queue management** — book, reschedule, cancel; manage walk-in queues per department
3. **Doctor/department management** — availability, specialization, schedules
4. **Billing & insurance** — consultation fees, tests, packages, insurance claims
5. **Admin/reporting** — occupancy, daily footfall, doctor load, revenue

## Medora for macOS

On an Apple Silicon Mac with Docker Desktop installed, open the Medora DMG, drag **Medora** into **Applications**, and open it. Medora starts Docker Desktop when needed and runs the bundled React app, FastAPI server, and PostgreSQL database. The first launch imports the images locally. Sign in to a new installation with `admin` / `admin123`.

Medora has a separate database from the repository's development stack. It keeps its data across launches and stops its containers when you quit the app.

To upgrade, quit the open copy, replace it in Applications, and sign in again if prompted. The new app uses the same database volume. Administrators can create logins and edit roles under **Staff Assignments → Accounts & roles**. Register a doctor under **Doctors** before linking their login. Use **Appointment assignments** to assign a nurse or receptionist to a booked visit. Staff can find their assigned visits with **My assignments** on the Appointments page.

To rebuild the installer from this checkout, start Docker Desktop and run `bash packaging/macos/build-dmg.sh`. The versioned installer is written to `dist/`.

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
