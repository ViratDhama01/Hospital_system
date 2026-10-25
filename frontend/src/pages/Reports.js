import React, { useState, useEffect } from 'react';
import { FileText, TrendingUp, DollarSign, UserCheck, RefreshCw } from 'lucide-react';
import { api } from '../api';

const Reports = () => {
  const [stats, setStats] = useState({
    totalRevenue: 0,
    totalPatients: 0,
    outstanding: 0
  });
  const [footfall, setFootfall] = useState([]);
  const [peakHours, setPeakHours] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReports(true);
    const timer = setInterval(() => fetchReports(false), 30000);
    return () => clearInterval(timer);
  }, []);

  const fetchReports = async (saveSnapshot = true) => {
    setLoading(true);
    try {
      const [financials, deptFootfall, peakHoursData] = await Promise.all([
        api.get('/reports/financials'),
        api.get('/reports/department-footfall'),
        api.get('/reports/peak-hours')
      ]);
      if (saveSnapshot) await api.post('/reports/snapshot', {});

      setStats({
        totalRevenue: financials.total_collected || 0,
        totalPatients: (await api.get('/patients/')).length || 0,
        outstanding: financials.outstanding || 0
      });
      setFootfall(deptFootfall);
      setPeakHours(peakHoursData);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      alert(error.message || 'Unable to load reports. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-clinical-dark">Analytics & Reports</h1>
          <p className="text-slate-500">Hospital performance and financial insights.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">Auto-refreshes every 30 seconds</span>
          <button
            onClick={fetchReports}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={20} className={loading ? 'animate-spin' : ''}/>
            <span>Refresh Data</span>
          </button>
          <button className="btn-primary flex items-center gap-2">
            <FileText size={20}/>
            <span>Export PDF Report</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center">
            <TrendingUp size={24}/>
          </div>
          <div>
            <p className="text-sm text-slate-500">Total Revenue</p>
            <h3 className="text-xl font-bold">₹{stats.totalRevenue.toLocaleString()}</h3>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center">
            <UserCheck size={24}/>
          </div>
          <div>
            <p className="text-sm text-slate-500">Patient Load</p>
            <h3 className="text-xl font-bold">{stats.totalPatients} Patients</h3>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-2xl flex items-center justify-center">
            <DollarSign size={24}/>
          </div>
          <div>
            <p className="text-sm text-slate-500">Outstanding</p>
            <h3 className="text-xl font-bold">₹{stats.outstanding.toLocaleString()}</h3>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card">
          <h2 className="text-lg font-bold mb-4">Departmental Footfall</h2>
          <div className="space-y-4">
            {loading ? (
              <div className="py-10 text-center text-slate-400">Loading footfall data...</div>
            ) : footfall.length === 0 ? (
              <div className="py-10 text-center text-slate-400">No footfall data available.</div>
            ) : (
              footfall.map((dept) => (
                <div key={dept.department} className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">{dept.department}</span>
                  <div className="flex items-center gap-4">
                  <div className="w-48 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-clinical-blue"
                      style={{ width: `${Math.max(...footfall.map((item) => item.total_visits), 1) ? Math.max((dept.total_visits / Math.max(...footfall.map((item) => item.total_visits), 1)) * 100, 4) : 4}%` }}
                      ></div>
                    </div>
                    <span className="text-xs font-bold text-slate-500">{dept.total_visits} visits</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-bold mb-4">Peak Hours</h2>
          {loading ? (
            <div className="py-10 text-center text-slate-400">Loading peak hours...</div>
          ) : peakHours.length === 0 ? (
            <div className="py-10 text-center text-slate-400">No peak hour data available.</div>
          ) : (
            <div className="flex items-end justify-between h-40 gap-2 px-4">
              {peakHours.map((hour, i) => (
                <div key={i} className="flex flex-col items-center gap-2 w-full">
                  <div
                    className="w-full bg-clinical-blue rounded-t-md transition-all hover:bg-blue-700"
                    style={{ height: `${Math.min((hour.appointment_count / 50) * 100, 100)}%` }}
                  ></div>
                  <span className="text-[10px] text-slate-400">{hour.hour}:00</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Reports;
