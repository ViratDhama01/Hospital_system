import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Calendar, Clock, User, CheckCircle, X, AlertTriangle } from 'lucide-react';
import { api } from '../api';

const localDateValue = () => {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
};

const Appointments = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [appointments, setAppointments] = useState([]);
  const [patients, setPatients] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [canComplete, setCanComplete] = useState(false);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [slotsError, setSlotsError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [bookingData, setBookingData] = useState({
    patient_id: '',
    doctor_id: '',
    appointment_date: localDateValue(),
    slot_time: '',
    duration_minutes: 30,
    category: 'routine'
  });

  useEffect(() => {
    fetchAppointments(false);
    const timer = setInterval(() => fetchAppointments(true), 15000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (searchParams.get('new') === '1') setShowModal(true);
  }, [searchParams]);

  useEffect(() => {
    if (!showModal || !bookingData.doctor_id || !bookingData.appointment_date) {
      setAvailableSlots([]);
      setSlotsLoading(false);
      setSlotsError('');
      return undefined;
    }
    let cancelled = false;
    setSlotsLoading(true);
    setSlotsError('');
    const query = new URLSearchParams({
      doctor_id: bookingData.doctor_id,
      date: bookingData.appointment_date,
      duration_minutes: String(bookingData.duration_minutes),
      timezone_offset_minutes: String(new Date().getTimezoneOffset())
    });
    api.get(`/appointments/available-slots?${query.toString()}`)
      .then((data) => { if (!cancelled) setAvailableSlots(data.slots || []); })
      .catch((error) => { if (!cancelled) { setAvailableSlots([]); setSlotsError(error.message || 'Unable to load available slots.'); } })
      .finally(() => { if (!cancelled) setSlotsLoading(false); });
    return () => { cancelled = true; };
  }, [showModal, bookingData.doctor_id, bookingData.appointment_date, bookingData.duration_minutes]);

  useEffect(() => {
    if (bookingData.slot_time && !availableSlots.some((slot) => slot.slice(11, 16) === bookingData.slot_time)) {
      setBookingData((current) => ({ ...current, slot_time: '' }));
    }
  }, [availableSlots, bookingData.slot_time]);

  const closeBookingModal = () => {
    setShowModal(false);
    if (searchParams.has('new')) setSearchParams({}, { replace: true });
  };

  const fetchAppointments = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [data, patientData, doctorData, auth] = await Promise.all([
        api.get('/appointments/'),
        api.get('/patients/'),
        api.get('/doctors/'),
        api.get('/auth/status')
      ]);
      setAppointments(data);
      setPatients(patientData);
      setDoctors(doctorData);
      setCanComplete(['doctor', 'admin'].includes(auth?.user?.role));
    } catch (error) {
      alert('Failed to fetch appointments');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const handleBook = async (e) => {
    e.preventDefault();
    try {
      const result = await api.post('/appointments/', {
        patient_id: Number(bookingData.patient_id),
        doctor_id: Number(bookingData.doctor_id),
        duration_minutes: Number(bookingData.duration_minutes),
        category: bookingData.category,
        start_time: `${bookingData.appointment_date}T${bookingData.slot_time}:00`,
        timezone_offset_minutes: new Date().getTimezoneOffset()
      });
      const actualTime = new Date(result.start_time).toLocaleString();
      alert(result.rescheduled_for_emergency
        ? `Emergency appointment prioritized. The earliest available slot is ${actualTime}.`
        : `Appointment booked for ${actualTime}.`);
      closeBookingModal();
      fetchAppointments();
    } catch (error) {
      alert(error.message || 'Booking failed');
    }
  };

  const handleCancel = async (id) => {
    if (!window.confirm('Are you sure you want to cancel this appointment?')) return;
    try {
      await api.patch(`/appointments/${id}/cancel`);
      alert('Appointment cancelled');
      fetchAppointments();
    } catch (error) {
      alert(error.message || 'Cancellation failed');
    }
  };

  const handleComplete = async (appointment) => {
    if (!window.confirm('Mark this appointment as completed? If it finishes before its scheduled end, this doctor’s later booked appointments will be moved earlier where possible.')) return;
    try {
      const localNow = new Date();
      localNow.setMinutes(localNow.getMinutes() - localNow.getTimezoneOffset());
      const result = await api.patch(`/appointments/${appointment.appointment_id}/complete`, {
        completed_at: localNow.toISOString().slice(0, 19)
      });
      const moved = result.shifted_appointments || [];
      alert(moved.length
        ? `Appointment completed. ${moved.length} upcoming appointment(s) were moved earlier. Review the updated times below.`
        : 'Appointment completed. No upcoming appointments needed to move.');
      await fetchAppointments();
    } catch (error) {
      alert(error.message || 'Unable to complete appointment');
    }
  };

  const todayAppointments = appointments.filter((appointment) =>
    new Date(appointment.start_time).toDateString() === new Date().toDateString() && appointment.status !== 'cancelled'
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-clinical-dark">Appointments</h1>
          <p className="text-slate-500">Schedule and manage patient visits.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Calendar size={20}/>
          <span>Book Appointment</span>
        </button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-xl font-bold text-clinical-dark">Book Appointment</h2>
              <button onClick={closeBookingModal} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                <X size={20} className="text-slate-400"/>
              </button>
            </div>
            <form onSubmit={handleBook} className="p-6 space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Patient</label>
                  <select
                    className="input-field"
                    value={bookingData.patient_id}
                    onChange={(e) => setBookingData({...bookingData, patient_id: e.target.value})}
                    required
                  >
                    <option value="">Choose a patient</option>
                    {patients.map(patient => <option key={patient.patient_id} value={patient.patient_id}>{patient.name} · #{patient.patient_id}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Doctor</label>
                  <select
                    className="input-field"
                    value={bookingData.doctor_id}
                    onChange={(e) => setBookingData({...bookingData, doctor_id: e.target.value, slot_time: ''})}
                    required
                  >
                    <option value="">Choose a doctor</option>
                    {doctors.map(doctor => <option key={doctor.doctor_id} value={doctor.doctor_id}>{doctor.name} · {doctor.available_from}–{doctor.available_to}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Appointment date</label>
                  <input
                    type="date"
                    className="input-field"
                    value={bookingData.appointment_date}
                    min={localDateValue()}
                    onChange={(e) => setBookingData({...bookingData, appointment_date: e.target.value, slot_time: ''})}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Duration (Minutes)</label>
                  <input
                    type="number"
                    className="input-field"
                    value={bookingData.duration_minutes}
                    min="5"
                    max="120"
                    step="5"
                    onChange={(e) => setBookingData({...bookingData, duration_minutes: Number(e.target.value), slot_time: ''})}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Available time slots</label>
                  <select
                    className="input-field"
                    value={bookingData.slot_time}
                    onChange={(e) => setBookingData({...bookingData, slot_time: e.target.value})}
                    disabled={!bookingData.doctor_id || slotsLoading || !availableSlots.length}
                    required
                  >
                    <option value="">{slotsLoading ? 'Checking availability…' : !bookingData.doctor_id ? 'Choose a doctor first' : 'Choose an available slot'}</option>
                    {availableSlots.map((slot) => <option key={slot} value={slot.slice(11, 16)}>{new Date(slot).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</option>)}
                  </select>
                  {slotsError && <p role="alert" className="mt-1 text-xs text-rose-600">{slotsError}</p>}
                  {!slotsLoading && bookingData.doctor_id && bookingData.appointment_date && !slotsError && availableSlots.length === 0 && <p className="mt-1 text-xs text-slate-500">No available slots for this date and duration.</p>}
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Appointment Category</label>
                  <select
                    className="input-field"
                    value={bookingData.category}
                    onChange={(e) => setBookingData({...bookingData, category: e.target.value})}
                  >
                    <option value="routine">Routine</option>
                    <option value="emergency">Emergency — prioritize next available slot</option>
                  </select>
                  {bookingData.category === 'emergency' && <p className="mt-1 text-xs text-rose-600">Emergency visits receive highest priority and are placed in the doctor’s earliest available slot.</p>}
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={closeBookingModal}
                  className="px-4 py-2 text-slate-500 hover:text-slate-700 font-medium"
                >
                  Cancel
                </button>
                <button type="submit" disabled={!bookingData.slot_time || slotsLoading} className="btn-primary px-6 disabled:cursor-not-allowed disabled:opacity-50">
                  Confirm Booking
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 card">
          <h2 className="text-lg font-bold mb-4">Upcoming Visits</h2>
          <div className="space-y-4">
            {loading ? (
              <div className="py-10 text-center text-slate-400">Loading appointments...</div>
            ) : appointments.length === 0 ? (
              <div className="py-10 text-center text-slate-400">No upcoming appointments.</div>
            ) : (
              appointments.map((apt) => (
                <div key={apt.appointment_id} className="flex items-center justify-between p-4 border border-slate-100 rounded-xl hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">
                      P{apt.patient_id}
                    </div>
                    <div>
                      <p className="font-medium text-clinical-dark">Appointment #{apt.appointment_id}</p>
                      <p className="text-xs text-slate-500">Doctor ID: {apt.doctor_id} • {new Date(apt.start_time).toLocaleString()}</p>
                      {apt.category === 'emergency' && <span className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-rose-600"><AlertTriangle size={13}/>Emergency · priority {apt.priority}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                      apt.status === 'booked' ? 'bg-amber-100 text-amber-600' :
                      apt.status === 'cancelled' ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {apt.status}
                    </span>
                    {apt.status === 'booked' && (
                      <>
                        {canComplete && new Date(apt.start_time) <= new Date() && <button
                          onClick={() => handleComplete(apt)}
                          className="flex items-center gap-1 rounded-lg bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                          title="Mark appointment completed"
                        ><CheckCircle size={15}/>Complete</button>}
                        <button
                          onClick={() => handleCancel(apt.appointment_id)}
                          className="p-2 text-slate-400 hover:text-red-500 transition-colors"
                          title="Cancel Appointment"
                        ><X size={18}/></button>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card bg-slate-50">
          <h2 className="text-lg font-bold mb-4">Today's Schedule</h2>
          <div className="space-y-3">
            {todayAppointments.length === 0 ? <p className="py-8 text-center text-sm text-slate-500">No appointments scheduled for today.</p> : todayAppointments.map((appointment) => (
              <div key={appointment.appointment_id} className="rounded-xl border border-slate-100 bg-white p-3 shadow-sm">
                <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{new Date(appointment.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span><span className={`text-xs capitalize ${appointment.category === 'emergency' ? 'text-rose-600 font-bold' : 'text-slate-500'}`}>{appointment.category || 'routine'}</span></div>
                <p className="mt-1 text-sm text-slate-600">Patient #{appointment.patient_id} · Doctor #{appointment.doctor_id}</p>
                <p className="text-xs capitalize text-slate-400">{appointment.status}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Appointments;
