import React, { useEffect, useRef, useState } from 'react';
import { Link, Navigate, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  UserRound,
  UserPlus,
  CalendarDays,
  FileText,
  CreditCard,
  BarChart3,
  LogOut,
  Search,
  X,
  ChevronDown,
  History as HistoryIcon,
  LogOut as SwitchAccountIcon,
} from 'lucide-react';
import { api } from '../api';
import { canReadStaffRecords, canRunOperations, isClinician, roleLabel } from '../access';

const Layout = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState({ patients: [], doctors: [] });
  const [searching, setSearching] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);
  const [profile, setProfile] = useState(null);
  const [profileError, setProfileError] = useState('');
  const [signingOut, setSigningOut] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileForm, setProfileForm] = useState({ username: '', display_name: '', current_password: '', new_password: '' });
  const [localClock, setLocalClock] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setLocalClock(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!localStorage.getItem('access_token')) return;
    api.get('/auth/profile')
      .then((data) => {
        setProfile(data);
        setProfileForm({ username: data.username, display_name: data.display_name || data.username, current_password: '', new_password: '' });
      })
      .catch((error) => setProfileError(error.message || 'Unable to load your account.'));
  }, []);

  useEffect(() => {
    const term = searchTerm.trim();
    if (term.length < 2) {
      setSearchResults({ patients: [], doctors: [] });
      setSearching(false);
      return undefined;
    }

    let cancelled = false;
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await api.get(`/search?q=${encodeURIComponent(term)}`);
        if (!cancelled) setSearchResults(results);
      } catch (error) {
        if (!cancelled) setSearchResults({ patients: [], doctors: [], error: error.message });
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [searchTerm]);

  const openResult = (type, id) => {
    if (type === 'patient') navigate(`/patients/${id}`);
    else if (isClinician(profile?.role)) navigate(`/doctors/${id}`);
    setSearchTerm('');
    setSearchOpen(false);
  };

  const flattenedResults = [
    ...(searchResults.patients || []).map((patient) => ({
      type: 'patient', id: patient.patient_id, title: patient.name,
      detail: `Patient #${patient.patient_id} · ${patient.phone}`
    })),
    ...(isClinician(profile?.role) ? searchResults.doctors || [] : []).map((doctor) => ({
      type: 'doctor', id: doctor.doctor_id, title: `Dr. ${doctor.name}`,
      detail: `${doctor.specialization} · ${doctor.department}`
    }))
  ];

  const handleSearchKeyDown = (event) => {
    if (event.key === 'Escape') setSearchOpen(false);
    if (event.key === 'Enter' && flattenedResults.length) {
      openResult(flattenedResults[0].type, flattenedResults[0].id);
    }
  };

  const openProfileEditor = () => {
    setProfileForm({
      username: profile?.username || '',
      display_name: profile?.display_name || profile?.username || '',
      current_password: '',
      new_password: ''
    });
    setProfileModalOpen(true);
    setAccountMenuOpen(false);
  };

  const saveProfile = async (event) => {
    event.preventDefault();
    setProfileSaving(true);
    try {
      const payload = { username: profileForm.username, display_name: profileForm.display_name };
      if (profileForm.new_password) {
        payload.current_password = profileForm.current_password;
        payload.new_password = profileForm.new_password;
      }
      const updated = await api.put('/auth/profile', payload);
      if (updated.access_token) localStorage.setItem('access_token', updated.access_token);
      setProfile(updated);
      setProfileModalOpen(false);
    } catch (error) {
      alert(error.message || 'Unable to update profile');
    } finally {
      setProfileSaving(false);
    }
  };

  const switchAccount = async () => {
    setSigningOut(true);
    try {
      await api.post('/logout');
    } catch (error) {
      console.error('Could not end the server session:', error);
    } finally {
      localStorage.removeItem('access_token');
      setAccountMenuOpen(false);
      navigate('/', { replace: true });
    }
  };

  if (!localStorage.getItem('access_token')) return <Navigate to="/" replace/>;
  if (!profile) return <div className="p-8" role={profileError ? 'alert' : 'status'}>
    {profileError || 'Loading account…'}
    {profileError && <button className="ml-4 btn-primary" onClick={() => window.location.reload()}>Retry</button>}
  </div>;

  const menuItems = [
    { name: 'Dashboard', icon: <LayoutDashboard size={20}/>, path: '/dashboard', allowed: isClinician },
    { name: 'Patients', icon: <Users size={20}/>, path: '/patients', allowed: canRunOperations },
    { name: 'Doctors', icon: <UserRound size={20}/>, path: '/doctors', allowed: isClinician },
    { name: 'Appointments', icon: <CalendarDays size={20}/>, path: '/appointments', allowed: canReadStaffRecords },
    { name: 'Staff Assignments', icon: <UserPlus size={20}/>, path: '/staff', allowed: (role) => role === 'admin' },
    { name: 'Reports', icon: <BarChart3 size={20}/>, path: '/reports', allowed: isClinician },
    { name: 'Billing', icon: <CreditCard size={20}/>, path: '/billing', allowed: canRunOperations },
    { name: isClinician(profile.role) ? 'EHR' : 'Prescriptions & labs', icon: <FileText size={20}/>, path: '/ehr', allowed: canReadStaffRecords },
    { name: 'History', icon: <HistoryIcon size={20}/>, path: '/history', allowed: isClinician },
  ];

  return (
    <div className="flex h-screen bg-clinical-light">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-clinical-blue rounded-lg flex items-center justify-center text-white font-bold">M</div>
          <span className="text-xl font-bold text-clinical-dark tracking-tight">Medora</span>
        </div>

        <nav className="flex-1 overflow-y-auto px-4 space-y-1">
          {menuItems.filter((item) => item.allowed(profile.role)).map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className="flex items-center gap-3 px-3 py-2 text-slate-600 hover:bg-blue-50 hover:text-clinical-blue rounded-xl transition-all group"
            >
              <span className="text-slate-400 group-hover:text-clinical-blue">{item.icon}</span>
              <span className="font-medium">{item.name}</span>
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-100">
          <button onClick={switchAccount} disabled={signingOut} className="flex items-center gap-3 px-3 py-2 w-full text-slate-600 hover:bg-red-50 hover:text-red-600 rounded-xl transition-all group">
            <LogOut size={20} className="text-slate-400 group-hover:text-red-600"/>
            <span className="font-medium">{signingOut ? 'Signing out…' : 'Logout'}</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between">
          {canRunOperations(profile.role) ? <div className="relative w-96" ref={searchRef}>
            <input
              type="text"
              role="combobox"
              aria-expanded={searchOpen && searchTerm.trim().length >= 2}
              aria-controls="global-search-results"
              placeholder={isClinician(profile.role) ? 'Search patients, doctors...' : 'Search patients...'}
              className="w-full pl-10 pr-10 py-2 bg-slate-100 border-none rounded-full text-sm focus:ring-2 focus:ring-clinical-blue transition-all"
              value={searchTerm}
              onChange={(event) => { setSearchTerm(event.target.value); setSearchOpen(true); }}
              onFocus={() => setSearchOpen(true)}
              onKeyDown={handleSearchKeyDown}
            />
            <Search size={17} className="absolute left-3 top-2.5 text-slate-400"/>
            {searchTerm && <button onClick={() => { setSearchTerm(''); setSearchResults({ patients: [], doctors: [] }); }} className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-700" aria-label="Clear search"><X size={17}/></button>}
            {searchOpen && searchTerm.trim().length >= 2 && (
              <div id="global-search-results" role="listbox" className="absolute z-50 top-12 left-0 right-0 bg-white rounded-xl border border-slate-200 shadow-xl overflow-hidden">
                {searching ? (
                  <p className="px-4 py-3 text-sm text-slate-500">Searching…</p>
                ) : searchResults.error ? (
                  <p className="px-4 py-3 text-sm text-red-600">{searchResults.error}</p>
                ) : flattenedResults.length ? (
                  <div className="max-h-80 overflow-y-auto py-1">
                    {flattenedResults.map((result) => (
                      <button
                        key={`${result.type}-${result.id}`}
                        role="option"
                        aria-selected="false"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => openResult(result.type, result.id)}
                        className="w-full px-4 py-3 text-left hover:bg-blue-50 flex flex-col"
                      >
                        <span className="text-sm font-semibold text-clinical-dark">{result.title}</span>
                        <span className="text-xs text-slate-500">{result.detail}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="px-4 py-3 text-sm text-slate-500">No matching patients or active doctors.</p>
                )}
              </div>
            )}
          </div> : <div/>}

          <time
            dateTime={localClock.toISOString()}
            aria-label={`Local date and time: ${localClock.toLocaleString()}`}
            className="hidden text-right sm:block"
          >
            <span className="block text-sm font-semibold tabular-nums text-clinical-dark">
              {new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(localClock)}
            </span>
            <span className="block text-xs text-slate-500">
              {new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(localClock)} · Local time
            </span>
          </time>

          <div className="relative">
            <button onClick={() => setAccountMenuOpen(!accountMenuOpen)} className="flex items-center gap-3 rounded-xl p-1.5 hover:bg-slate-50">
              <div className="text-right">
                <p className="text-sm font-bold text-clinical-dark">{profile?.display_name || profile?.username || 'Account'}</p>
                <p className="text-xs text-slate-500">{roleLabel(profile?.role)}</p>
              </div>
              <div className="w-10 h-10 bg-clinical-blue text-white rounded-full flex items-center justify-center font-bold border-2 border-white shadow-sm">
                {(profile?.display_name || profile?.username || 'A').trim().charAt(0).toUpperCase()}
              </div>
              <ChevronDown size={16} className="text-slate-400"/>
            </button>
            {accountMenuOpen && (
              <div className="absolute z-40 right-0 top-14 w-52 rounded-xl border border-slate-200 bg-white shadow-xl py-2">
                <button onClick={openProfileEditor} className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-blue-50 flex items-center gap-2">
                  <UserRound size={16}/> Edit profile
                </button>
                <button onClick={switchAccount} disabled={signingOut} className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-red-50 flex items-center gap-2">
                  <SwitchAccountIcon size={16}/> Switch account
                </button>
              </div>
            )}
          </div>
        </header>

        {profileModalOpen && (
          <div className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl overflow-hidden">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-clinical-dark">Edit profile</h2>
                  <p className="text-sm text-slate-500">Update your account name and sign-in details.</p>
                </div>
                <button onClick={() => setProfileModalOpen(false)} className="p-2 rounded-full hover:bg-slate-100" aria-label="Close profile editor"><X size={20}/></button>
              </div>
              <form onSubmit={saveProfile} className="p-6 space-y-4">
                <label className="block text-xs font-bold uppercase text-slate-500">Display name
                  <input className="input-field mt-1" value={profileForm.display_name} onChange={event => setProfileForm({...profileForm, display_name: event.target.value})} required maxLength={120}/>
                </label>
                <label className="block text-xs font-bold uppercase text-slate-500">Username
                  <input className="input-field mt-1" value={profileForm.username} onChange={event => setProfileForm({...profileForm, username: event.target.value})} required minLength={3} maxLength={64}/>
                </label>
                <div className="border-t border-slate-100 pt-4">
                  <p className="text-sm font-semibold text-slate-700 mb-3">Change password <span className="font-normal text-slate-400">(optional)</span></p>
                  <div className="space-y-3">
                    <input type="password" className="input-field" placeholder="Current password" autoComplete="current-password" value={profileForm.current_password} onChange={event => setProfileForm({...profileForm, current_password: event.target.value})}/>
                    <input type="password" className="input-field" placeholder="New password (8+ characters)" autoComplete="new-password" minLength={8} value={profileForm.new_password} onChange={event => setProfileForm({...profileForm, new_password: event.target.value})}/>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setProfileModalOpen(false)} className="px-4 py-2 text-slate-500">Cancel</button>
                  <button type="submit" disabled={profileSaving} className="btn-primary px-5 disabled:opacity-50">{profileSaving ? 'Saving…' : 'Save profile'}</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <Outlet context={profile}/>
        </div>
      </main>
    </div>
  );
};

export default Layout;
