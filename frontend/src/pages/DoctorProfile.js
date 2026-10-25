import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Save, Activity } from 'lucide-react';
import { api } from '../api';

const DoctorProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doctor, setDoctor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    fetchDoctor();
  }, [id]);

  const fetchDoctor = async () => {
    try {
      const data = await api.get(`/doctors/${id}`);
      setDoctor(data);
      setEditForm(data);
    } catch (error) {
      alert('Failed to fetch doctor profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await api.patch(`/doctors/${id}`, editForm);
      alert('Doctor profile updated successfully!');
      setIsEditing(false);
      fetchDoctor();
    } catch (error) {
      alert(error.message || 'Update failed');
    }
  };

  if (loading) return <div className="p-8 text-center">Loading profile...</div>;
  if (!doctor) return <div className="p-8 text-center">Doctor not found.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/doctors')} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-clinical-dark">Dr. {doctor.name}</h1>
            <p className="text-slate-500">{doctor.specialization} • {doctor.department}</p>
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
            <User size={20} className="text-clinical-blue"/> Profile Details
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase">Full Name</label>
              {isEditing ? (
                <input
                  className="input-field mt-1"
                  value={editForm.name}
                  onChange={e => setEditForm({...editForm, name: e.target.value})}
                />
              ) : <p className="font-medium">{doctor.name}</p>}
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase">Department</label>
              {isEditing ? (
                <input
                  className="input-field mt-1"
                  value={editForm.department}
                  onChange={e => setEditForm({...editForm, department: e.target.value})}
                />
              ) : <p className="font-medium">{doctor.department}</p>}
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase">Specialization</label>
              {isEditing ? (
                <input
                  className="input-field mt-1"
                  value={editForm.specialization}
                  onChange={e => setEditForm({...editForm, specialization: e.target.value})}
                />
              ) : <p className="font-medium">{doctor.specialization}</p>}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">From</label>
                {isEditing ? (
                  <input
                    type="time"
                    className="input-field mt-1"
                    value={editForm.available_from}
                    onChange={e => setEditForm({...editForm, available_from: e.target.value})}
                  />
                ) : <p className="font-medium">{doctor.available_from}</p>}
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase">To</label>
                {isEditing ? (
                  <input
                    type="time"
                    className="input-field mt-1"
                    value={editForm.available_to}
                    onChange={e => setEditForm({...editForm, available_to: e.target.value})}
                  />
                ) : <p className="font-medium">{doctor.available_to}</p>}
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Activity size={20} className="text-clinical-blue"/> Appointment Load
            </h2>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
              <p className="text-sm text-slate-600 italic">Patient load analytics will appear here.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DoctorProfile;
