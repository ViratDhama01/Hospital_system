import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { homeForRole } from '../access';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await api.post('/login', { username, password });
      if (!data.access_token) throw new Error('No sign-in session was returned.');
      localStorage.setItem('access_token', data.access_token);
      navigate(homeForRole(data.user.role), { replace: true });
    } catch (requestError) {
      setError(requestError.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex items-center justify-center bg-clinical-light">
      <div className="card w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-clinical-blue rounded-2xl flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4 shadow-lg">
            M
          </div>
          <h1 className="text-2xl font-bold text-clinical-dark">Welcome to Medora</h1>
          <p className="text-slate-500">Please sign in to your account</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="login-username" className="block text-sm font-medium text-slate-700 mb-1">Username</label>
            <input
              id="login-username"
              autoComplete="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field"
              placeholder="Enter your username"
              required
            />
          </div>

          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              id="login-password"
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              placeholder="••••••••"
              required
            />
          </div>

          {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 mt-6 shadow-lg shadow-blue-200 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">Need an account? Contact your Medora administrator.</p>
      </div>
    </div>
  );
};

export default Login;
