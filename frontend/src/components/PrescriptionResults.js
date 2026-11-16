import React from 'react';
import { FileText, Pill, Plus } from 'lucide-react';

const PrescriptionResults = ({ prescriptions, labs, onAddPrescription, onAddLab }) => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Pill size={20} className="text-clinical-blue"/> Active Prescriptions
          </h2>
          {onAddPrescription && <button onClick={onAddPrescription} className="btn-primary py-1 px-3 text-xs flex items-center gap-1">
            <Plus size={14}/> Add
          </button>}
        </div>
        <div className="space-y-3">
          {prescriptions.length === 0 ? (
            <p className="text-sm text-slate-500">No active prescriptions.</p>
          ) : (
            prescriptions.map((p) => (
              <div key={p.prescription_id} className="p-3 bg-slate-50 rounded-xl border border-slate-100">
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
          {onAddLab && <button onClick={onAddLab} className="btn-primary py-1 px-3 text-xs flex items-center gap-1">
            <Plus size={14}/> Add
          </button>}
        </div>
        <div className="space-y-3">
          {labs.length === 0 ? (
            <p className="text-sm text-slate-500">No laboratory results found.</p>
          ) : (
            labs.map((l) => (
              <div key={l.lab_id} className="p-3 bg-slate-50 rounded-xl border border-slate-100">
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
);

export default PrescriptionResults;
