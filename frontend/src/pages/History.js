import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History as HistoryIcon, RefreshCw, Search } from 'lucide-react';
import { api } from '../api';

const History = () => {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [category, setCategory] = useState('All');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const data = await api.get('/history/');
      setEvents(data.events || []);
      setError('');
    } catch (requestError) {
      setError(requestError.message || 'Unable to load record history.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 30000);
    return () => clearInterval(timer);
  }, [refresh]);

  const categories = useMemo(() => ['All', ...new Set(events.map((event) => event.category))], [events]);
  const filteredEvents = useMemo(() => {
    const term = search.trim().toLowerCase();
    return events.filter((event) => (category === 'All' || event.category === category) &&
      (!term || `${event.title} ${event.detail} ${event.record_id} ${event.patient_id || ''}`.toLowerCase().includes(term)));
  }, [events, category, search]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><h1 className="flex items-center gap-2 text-2xl font-bold text-clinical-dark"><HistoryIcon className="text-clinical-blue"/>Hospital History</h1><p className="text-slate-500">Appointments, patients, doctors, billing, reports, and clinical records from saved data.</p></div>
        <button onClick={refresh} className="btn-secondary flex items-center gap-2"><RefreshCw size={17} className={loading ? 'animate-spin' : ''}/>Refresh</button>
      </div>

      {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      <div className="card space-y-4">
        <div className="flex flex-col gap-3 md:flex-row">
          <div className="relative flex-1"><Search size={17} className="absolute left-3 top-3 text-slate-400"/><input className="input-field pl-10" placeholder="Search the record history" value={search} onChange={(event) => setSearch(event.target.value)}/></div>
          <select className="input-field md:w-56" value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter history by category">{categories.map((item) => <option key={item}>{item}</option>)}</select>
        </div>

        {loading && events.length === 0 ? <p className="py-12 text-center text-slate-500">Loading history…</p> : error && events.length === 0 ? null : filteredEvents.length === 0 ? <p className="py-12 text-center text-slate-500">No records match this history filter.</p> : (
          <div className="divide-y divide-slate-100">
            {filteredEvents.map((event, index) => (
              <div key={`${event.category}-${event.record_id}-${index}`} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-bold uppercase text-clinical-blue">{event.category}</span>
                    <span className="text-xs text-slate-400">Record #{event.record_id}</span>
                  </div>
                  <p className="font-semibold text-clinical-dark">{event.title}</p>
                  <p className="break-words text-sm text-slate-600">{event.detail}</p>
                  {event.patient_id && <button onClick={() => navigate(`/patients/${event.patient_id}`)} className="mt-1 text-xs font-medium text-clinical-blue hover:underline">Open patient #{event.patient_id}</button>}
                </div>
                <time className="shrink-0 text-xs text-slate-500" dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time>
              </div>
            ))}
          </div>
        )}
        <p className="border-t border-slate-100 pt-3 text-xs text-slate-400">Showing up to 500 saved events. The list refreshes every 30 seconds.</p>
      </div>
    </div>
  );
};

export default History;
