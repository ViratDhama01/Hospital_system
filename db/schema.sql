-- Patients Table
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dob TEXT,
    gender TEXT,
    phone TEXT UNIQUE NOT NULL,
    address TEXT,
    blood_group TEXT,
    is_cured INTEGER NOT NULL DEFAULT 0,
    cured_at TIMESTAMP,
    archived_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Doctors Table
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    specialization TEXT NOT NULL,
    available_from TEXT NOT NULL, -- Stored as 'HH:MM'
    available_to TEXT NOT NULL,   -- Stored as 'HH:MM'
    employment_status TEXT NOT NULL DEFAULT 'active',
    status_reason TEXT,
    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Appointments Table
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'booked', -- booked, completed, cancelled, no-show
    priority INTEGER DEFAULT 0,
    category TEXT NOT NULL DEFAULT 'routine',
    completed_at TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id),
    FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id)
);

-- Walk-in Queue Table (for persistence)
CREATE TABLE IF NOT EXISTS walk_in_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    priority INTEGER NOT NULL,
    arrival_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
);

-- Users Table for Auth
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL, -- admin, receptionist, doctor, nurse
    display_name TEXT NOT NULL DEFAULT '',
    doctor_id INTEGER REFERENCES doctors (doctor_id)
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions (user_id);

CREATE TABLE IF NOT EXISTS appointment_staff_assignments (
    appointment_id INTEGER NOT NULL REFERENCES appointments (appointment_id),
    role TEXT NOT NULL CHECK (role IN ('nurse', 'receptionist')),
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    assigned_by INTEGER NOT NULL REFERENCES users (user_id),
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (appointment_id, role)
);

CREATE INDEX IF NOT EXISTS idx_appointment_staff_user ON appointment_staff_assignments (user_id);

CREATE TABLE IF NOT EXISTS staff_assignment_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER REFERENCES appointments (appointment_id),
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    changed_by INTEGER NOT NULL REFERENCES users (user_id),
    detail TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patient_status_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients (patient_id),
    changed_by INTEGER NOT NULL REFERENCES users (user_id),
    action TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Health Records Table
CREATE TABLE IF NOT EXISTS health_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    note TEXT NOT NULL,
    category TEXT, -- e.g., 'Consultation', 'Emergency', 'Follow-up'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id),
    FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id)
);

-- Prescriptions Table
CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    medication TEXT NOT NULL,
    dosage TEXT NOT NULL,
    frequency TEXT NOT NULL,
    duration TEXT NOT NULL,
    date_issued TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id),
    FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id)
);

-- Lab Results Table
CREATE TABLE IF NOT EXISTS lab_results (
    lab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    test_name TEXT NOT NULL,
    result_value TEXT NOT NULL,
    unit TEXT,
    status TEXT DEFAULT 'pending', -- pending, final
    date_performed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
);

-- Bills Table
CREATE TABLE IF NOT EXISTS bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_status TEXT DEFAULT 'unpaid',
    bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments (appointment_id)
);

-- Payments Table
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT,
    transaction_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'completed',
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills (bill_id)
);

-- Insurance Policies Table
CREATE TABLE IF NOT EXISTS insurance_policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    provider_name TEXT NOT NULL,
    policy_number TEXT NOT NULL UNIQUE,
    coverage_details TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
);

-- Notification History Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
);

-- Generated report snapshots are retained so report history remains reviewable.
CREATE TABLE IF NOT EXISTS report_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_name TEXT NOT NULL,
    generated_by INTEGER,
    payload TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (generated_by) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS triage_logs (
    triage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    symptoms TEXT NOT NULL,
    assigned_priority INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
);

CREATE TABLE IF NOT EXISTS appointment_schedule_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    previous_start TIMESTAMP NOT NULL,
    previous_end TIMESTAMP NOT NULL,
    new_start TIMESTAMP NOT NULL,
    new_end TIMESTAMP NOT NULL,
    reason TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by INTEGER,
    FOREIGN KEY (appointment_id) REFERENCES appointments (appointment_id),
    FOREIGN KEY (changed_by) REFERENCES users (user_id)
);
