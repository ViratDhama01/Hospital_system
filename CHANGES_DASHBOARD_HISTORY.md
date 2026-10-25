# Dashboard and history changes

## Dashboard values

- Replaced the fixed appointment count, fixed wait-time estimate, and made-up month-over-month percentages with values read from the active database.
- Dashboard counts show active patients, active doctors, and non-cancelled appointments scheduled for today.
- Revenue uses amounts on bills marked paid; billed and outstanding amounts are shown separately.
- Average current wait is calculated from arrival timestamps for patients currently in the walk-in queue. When nobody is waiting, the dashboard shows no average instead of inventing one. This is current elapsed queue time, not a completed visit's historical wait duration.
- The dashboard reloads its summary every 15 seconds and has a manual refresh button. Today's schedule includes real appointment, patient, doctor, department, and status values. Recent patient rows use the saved registration timestamp.

## Dashboard actions

- Register Patient opens the patient registration form. Schedule Visit opens the existing appointment form.
- Triage Patient collects a patient and symptoms, runs the existing symptom-priority assessment, saves the assessment, and adds the patient to the persistent queue.
- Added the missing `triage_logs` table so triage can persist on both SQLite and PostgreSQL.

## History

- Added a History page with category and text filters. It combines saved appointments, patient registrations and cured status, doctor status, bills and payments, EHR notes, prescriptions, lab results, notifications, triage assessments, and report snapshots.
- Report data is saved as a snapshot when the Reports page is opened or its Refresh Data action is used. Reports then refresh their displayed values every 30 seconds without generating more snapshots for each automatic refresh.
- History refreshes every 30 seconds and displays up to the 500 most recent saved events. The existing database records are preserved; the new history tables are additive.

## Appointment completion and emergency priority

- Added an appointment category at booking: routine or emergency. Emergency appointments receive priority 1 and are placed in the doctor's earliest available slot at or after the requested time. Routine appointments retain the requested slot and existing overlap checks.
- Doctors and admins can mark an appointment complete after its scheduled start. The completion time is saved. If the doctor finishes before the planned end, future booked appointments for that same doctor move earlier by the time saved, with durations and order preserved and overlaps avoided.
- Each automatic schedule change is recorded in appointment schedule history. The appointment list refreshes every 15 seconds; dashboard and history views also refresh automatically.
- Booking and completion use the browser's local time so the clinic schedule is not shifted by the database container's timezone.

## Billing and payment controls

- Moved Process Payment into a high-contrast, full-width form and replaced free-typed invoice IDs with a list of outstanding invoices. Selecting Pay Now fills the invoice balance, and partial payments display the paid and remaining amounts.
- Fixed the payment amount input state update and made payment submission a validated form with an inline error message.
- Added backward-compatible payment table migrations for transaction IDs and payment status, which the payment processor already writes.
- Payment processing now checks the invoice, rejects overpayments, returns the resulting status, and marks invoices paid after the full balance has been received.
- Added per-invoice Mark Paid and Mark Unpaid controls for manual status correction.
- Billing totals include partial payments and remaining balances; a manual status change is reflected in the paid/unpaid totals.
- Cash payments are recorded as completed. Card and UPI methods are saved as in-process transactions and do not mark an invoice paid until confirmed; repeated attempts are blocked while one is pending.

## Appointment slot selection

- Booking now asks for a doctor, date, adjustable duration (30 minutes by default), and an available time from a slot list. The date/time field no longer asks the booker to guess.
- Available slots are generated from the doctor's shift, the selected duration, current local time, and existing booked appointments. Starts are offered on a 15-minute grid and the booking API still checks for conflicts when the user submits.
- The slot list refreshes when the doctor, date, or duration changes. The booking dialog can scroll on shorter screens.

## Live local clock

- Added a clock in the application header that reads the browser/device's current time and date in the user's local timezone and refreshes every second.
- The dashboard's “Data refreshed” label remains tied to the last database refresh so it is distinct from the live clock.

## Verification

- Frontend production build completed successfully.
- Verified the dashboard summary, unified history, and report snapshot endpoints against the running PostgreSQL-backed API. Removed the temporary report snapshot created during that check.
- The appointment completion action is restricted to doctor and admin accounts. Automatic moves are limited to future booked appointments belonging to the same doctor.
- Verified the rebuilt PostgreSQL API returns appointment category/completion fields, the local-time-aware dashboard summary, and history records; Compose API and database are running.
- Verified cash settlement, UPI in-process status, transaction creation, and manual paid/unpaid controls using temporary invoices; removed all verification invoices and payments afterward.
- Python syntax parsing succeeded for the changed backend modules.
