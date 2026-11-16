import React, { useState, useEffect } from 'react';
import { Plus, Search, X, HeartPulse, RotateCcw, Archive } from 'lucide-react';
import { useNavigate, useOutletContext, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { isClinician } from '../access';

const PatientRegistry = () => {
  const navigate = useNavigate();
  const { role } = useOutletContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [patientStatus, setPatientStatus] = useState('active');
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [statusError, setStatusError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [newPatient, setNewPatient] = useState({
    name: '', dob: '', gender: 'Male', phone: '', address: '', blood_group: 'O+'
  });

  useEffect(() => {
    fetchPatients();
  }, [patientStatus]);

  useEffect(() => {
    if (searchParams.get('new') === '1') setShowModal(true);
  }, [searchParams]);

  const closeRegistration = () => {
    setShowModal(false);
    if (searchParams.has('new')) setSearchParams({}, { replace: true });
  };

  const fetchPatients = async () => {
    try {
      setLoading(true);
      setPatients(await api.get(`/patients/?status=${patientStatus}`));
    } catch (error) {
      alert('Failed to fetch patients');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await api.post('/patients/', newPatient);
      alert('Patient registered successfully!');
      closeRegistration();
      setNewPatient({ name: '', dob: '', gender: 'Male', phone: '', address: '', blood_group: 'O+' });
      fetchPatients();
    } catch (error) {
      alert(error.message || 'Registration failed');
    }
  };

  const updateStatus = async (patient, endpoint, payload, question) => {
    if (!window.confirm(question)) return;
    setStatusUpdating(true);
    setStatusError('');
    try {
      await api.patch(`/patients/${patient.patient_id}/${endpoint}`, payload);
      await fetchPatients();
    } catch (error) {
      setStatusError(error.message || 'Unable to update patient status');
    } finally {
      setStatusUpdating(false);
    }
  };

  const selectStatus = (status) => {
    setStatusError('');
    setPatientStatus(status);
  };

  const filteredPatients = patients.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.phone.includes(searchTerm) || String(p.patient_id).includes(searchTerm)
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-clinical-dark">Patient Registry</h1>
          <p className="text-slate-500">Manage active patients and review cured patient history.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={20}/>
          <span>Register New Patient</span>
        </button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-xl font-bold text-clinical-dark">Register Patient</h2>
              <button onClick={closeRegistration} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                <X size={20} className="text-slate-400"/>
              </button>
            </div>
            <form onSubmit={handleRegister} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Full Name</label>
                  <input
                    type="text"
                    className="input-field"
                    value={newPatient.name}
                    onChange={(e) => setNewPatient({...newPatient, name: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">DOB</label>
                  <input
                    type="date"
                    className="input-field"
                    value={newPatient.dob}
                    onChange={(e) => setNewPatient({...newPatient, dob: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Gender</label>
                  <select
                    className="input-field"
                    value={newPatient.gender}
                    onChange={(e) => setNewPatient({...newPatient, gender: e.target.value})}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Phone</label>
                  <input
                    type="text"
                    className="input-field"
                    value={newPatient.phone}
                    onChange={(e) => setNewPatient({...newPatient, phone: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Blood Group</label>
                  <input
                    type="text"
                    className="input-field"
                    value={newPatient.blood_group}
                    onChange={(e) => setNewPatient({...newPatient, blood_group: e.target.value})}
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Address</label>
                  <textarea
                    className="input-field h-20"
                    value={newPatient.address}
                    onChange={(e) => setNewPatient({...newPatient, address: e.target.value})}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={closeRegistration}
                  className="px-4 py-2 text-slate-500 hover:text-slate-700 font-medium"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary px-6">
                  Register Patient
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <div className="absolute left-3 top-2.5 text-slate-400">
              <Search size={18}/>
            </div>
            <input
              type="text"
              placeholder="Search by name, phone or ID..."
              className="input-field pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            {[
              ['active', 'Active patients'], ['cured', 'Cured history'],
              ...(role === 'admin' ? [['archived', 'Archived']] : []),
            ].map(([status, label]) => (
              <button key={status} onClick={() => selectStatus(status)} disabled={statusUpdating} className={`px-4 py-2 rounded-lg font-medium ${patientStatus === status ? 'bg-clinical-blue text-white' : 'border border-slate-200 text-slate-600'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        {statusError && <p role="alert" className="mb-4 text-sm text-rose-700">{statusError}</p>}
        {loading ? (
          <div className="py-20 text-center text-slate-500">Loading patients...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                <tr className="border-b border-slate-100">
                  <th className="px-6 py-3 font-semibold">Patient</th>
                  <th className="px-6 py-3 font-semibold">Phone</th>
                  <th className="px-6 py-3 font-semibold">Blood Group</th>
                  <th className="px-6 py-3 font-semibold">Gender</th>
                  <th className="px-6 py-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredPatients.map((p) => (
                  <tr key={p.patient_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-clinical-dark">{p.name}</p>
                      <p className="text-xs text-slate-500">ID: {p.patient_id}</p>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{p.phone}</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 rounded-md bg-blue-50 text-blue-600 text-xs font-bold">{p.blood_group}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{p.gender}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => navigate(`/patients/${p.patient_id}`)}
                          className="text-clinical-blue hover:underline text-sm font-medium"
                        >
                          View Profile
                        </button>
                        {isClinician(role) && patientStatus !== 'archived' && <button
                          disabled={statusUpdating}
                          onClick={() => updateStatus(p, 'cure', { cured: !p.is_cured }, p.is_cured ? 'Restore this patient to the active registry?' : 'Mark this patient as cured?')}
                          className={`flex items-center gap-1 text-sm font-medium ${patientStatus === 'cured' ? 'text-amber-700' : 'text-emerald-700'}`}
                          title={patientStatus === 'cured' ? 'Restore to active patients' : 'Mark as cured'}
                        >
                          {patientStatus === 'cured' ? <RotateCcw size={15}/> : <HeartPulse size={15}/>}
                          {patientStatus === 'cured' ? 'Restore' : 'Cure'}
                        </button>}
                        {role === 'admin' && <button
                          disabled={statusUpdating}
                          onClick={() => updateStatus(p, 'archive', { archived: !p.archived_at }, p.archived_at ? 'Restore this patient from the archive?' : 'Remove this patient from the registry? Their records and existing appointments will be kept.')}
                          className="flex items-center gap-1 text-sm font-medium text-rose-700"
                        >
                          {p.archived_at ? <RotateCcw size={15}/> : <Archive size={15}/>}
                          {p.archived_at ? 'Restore' : 'Remove'}
                        </button>}
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredPatients.length === 0 && (
                  <tr>
                    <td colSpan="5" className="px-6 py-10 text-center text-slate-500">No patients found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientRegistry;
