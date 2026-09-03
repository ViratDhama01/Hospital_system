-- Patients Table
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dob TEXT,
    gender TEXT,
    phone TEXT UNIQUE NOT NULL,
    address TEXT,
    blood_group TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Doctors Table
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    specialization TEXT NOT NULL,
    available_from TEXT NOT NULL, -- Stored as 'HH:MM'
    available_to TEXT NOT NULL    -- Stored as 'HH:MM'
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
    role TEXT NOT NULL -- admin, receptionist, doctor
);
