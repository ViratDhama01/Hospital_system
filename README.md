# 🏥 Medora · Hospital Management System

Medora brings patient registration, appointments, clinical records, billing, and staff assignments into one workspace for hospital teams. Use the desktop app on Apple Silicon or run the React frontend and FastAPI backend for development.

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-00796B?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-1D1D1F?style=for-the-badge&logo=apple&logoColor=white)

## ✨ What Medora does

| Workflow | What you can do |
| --- | --- |
| **Patient registry** | Register and search patients, update their details, mark patients as cured, and archive or restore records. |
| **Appointments and queues** | Book available slots, manage walk-ins, prioritize urgent visits, and track doctor availability. |
| **Clinical records** | Review clinical notes, prescriptions, and lab results. Doctors and admins can add clinical entries. |
| **Billing** | Generate invoices, record cash payments, and confirm card or UPI payments after verifying receipt. |
| **Reports and history** | Review appointment activity, department footfall, doctor workload, and financial totals. |
| **Staff assignments** | Create staff accounts, link doctor profiles, and assign a nurse or receptionist to a booked visit. |

## 👥 Staff roles

| Role | Access |
| --- | --- |
| **Administrator** | Manage staff accounts and assignments, doctor profiles, patient archives, and hospital workflows. |
| **Doctor** | Work with clinical records, prescriptions, lab results, appointments, billing, and reports. |
| **Nurse** | View appointments, prescriptions, and lab results. |
| **Receptionist** | Handle patient registration, scheduling, and billing. View prescriptions and lab results. |

Admins can create accounts and change roles under **Staff Assignments → Accounts & roles**. Register doctors under **Doctors** before linking their accounts. Use **Staff Assignments → Appointment assignments** to assign booked visits. Staff can filter their visits under **Appointments → My assignments**.

## 🍎 Install on macOS

On an Apple Silicon Mac with Docker Desktop installed, open the Medora DMG, drag **Medora** into **Applications**, and launch it. The first launch imports the bundled Docker images and starts the backend and database. On a new installation, sign in with `admin` / `admin123`.

To upgrade, quit Medora and replace the app in **Applications**. The app keeps its database across upgrades and stops its containers when you quit. The desktop database is separate from the development database.

### Build the installer

Start Docker Desktop on an Apple Silicon Mac with Xcode or its command-line tools installed. Run the build command from the repository root.

```bash
bash packaging/macos/build-dmg.sh
```

The build writes the versioned DMG to `dist/`.

## 🛠️ Run locally for development

With Docker Compose and Node.js installed, run the API and PostgreSQL from the repository root.

```bash
docker compose up --build -d
```

Start the React frontend in a second terminal.

```bash
cd frontend
npm ci --legacy-peer-deps
npm start
```

Open the [Medora frontend](http://localhost:3000) or the [FastAPI documentation](http://localhost:8000/docs). For local configuration, see [.env.example](.env.example).

## 🧩 How it fits together

The Mac app opens Medora in a native window. The Docker app container serves both the React interface and FastAPI, and a separate container runs PostgreSQL.

```mermaid
flowchart LR
    A["Medora for macOS"] --> B["App container<br/>React and FastAPI"]
    B --> C["Database container<br/>PostgreSQL"]
    C --> D["Persistent Docker volume"]
```

| Directory | Purpose |
| --- | --- |
| [`frontend/`](frontend/) | React pages, navigation, and API client |
| [`api/`](api/) | FastAPI routes and request schemas |
| [`core/`](core/) | Patient, scheduling, billing, and clinical workflows |
| [`db/`](db/) | Database adapter, schema, and migrations |
| [`packaging/macos/`](packaging/macos/) | Mac launcher, packaged Docker stack, and installer build |
| [`tests/`](tests/) | Core workflow tests |
