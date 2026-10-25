import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Search, FileText } from 'lucide-react';
import { api } from '../api';

const EHR = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/patients/?status=all')
      .then(setPatients)
      .catch((requestError) => setError(requestError.message || 'Unable to load patient records.'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = patients.filter((patient) =>
    patient.name.toLowerCase().includes(search.toLowerCase()) ||
    patient.phone.includes(search) ||
    String(patient.patient_id).includes(search)
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-clinical-dark flex items-center gap-2">
          <Activity className="text-clinical-blue"/> Electronic Health Records
        </h1>
        <p className="text-slate-500">Choose a patient to review their clinical notes, prescriptions, and lab results.</p>
      </div>

      <div className="card">
        <div className="relative mb-5">
          <Search size={18} className="absolute left-3 top-3 text-slate-400"/>
          <input
            className="input-field pl-10"
            placeholder="Search by patient name, phone, or ID"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        {loading ? (
          <p className="py-10 text-center text-slate-500">Loading patient records…</p>
        ) : error ? (
          <p className="py-10 text-center text-red-600">{error}</p>
        ) : filtered.length === 0 ? (
          <p className="py-10 text-center text-slate-500">No patients match this search.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {filtered.map((patient) => (
              <button
                key={patient.patient_id}
                onClick={() => navigate(`/patients/${patient.patient_id}`)}
                className="w-full flex items-center justify-between py-4 text-left hover:bg-slate-50 px-2 rounded-lg"
              >
                <span>
                  <span className="block font-semibold text-clinical-dark">{patient.name}</span>
                  <span className="text-sm text-slate-500">Patient #{patient.patient_id} · {patient.phone}{patient.is_cured ? ' · Cured' : ''}</span>
                </span>
                <span className="flex items-center gap-2 text-sm font-medium text-clinical-blue">
                  <FileText size={17}/> Open record
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default EHR;
