import React, { useState, useEffect } from 'react';
import { Plus, Search, X, Archive, RotateCcw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

const Doctors = () => {
  const navigate = useNavigate();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [directoryStatus, setDirectoryStatus] = useState('active');
  const [canManageDoctors, setCanManageDoctors] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [doctorToArchive, setDoctorToArchive] = useState(null);
  const [archiveReason, setArchiveReason] = useState('resigned');
  const [newDoctor, setNewDoctor] = useState({
    name: '', department: '', specialization: '', available_from: '09:00', available_to: '17:00'
  });

  useEffect(() => {
    fetchDoctors();
  }, [directoryStatus]);

  const fetchDoctors = async () => {
    try {
      setLoading(true);
      const [data, auth] = await Promise.all([
        api.get(`/doctors/?status=${directoryStatus}`),
        api.get('/auth/status')
      ]);
      setDoctors(data);
      setCanManageDoctors(auth?.user?.role === 'admin');
    } catch (error) {
      alert('Failed to fetch doctors');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await api.post('/doctors/', newDoctor);
      alert('Doctor registered successfully!');
      setShowModal(false);
      setNewDoctor({ name: '', department: '', specialization: '', available_from: '09:00', available_to: '17:00' });
      fetchDoctors();
    } catch (error) {
      alert(error.message || 'Registration failed');
    }
  };

  const handleDoctorStatus = async (doctor, employmentStatus) => {
    try {
      await api.patch(`/doctors/${doctor.doctor_id}/status`, { employment_status: employmentStatus });
      setDoctorToArchive(null);
      await fetchDoctors();
    } catch (error) {
      alert(error.message || 'Unable to update doctor status');
    }
  };

  const filteredDoctors = doctors.filter(d =>
    d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.specialization.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-clinical-dark">Doctor Management</h1>
          <p className="text-slate-500">Manage the active doctor directory and review resigned, suspended, or duplicate records.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={20}/>
          <span>Add New Doctor</span>
        </button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-xl font-bold text-clinical-dark">Add New Doctor</h2>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                <X size={20} className="text-slate-400"/>
              </button>
            </div>
            <form onSubmit={handleRegister} className="p-6 space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Full Name</label>
                  <input
                    type="text"
                    className="input-field"
                    value={newDoctor.name}
                    onChange={(e) => setNewDoctor({...newDoctor, name: e.target.value})}
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Department</label>
                    <input
                      type="text"
                      className="input-field"
                      value={newDoctor.department}
                      onChange={(e) => setNewDoctor({...newDoctor, department: e.target.value})}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Specialization</label>
                    <input
                      type="text"
                      className="input-field"
                      value={newDoctor.specialization}
                      onChange={(e) => setNewDoctor({...newDoctor, specialization: e.target.value})}
                      required
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Available From</label>
                    <input
                      type="time"
                      className="input-field"
                      value={newDoctor.available_from}
                      onChange={(e) => setNewDoctor({...newDoctor, available_from: e.target.value})}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Available To</label>
                    <input
                      type="time"
                      className="input-field"
                      value={newDoctor.available_to}
                      onChange={(e) => setNewDoctor({...newDoctor, available_to: e.target.value})}
                      required
                    />
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-slate-500 hover:text-slate-700 font-medium"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary px-6">
                  Register Doctor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {doctorToArchive && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-xl font-bold text-clinical-dark">Remove doctor from active directory</h2>
              <button onClick={() => setDoctorToArchive(null)} className="p-2 hover:bg-slate-100 rounded-full">
                <X size={20} className="text-slate-400"/>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-slate-600">Dr. {doctorToArchive.name} will no longer appear in appointment booking. Their past appointments and clinical records will remain available.</p>
              <label className="block text-xs font-bold text-slate-500 uppercase">Reason
                <select className="input-field mt-1" value={archiveReason} onChange={event => setArchiveReason(event.target.value)}>
                  <option value="resigned">Resigned</option>
                  <option value="suspended">Suspended</option>
                  <option value="duplicate">Duplicate record</option>
                </select>
              </label>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setDoctorToArchive(null)} className="px-4 py-2 text-slate-500">Cancel</button>
                <button onClick={() => handleDoctorStatus(doctorToArchive, archiveReason)} className="btn-primary px-5">Remove doctor</button>
              </div>
            </div>
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
              placeholder="Search by name or specialization..."
              className="input-field pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button onClick={() => setDirectoryStatus('active')} className={`px-4 py-2 rounded-lg font-medium ${directoryStatus === 'active' ? 'bg-clinical-blue text-white' : 'border border-slate-200 text-slate-600'}`}>
              Active
            </button>
            <button onClick={() => setDirectoryStatus('archived')} className={`px-4 py-2 rounded-lg font-medium ${directoryStatus === 'archived' ? 'bg-clinical-blue text-white' : 'border border-slate-200 text-slate-600'}`}>
              Removed / suspended
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-20 text-center text-slate-500">Loading doctors...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                <tr className="border-b border-slate-100">
                  <th className="px-6 py-3 font-semibold">Doctor</th>
                  <th className="px-6 py-3 font-semibold">Department</th>
                  <th className="px-6 py-3 font-semibold">Specialization</th>
                  <th className="px-6 py-3 font-semibold">Availability</th>
                  <th className="px-6 py-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDoctors.map((d) => (
                  <tr key={d.doctor_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-clinical-dark">Dr. {d.name}</p>
                      <p className="text-xs text-slate-500">ID: {d.doctor_id}</p>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{d.department}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{d.specialization}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-md text-xs font-bold ${d.employment_status === 'active' ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-700'}`}>
                        {d.employment_status === 'active' ? 'Active' : d.employment_status}
                      </span>
                      {d.status_reason && <p className="text-xs text-slate-400 mt-1">{d.status_reason}</p>}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => navigate(`/doctors/${d.doctor_id}`)}
                          className="text-clinical-blue hover:underline text-sm font-medium"
                        >
                          View
                        </button>
                        {canManageDoctors && (directoryStatus === 'active' ? (
                          <button onClick={() => setDoctorToArchive(d)} className="flex items-center gap-1 text-sm font-medium text-red-700">
                            <Archive size={15}/> Remove
                          </button>
                        ) : (
                          <button onClick={() => handleDoctorStatus(d, 'active')} className="flex items-center gap-1 text-sm font-medium text-emerald-700">
                            <RotateCcw size={15}/> Restore
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredDoctors.length === 0 && (
                  <tr>
                    <td colSpan="5" className="px-6 py-10 text-center text-slate-500">No doctors found.</td>
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

export default Doctors;
