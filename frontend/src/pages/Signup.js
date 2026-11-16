import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { roleLabel } from '../access';

const emptyForm = { username: '', password: '', display_name: '', role: 'receptionist', doctor_id: '' };

const Signup = () => {
  const [form, setForm] = useState(emptyForm);
  const [staff, setStaff] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editing, setEditing] = useState(null);
  const accountForm = useRef(null);

  useEffect(() => {
    Promise.all([api.get('/staff'), api.get('/doctors/')])
      .then(([accounts, directory]) => { setStaff(accounts); setDoctors(directory); })
      .catch((failure) => setError(failure.message))
      .finally(() => setLoading(false));
  }, []);

  const availableDoctors = doctors.filter((doctor) =>
    !staff.some((user) => user.doctor_id === doctor.doctor_id && user.user_id !== editing?.user_id)
  );

  const change = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value, ...(name === 'role' ? { doctor_id: '' } : {}) }));
  };

  const editAssignment = (account) => {
    setEditing(account);
    setNotice('');
    setError('');
    setForm({ ...emptyForm, role: account.role, doctor_id: account.doctor_id ?? '' });
    accountForm.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  };

  const clearEditing = () => {
    setEditing(null);
    setForm(emptyForm);
    setError('');
  };

  const saveAccount = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const access = { role: form.role, doctor_id: form.role === 'doctor' ? Number(form.doctor_id) : null };
      const doctorName = doctors.find((doctor) => doctor.doctor_id === access.doctor_id)?.name;
      if (editing) {
        await api.patch(`/staff/${editing.user_id}/assignment`, access);
        setStaff((current) => current.map((account) => account.user_id === editing.user_id
          ? { ...account, ...access, doctor_name: doctorName }
          : account));
        const changed = editing.role !== access.role || editing.doctor_id !== access.doctor_id;
        setNotice(changed
          ? `Assignment updated for ${editing.username}. They’ll need to sign in again.`
          : `Assignment for ${editing.username} is up to date.`);
        clearEditing();
        return;
      }
      const result = await api.post('/signup', {
        ...form,
        username: form.username.trim(),
        display_name: form.display_name.trim(),
        ...access,
      });
      setStaff((current) => [...current, {
        user_id: result.user_id,
        username: form.username.trim().toLowerCase(),
        display_name: form.display_name.trim(),
        ...access,
        doctor_name: doctorName,
      }]);
      setNotice(`Account created for ${form.username.trim().toLowerCase()}.`);
      setForm(emptyForm);
    } catch (failure) {
      setError(failure.message || 'Unable to save the account.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="card max-w-2xl space-y-4" ref={accountForm}>
        <h2 className="text-lg font-bold">{editing ? `Edit assignment for ${editing.display_name}` : 'Create a staff account'}</h2>
        {editing && <p className="text-sm text-slate-600">A role change signs this user out and clears their appointment assignments for the previous role from booked appointments.</p>}
        <form onSubmit={saveAccount} className="grid gap-4 sm:grid-cols-2">
          {!editing && <label className="block text-sm font-medium">Display name
            <input className="input-field mt-1" name="display_name" value={form.display_name} onChange={change} maxLength={120} required/>
          </label>}
          {!editing && <label className="block text-sm font-medium">Username
            <input className="input-field mt-1" name="username" value={form.username} onChange={change} autoComplete="off" minLength={3} maxLength={64} required/>
          </label>}
          <label className="block text-sm font-medium">Role
            <select className="input-field mt-1" name="role" value={form.role} onChange={change}>
              <option value="receptionist">Receptionist</option>
              <option value="nurse">Nurse</option>
              <option value="doctor">Doctor</option>
            </select>
          </label>
          {!editing && <label className="block text-sm font-medium">Password
            <input className="input-field mt-1" type="password" name="password" value={form.password} onChange={change} autoComplete="new-password" minLength={8} maxLength={72} required/>
          </label>}
          {form.role === 'doctor' && (
            <label className="block text-sm font-medium sm:col-span-2">Doctor profile
              <select className="input-field mt-1" name="doctor_id" value={form.doctor_id} onChange={change} required>
                <option value="">Select a registered doctor</option>
                {availableDoctors.map((doctor) => <option key={doctor.doctor_id} value={doctor.doctor_id}>{doctor.name} · {doctor.department}</option>)}
              </select>
              {!availableDoctors.length && <span className="mt-1 block text-slate-500">Register a doctor under Doctors first, or select a doctor without an account.</span>}
            </label>
          )}
          <div className="sm:col-span-2">
            {error && <p role="alert" className="mb-3 text-sm text-rose-700">{error}</p>}
            {notice && <p role="status" className="mb-3 text-sm text-emerald-700">{notice}</p>}
            <button className="btn-primary" type="submit" disabled={saving || loading}>{saving ? 'Saving…' : editing ? 'Save assignment' : 'Create account'}</button>
            {editing && <button type="button" className="ml-3 rounded-lg px-4 py-2 text-slate-700" onClick={clearEditing} disabled={saving}>Cancel</button>}
          </div>
        </form>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="mb-4 text-lg font-bold">Staff accounts</h2>
        {loading ? <p role="status">Loading accounts…</p> : (
          <table className="w-full text-left text-sm">
            <thead className="text-slate-600"><tr><th>Display name</th><th>Username</th><th>Role</th><th>Doctor profile</th><th>Assignment</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {staff.map((account) => (
                <tr key={account.user_id}>
                  <td className="py-3 font-medium">{account.display_name}</td>
                  <td>{account.username}</td>
                  <td>{roleLabel(account.role)}</td>
                  <td>{account.doctor_name || '—'}</td>
                  <td>{account.role !== 'admin' && <button type="button" onClick={() => editAssignment(account)} disabled={saving} className="py-2 font-semibold text-clinical-blue hover:underline">Edit assignment</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

export default Signup;
