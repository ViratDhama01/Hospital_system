import React, { useCallback, useEffect, useState } from 'react';
import { Users, Calendar, Activity, CreditCard, RefreshCw, Stethoscope, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

const formatMoney = (amount) => `₹${Number(amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

const StatCard = ({ title, value, caption, icon: Icon, color }) => (
  <div className="card flex items-center justify-between">
    <div>
      <p className="text-slate-500 text-sm font-medium">{title}</p>
      <h3 className="text-2xl font-bold mt-1">{value}</h3>
      <p className="text-xs text-slate-500 mt-2">{caption}</p>
    </div>
    <div className={`w-12 h-12 ${color} rounded-2xl flex items-center justify-center text-white shadow-lg`}><Icon size={24}/></div>
  </div>
);

const Dashboard = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triageOpen, setTriageOpen] = useState(false);
  const [patients, setPatients] = useState([]);
  const [triage, setTriage] = useState({ patient_id: '', symptoms: '' });
  const [triageSaving, setTriageSaving] = useState(false);
  const [triageMessage, setTriageMessage] = useState('');
  const [error, setError] = useState('');

  const fetchDashboard = useCallback(async () => {
    try {
      const offset = new Date().getTimezoneOffset();
      const data = await api.get(`/dashboard/summary?timezone_offset_minutes=${offset}`);
      setSummary(data);
      setError('');
    } catch (requestError) {
      setError(requestError.message || 'Unable to load live dashboard data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    const timer = setInterval(fetchDashboard, 15000);
    return () => clearInterval(timer);
  }, [fetchDashboard]);

  const openTriage = async () => {
    setTriageOpen(true);
    setTriageMessage('');
    try {
      setPatients(await api.get('/patients/?status=active'));
    } catch (requestError) {
      setTriageMessage(requestError.message || 'Unable to load patients.');
    }
  };

  const submitTriage = async (event) => {
    event.preventDefault();
    setTriageSaving(true);
    setTriageMessage('');
    try {
      const query = new URLSearchParams({ patient_id: triage.patient_id, symptoms: triage.symptoms });
      const result = await api.post(`/queue/triage?${query.toString()}`, {});
      setTriageMessage(result.message);
      setTriage({ patient_id: '', symptoms: '' });
      await fetchDashboard();
    } catch (requestError) {
      setTriageMessage(requestError.message || 'Unable to assess this patient.');
    } finally {
      setTriageSaving(false);
    }
  };

  const relativeTime = (value) => {
    const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hr ago`;
    return `${Math.floor(hours / 24)} days ago`;
  };

  const schedule = summary?.today_schedule || [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-clinical-dark">Hospital Overview</h1>
          <p className="text-slate-500">Current figures from hospital records, refreshed every 15 seconds.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">{summary?.as_of ? `Data refreshed ${new Date(summary.as_of).toLocaleTimeString()}` : ''}</span>
          <button onClick={fetchDashboard} className="btn-secondary flex items-center gap-2" aria-label="Refresh dashboard"><RefreshCw size={17}/><span>Refresh</span></button>
          <button onClick={() => navigate('/appointments?new=1')} className="btn-primary">+ New Appointment</button>
        </div>
      </div>

      {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
      {loading && !summary ? <div className="card text-center text-slate-500">Loading live dashboard data…</div> : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard title="Active Patients" value={summary?.active_patients ?? '—'} caption="Currently in the active registry" icon={Users} color="bg-blue-500"/>
            <StatCard title="Appointments Today" value={summary?.appointments_today ?? '—'} caption="Booked or completed · excludes cancellations" icon={Calendar} color="bg-indigo-500"/>
            <StatCard title="Average Current Wait" value={summary?.average_current_wait_minutes == null ? '—' : `${summary.average_current_wait_minutes} min`} caption={summary?.patients_waiting ? `Across ${summary.patients_waiting} patients in the walk-in queue` : 'No patients currently in the walk-in queue'} icon={Activity} color="bg-emerald-500"/>
            <StatCard title="Collected Revenue" value={formatMoney(summary?.total_collected)} caption={`Billed ${formatMoney(summary?.total_billed)} · Outstanding ${formatMoney(summary?.outstanding)}`} icon={CreditCard} color="bg-amber-500"/>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <section className="lg:col-span-2 card">
              <div className="flex items-center justify-between mb-5">
                <div><h2 className="text-lg font-bold">Today’s Schedule</h2><p className="text-sm text-slate-500">{schedule.length} appointment{schedule.length === 1 ? '' : 's'} on record</p></div>
                <button onClick={() => navigate('/appointments')} className="text-clinical-blue text-sm font-medium hover:underline">All appointments</button>
              </div>
              {schedule.length === 0 ? <p className="py-8 text-center text-slate-500">No appointments scheduled for today.</p> : (
                <div className="overflow-x-auto"><table className="w-full text-left">
                  <thead className="bg-slate-50 text-slate-500 text-xs uppercase"><tr><th className="px-4 py-3">Time</th><th className="px-4 py-3">Patient</th><th className="px-4 py-3">Doctor</th><th className="px-4 py-3">Status</th></tr></thead>
                  <tbody className="divide-y divide-slate-100">{schedule.map((appointment) => (
                    <tr key={appointment.appointment_id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 text-sm">{new Date(appointment.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</td>
                      <td className="px-4 py-3"><button onClick={() => navigate(`/patients/${appointment.patient_id}`)} className="text-left font-medium text-clinical-blue hover:underline">{appointment.patient_name}</button><p className="text-xs text-slate-500">#{appointment.patient_id}</p></td>
                      <td className="px-4 py-3 text-sm">Dr. {appointment.doctor_name}<p className="text-xs text-slate-500">{appointment.department}</p></td>
                      <td className="px-4 py-3"><span className={`text-sm capitalize ${appointment.category === 'emergency' ? 'font-bold text-rose-600' : 'text-slate-600'}`}>{appointment.category === 'emergency' ? 'Emergency · ' : ''}{appointment.status}</span></td>
                    </tr>
                  ))}</tbody>
                </table></div>
              )}
            </section>

            <section className="card bg-clinical-dark text-white">
              <h2 className="text-lg font-bold mb-1">Quick Actions</h2>
              <p className="text-xs text-slate-400 mb-5">{summary?.active_doctors ?? 0} active doctors available</p>
              <div className="space-y-3">
                <button onClick={() => navigate('/patients?new=1')} className="w-full p-4 bg-white/10 rounded-xl hover:bg-white/20 text-left flex items-center gap-4">
                  <span className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center"><Users size={20}/></span><span><span className="block font-medium">Register Patient</span><span className="text-xs text-slate-400">Open patient registration</span></span>
                </button>
                <button onClick={() => navigate('/appointments?new=1')} className="w-full p-4 bg-white/10 rounded-xl hover:bg-white/20 text-left flex items-center gap-4">
                  <span className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center"><Calendar size={20}/></span><span><span className="block font-medium">Schedule Visit</span><span className="text-xs text-slate-400">Book for an existing patient</span></span>
                </button>
                <button onClick={openTriage} className="w-full p-4 bg-white/10 rounded-xl hover:bg-white/20 text-left flex items-center gap-4">
                  <span className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center"><Stethoscope size={20}/></span><span><span className="block font-medium">Triage Patient</span><span className="text-xs text-slate-400">Assess symptoms and add to queue</span></span>
                </button>
              </div>
            </section>
          </div>

          <section className="card">
            <div className="flex items-center justify-between mb-4"><div><h2 className="text-lg font-bold">Recently Registered Patients</h2><p className="text-sm text-slate-500">Registration times from the patient records</p></div><button onClick={() => navigate('/patients')} className="text-clinical-blue text-sm font-medium hover:underline">View patients</button></div>
            {(summary?.recent_patients || []).length === 0 ? <p className="py-6 text-center text-slate-500">No patient records yet.</p> : <div className="divide-y divide-slate-100">{summary.recent_patients.map((patient) => (
              <button key={patient.patient_id} onClick={() => navigate(`/patients/${patient.patient_id}`)} className="w-full py-3 flex items-center justify-between text-left hover:bg-slate-50 px-2 rounded">
                <span className="font-medium text-clinical-dark">{patient.name}<span className="ml-2 text-xs font-normal text-slate-500">#{patient.patient_id}{patient.is_cured ? ' · Cured' : ''}</span></span><span className="text-sm text-slate-500">{relativeTime(patient.created_at)}</span>
              </button>
            ))}</div>}
          </section>
        </>
      )}

      {triageOpen && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b p-5"><h2 className="text-lg font-bold">Priority Assessment</h2><button onClick={() => setTriageOpen(false)} aria-label="Close triage"><X size={20}/></button></div>
          <form onSubmit={submitTriage} className="space-y-4 p-5">
            <label className="block text-sm font-medium">Patient<select className="input-field mt-1" required value={triage.patient_id} onChange={(event) => setTriage({ ...triage, patient_id: event.target.value })}><option value="">Choose patient</option>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patient.name} · #{patient.patient_id}</option>)}</select></label>
            <label className="block text-sm font-medium">Symptoms<textarea className="input-field mt-1 min-h-24" required value={triage.symptoms} onChange={(event) => setTriage({ ...triage, symptoms: event.target.value })} placeholder="Describe the patient's symptoms"/></label>
            {triageMessage && <p role="status" className="text-sm text-clinical-blue">{triageMessage}</p>}
            <div className="flex justify-end gap-3"><button type="button" onClick={() => setTriageOpen(false)} className="btn-secondary">Close</button><button disabled={triageSaving} className="btn-primary disabled:opacity-60">{triageSaving ? 'Assessing…' : 'Assess & Add to Queue'}</button></div>
          </form>
        </div>
      </div>}
    </div>
  );
};

export default Dashboard;
