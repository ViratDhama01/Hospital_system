import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { roleLabel } from '../access';
import Signup from './Signup';

const displayAppointment = (appointment) =>
  `#${appointment.appointment_id} · ${appointment.patient_name || `Patient #${appointment.patient_id}`} · ${new Date(appointment.start_time).toLocaleString()}`;

const AppointmentAssignee = ({ appointment, role, staff, onSaved }) => {
  const assigned = appointment[`${role}_user_id`];
  const [selected, setSelected] = useState(assigned ? String(assigned) : '');
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const label = roleLabel(role);

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    setNotice('');
    setError('');
    try {
      const updated = await api.patch(`/appointments/${appointment.appointment_id}/staff`, {
        role,
        user_id: selected ? Number(selected) : null,
      });
      onSaved(updated);
      setNotice(updated.user_id ? `${label} assignment saved.` : `${label} assignment removed.`);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="space-y-3 rounded-lg border border-slate-200 p-4" onSubmit={save}>
      <label className="block text-sm font-medium">{label}
        <select className="input-field mt-1" value={selected} onChange={(event) => { setSelected(event.target.value); setNotice(''); setError(''); }} disabled={saving}>
          <option value="">Unassigned</option>
          {staff.filter((account) => account.role === role).map((account) => (
            <option key={account.user_id} value={account.user_id}>{account.display_name} ({account.username})</option>
          ))}
        </select>
      </label>
      <button type="submit" className="btn-primary disabled:opacity-50" disabled={saving || selected === String(assigned ?? '')}>
        {saving ? 'Saving…' : `Save ${label.toLowerCase()} assignment`}
      </button>
      {notice && <p className="text-sm text-emerald-700" role="status">{notice}</p>}
      {error && <p className="text-sm text-rose-700" role="alert">{error}</p>}
    </form>
  );
};

const AppointmentAssignments = ({ appointmentId, selectAppointment }) => {
  const [appointments, setAppointments] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([api.get('/appointments/'), api.get('/staff')])
      .then(([visits, accounts]) => {
        if (!active) return;
        setAppointments(visits.filter((visit) => visit.status === 'booked'));
        setStaff(accounts);
      })
      .catch((failure) => { if (active) setError(failure.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const appointment = appointments.find((visit) => String(visit.appointment_id) === appointmentId);
  const saveAppointment = (update) => {
    setAppointments((visits) => visits.map((visit) => visit.appointment_id === update.appointment_id
      ? { ...visit, [`${update.role}_user_id`]: update.user_id, [`${update.role}_name`]: update.display_name }
      : visit));
  };

  if (loading) return <p role="status">Loading appointments and staff…</p>;
  if (error) return <p role="alert" className="text-rose-700">{error}</p>;

  return (
    <section className="card max-w-4xl space-y-5">
      <label className="block text-sm font-medium">Booked appointment
        <select className="input-field mt-1" value={appointment ? appointmentId : ''} onChange={(event) => selectAppointment(event.target.value)}>
          <option value="">Choose an appointment</option>
          {appointments.map((visit) => <option key={visit.appointment_id} value={visit.appointment_id}>{displayAppointment(visit)}</option>)}
        </select>
      </label>
      {!appointments.length && <p className="text-sm text-slate-600">Book an appointment before assigning staff.</p>}
      {appointmentId && !appointment && <p className="text-sm text-slate-600">This appointment is no longer available for assignment.</p>}
      {appointment && <>
        <p className="text-sm text-slate-700"><strong>Booked doctor</strong> {appointment.doctor_name || `Doctor #${appointment.doctor_id}`}</p>
        <div className="grid gap-4 md:grid-cols-2">
          {['nurse', 'receptionist'].map((role) => (
            <AppointmentAssignee key={`${appointment.appointment_id}-${role}`} appointment={appointment} role={role} staff={staff} onSaved={saveAppointment}/>
          ))}
        </div>
      </>}
    </section>
  );
};

const AssignmentHistory = () => {
  const [events, setEvents] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/staff/assignment-history').then(setEvents).catch((failure) => setError(failure.message));
  }, []);

  if (error) return <p role="alert" className="text-rose-700">{error}</p>;
  if (!events) return <p role="status">Loading assignment history…</p>;

  return (
    <section className="card max-w-4xl">
      <h2 className="mb-4 text-lg font-bold">Recent assignment changes</h2>
      {!events.length && <p className="text-slate-600">No assignment changes yet.</p>}
      <ul className="divide-y divide-slate-100">
        {events.map((event) => (
          <li key={event.event_id} className="py-3">
            <p className="font-medium">{event.staff_name} · {event.detail}</p>
            <p className="text-sm text-slate-600">{event.appointment_id && `Appointment #${event.appointment_id} · `}{event.actor_name} · {new Date(event.created_at).toLocaleString()}</p>
          </li>
        ))}
      </ul>
    </section>
  );
};

const StaffAssignments = () => {
  const [params, setParams] = useSearchParams();
  const tabs = [['accounts', 'Accounts & roles'], ['appointments', 'Appointment assignments'], ['history', 'Assignment history']];
  const tab = tabs.some(([key]) => key === params.get('tab')) ? params.get('tab') : 'accounts';

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-clinical-dark">Staff Assignments</h1>
      <nav className="flex flex-wrap gap-2" aria-label="Staff assignment sections">
        {tabs.map(([key, label]) => (
          <button type="button" key={key} aria-pressed={tab === key} onClick={() => setParams({ tab: key })}
            className={`rounded-lg px-4 py-2 font-medium ${tab === key ? 'bg-clinical-blue text-white' : 'border border-slate-300 bg-white text-slate-700'}`}>
            {label}
          </button>
        ))}
      </nav>
      {tab === 'accounts' && <Signup />}
      {tab === 'history' && <AssignmentHistory />}
      {tab === 'appointments' && <AppointmentAssignments appointmentId={params.get('appointment_id')}
        selectAppointment={(id) => setParams(id ? { tab, appointment_id: id } : { tab })}/>}
    </div>
  );
};

export default StaffAssignments;
