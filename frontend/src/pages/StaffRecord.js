import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api';
import PrescriptionResults from '../components/PrescriptionResults';

const StaffRecord = () => {
  const { id } = useParams();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setRecord(null);
    setError('');
    Promise.all([
      api.get(`/patients/directory/${id}`),
      api.get(`/clinical/prescriptions/${id}`),
      api.get(`/clinical/labs/${id}`),
    ]).then(([patient, prescriptions, labs]) => {
      if (active) setRecord({ patient, prescriptions, labs });
    }).catch((failure) => {
      if (active) setError(failure.message);
    });
    return () => { active = false; };
  }, [id]);

  return (
    <div className="space-y-6">
      <Link to="/ehr" className="inline-flex items-center gap-2 font-medium text-clinical-blue"><ArrowLeft size={18}/> Back to records</Link>
      {error && <p role="alert" className="text-rose-700">{error}</p>}
      {!error && !record && <p role="status">Loading patient record…</p>}
      {record && <>
        <header>
          <h1 className="text-2xl font-bold">{record.patient.name}</h1>
          <p className="text-slate-500">Patient #{record.patient.patient_id}</p>
        </header>
        <PrescriptionResults prescriptions={record.prescriptions} labs={record.labs}/>
      </>}
    </div>
  );
};

export default StaffRecord;
