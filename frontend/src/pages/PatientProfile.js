import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Activity, FileText, Pill, User, Save, Plus, X } from 'lucide-react';
import { api } from '../api';

const PatientProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  const [clinicalNotes, setClinicalNotes] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [labs, setLabs] = useState([]);
  const [showAddNote, setShowAddNote] = useState(false);
  const [showAddPrescription, setShowAddPrescription] = useState(false);
  const [showAddLab, setShowAddLab] = useState(false);
  const [newNote, setNewNote] = useState({ doctor_id: '', note: '', category: 'Consultation' });
  const [newPrescription, setNewPrescription] = useState({ doctor_id: '', medication: '', dosage: '', frequency: '', duration: '' });
  const [newLab, setNewLab] = useState({ test_name: '', result_value: '', unit: '', status: 'final' });

  useEffect(() => {
    fetchPatient();
    fetchClinicalData();
  }, [id]);

  const fetchPatient = async () => {
    try {
      const data = await api.get(`/patients/${id}`);
      setPatient(data);
      setEditForm(data);
    } catch (error) {
      alert('Failed to fetch patient profile');
    } finally {
      setLoading(false);
    }
  };

  const fetchClinicalData = async () => {
    try {
      const [notes, pres, labResults, doctorData] = await Promise.all([
        api.get(`/clinical/ehr/${id}`),
        api.get(`/clinical/prescriptions/${id}`),
        api.get(`/clinical/labs/${id}`),
        api.get('/doctors/')
      ]);
      setClinicalNotes(notes);
      setPrescriptions(pres);
      setLabs(labResults);
      setDoctors(doctorData);
    } catch (error) {
      console.error('Failed to fetch clinical data:', error);
    }
  };

  const handleSave = async () => {
    try {
      await api.patch(`/patients/${id}`, editForm);
      alert('Profile updated successfully!');
      setIsEditing(false);
      fetchPatient();
    } catch (error) {
      alert(error.message || 'Update failed');
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    try {
      await api.post('/clinical/ehr', {
        patient_id: parseInt(id),
        ...newNote
      });
      alert('Health record added!');
      setShowAddNote(false);
      fetchClinicalData();
    } catch (error) {
      alert(error.message || 'Failed to add record');
    }
  };

  const handleAddPrescription = async (e) => {
    e.preventDefault();
    try {
      await api.post('/clinical/prescriptions', {
        ...newPrescription,
        patient_id: Number(id),
        doctor_id: Number(newPrescription.doctor_id)
      });
      setShowAddPrescription(false);
      setNewPrescription({ doctor_id: '', medication: '', dosage: '', frequency: '', duration: '' });
      await fetchClinicalData();
    } catch (error) {
      alert(error.message || 'Unable to add prescription');
    }
  };

  const handleAddLab = async (e) => {
    e.preventDefault();
    try {
      await api.post('/clinical/labs', { ...newLab, patient_id: Number(id) });
      setShowAddLab(false);
      setNewLab({ test_name: '', result_value: '', unit: '', status: 'final' });
      await fetchClinicalData();
    } catch (error) {
      alert(error.message || 'Unable to add lab result');
    }
  };

  if (loading) return <div className="p-8 text-center">Loading profile...</div>;
  if (!patient) return <div className="p-8 text-center">Patient not found.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/patients')} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-clinical-dark">{patient.name}</h1>
            <p className="text-slate-500">Patient ID: {patient.patient_id}</p>
          </div>
        </div>
        <button
          onClick={() => isEditing ? handleSave() : setIsEditing(true)}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${isEditing ? 'bg-emerald-500 text-white' : 'bg-clinical-blue text-white'}`}
        >
          {isEditing ? 'Save Changes' : 'Edit Profile'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="card space-y-6">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <User size={20} className="text-clinical-blue"/> Personal Information
          </h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">Gender</label>
                {isEditing ? (
                  <select
                    className="input-field mt-1"
                    value={editForm.gender}
                    onChange={e => setEditForm({...editForm, gender: e.target.value})}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                ) : <p className="font-medium">{patient.gender}</p>}
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">Blood Group</label>
                {isEditing ? (
                  <input
                    className="input-field mt-1"
                    value={editForm.blood_group}
                    onChange={e => setEditForm({...editForm, blood_group: e.target.value})}
                  />
                ) : <p className="font-medium">{patient.blood_group}</p>}
              </div>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase">Phone</label>
              {isEditing ? (
                <input
                  className="input-field mt-1"
                  value={editForm.phone}
                  onChange={e => setEditForm({...editForm, phone: e.target.value})}
                />
              ) : <p className="font-medium">{patient.phone}</p>}
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase">Address</label>
              {isEditing ? (
                <textarea
                  className="input-field mt-1 h-20"
                  value={editForm.address}
                  onChange={e => setEditForm({...editForm, address: e.target.value})}
                />
              ) : <p className="font-medium">{patient.address}</p>}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Activity size={20} className="text-clinical-blue"/> Clinical Summary (EHR)
              </h2>
              <button
                onClick={() => setShowAddNote(true)}
                className="btn-primary py-1 px-3 text-xs flex items-center gap-1"
              >
                <Plus size={14}/> Add Record
              </button>
            </div>
            <div className="space-y-3">
              {clinicalNotes.length === 0 ? (
                <p className="text-sm text-slate-600 italic p-4 bg-slate-50 rounded-xl border border-slate-100">No active clinical notes.</p>
              ) : (
                clinicalNotes.map((note, i) => (
                  <div key={i} className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-[10px] font-bold uppercase text-slate-400">{note.category}</span>
                      <span className="text-[10px] text-slate-500">{new Date(note.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-sm text-clinical-dark">{note.note}</p>
                    <p className="text-xs text-slate-500 mt-2">Doctor ID: {note.doctor_id}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {showAddNote && (
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                  <h2 className="text-xl font-bold text-clinical-dark">Add EHR Record</h2>
                  <button onClick={() => setShowAddNote(false)} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                    <X size={20} className="text-slate-400"/>
                  </button>
                </div>
                <form onSubmit={handleAddNote} className="p-6 space-y-4">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Doctor ID</label>
                      <select
                        className="input-field"
                        value={newNote.doctor_id}
                        onChange={e => setNewNote({...newNote, doctor_id: e.target.value})}
                        required
                      >
                        <option value="">Choose a doctor</option>
                        {doctors.map(doctor => <option key={doctor.doctor_id} value={doctor.doctor_id}>{doctor.name} · #{doctor.doctor_id}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Category</label>
                      <select
                        className="input-field"
                        value={newNote.category}
                        onChange={e => setNewNote({...newNote, category: e.target.value})}
                      >
                        <option value="Consultation">Consultation</option>
                        <option value="Emergency">Emergency</option>
                        <option value="Follow-up">Follow-up</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Clinical Note</label>
                      <textarea
                        className="input-field h-32"
                        value={newNote.note}
                        onChange={e => setNewNote({...newNote, note: e.target.value})}
                        required
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-3 pt-4">
                    <button type="button" onClick={() => setShowAddNote(false)} className="px-4 py-2 text-slate-500 hover:text-slate-700 font-medium">Cancel</button>
                    <button type="submit" className="btn-primary px-6">Save Record</button>
                  </div>
                </form>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Pill size={20} className="text-clinical-blue"/> Active Prescriptions
                </h2>
                <button onClick={() => setShowAddPrescription(true)} className="btn-primary py-1 px-3 text-xs flex items-center gap-1">
                  <Plus size={14}/> Add
                </button>
              </div>
              <div className="space-y-3">
                {prescriptions.length === 0 ? (
                  <p className="text-sm text-slate-500">No active prescriptions.</p>
                ) : (
                  prescriptions.map((p, i) => (
                    <div key={i} className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-clinical-dark">{p.medication}</span>
                        <span className="text-[10px] text-slate-500">{new Date(p.date_issued).toLocaleDateString()}</span>
                      </div>
                      <p className="text-xs text-slate-600">{p.dosage} • {p.frequency} • {p.duration}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <FileText size={20} className="text-clinical-blue"/> Recent Lab Results
                </h2>
                <button onClick={() => setShowAddLab(true)} className="btn-primary py-1 px-3 text-xs flex items-center gap-1">
                  <Plus size={14}/> Add
                </button>
              </div>
              <div className="space-y-3">
                {labs.length === 0 ? (
                  <p className="text-sm text-slate-500">No laboratory results found.</p>
                ) : (
                  labs.map((l, i) => (
                    <div key={i} className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-clinical-dark">{l.test_name}</span>
                        <span className="text-[10px] text-slate-500">{new Date(l.date_performed).toLocaleDateString()}</span>
                      </div>
                      <p className="text-xs text-slate-600">{l.result_value} {l.unit} • <span className="font-bold">{l.status}</span></p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {(showAddPrescription || showAddLab) && (
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                  <h2 className="text-xl font-bold text-clinical-dark">{showAddPrescription ? 'Add Prescription' : 'Add Lab Result'}</h2>
                  <button onClick={() => { setShowAddPrescription(false); setShowAddLab(false); }} className="p-2 hover:bg-slate-100 rounded-full">
                    <X size={20} className="text-slate-400"/>
                  </button>
                </div>
                {showAddPrescription ? (
                  <form onSubmit={handleAddPrescription} className="p-6 space-y-4">
                    <label className="block text-xs font-bold text-slate-500 uppercase">Doctor
                      <select className="input-field mt-1" value={newPrescription.doctor_id} onChange={e => setNewPrescription({...newPrescription, doctor_id: e.target.value})} required>
                        <option value="">Choose a doctor</option>
                        {doctors.map(doctor => <option key={doctor.doctor_id} value={doctor.doctor_id}>{doctor.name} · #{doctor.doctor_id}</option>)}
                      </select>
                    </label>
                    {['medication', 'dosage', 'frequency', 'duration'].map(field => (
                      <label key={field} className="block text-xs font-bold text-slate-500 uppercase">{field.replace('_', ' ')}
                        <input className="input-field mt-1" value={newPrescription[field]} onChange={e => setNewPrescription({...newPrescription, [field]: e.target.value})} required/>
                      </label>
                    ))}
                    <div className="flex justify-end gap-3 pt-2">
                      <button type="button" onClick={() => setShowAddPrescription(false)} className="px-4 py-2 text-slate-500">Cancel</button>
                      <button type="submit" className="btn-primary px-5">Save Prescription</button>
                    </div>
                  </form>
                ) : (
                  <form onSubmit={handleAddLab} className="p-6 space-y-4">
                    <label className="block text-xs font-bold text-slate-500 uppercase">Test name
                      <input className="input-field mt-1" value={newLab.test_name} onChange={e => setNewLab({...newLab, test_name: e.target.value})} required/>
                    </label>
                    <label className="block text-xs font-bold text-slate-500 uppercase">Result
                      <input className="input-field mt-1" value={newLab.result_value} onChange={e => setNewLab({...newLab, result_value: e.target.value})} required/>
                    </label>
                    <label className="block text-xs font-bold text-slate-500 uppercase">Unit
                      <input className="input-field mt-1" value={newLab.unit} onChange={e => setNewLab({...newLab, unit: e.target.value})}/>
                    </label>
                    <label className="block text-xs font-bold text-slate-500 uppercase">Status
                      <select className="input-field mt-1" value={newLab.status} onChange={e => setNewLab({...newLab, status: e.target.value})}>
                        <option value="final">Final</option>
                        <option value="pending">Pending</option>
                      </select>
                    </label>
                    <div className="flex justify-end gap-3 pt-2">
                      <button type="button" onClick={() => setShowAddLab(false)} className="px-4 py-2 text-slate-500">Cancel</button>
                      <button type="submit" className="btn-primary px-5">Save Lab Result</button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatientProfile;
