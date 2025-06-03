import React, { useState } from 'react';

// Add this import for your logo image
import appLogo from '../assets/app_logo.jpg';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGmailLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await fetch(`${API_BASE_URL}/auth/google`, { method: 'POST' });
      if (!resp.ok) throw new Error('Failed to get auth URL');
      const data = await resp.json();
      window.location.href = data.auth_url;
    } catch (err: any) {
      setError('Could not start authentication. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-br from-indigo-400 to-purple-500">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
        <div className="text-center mb-6">
          {/* App logo above the title */}
          <img src={appLogo} alt="App Logo" className="mx-auto mb-4 w-20 h-20 rounded-full object-cover" />
          <h1 className="text-3xl font-bold text-indigo-700 mb-2">Gmail Auto-Responder</h1>
          <p className="text-gray-600">AI-powered intelligent email replies</p>
        </div>
        <button
          onClick={handleGmailLogin}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg shadow transition mb-4"
        >
          <svg width="24" height="24" viewBox="0 0 48 48" className="inline-block" xmlns="http://www.w3.org/2000/svg">
            <g>
              <path fill="#4285F4" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.4-5.7 7.5-11.3 7.5-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.1 8.1 3.1l6.1-6.1C34.5 5.1 29.5 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21c10.5 0 20-7.5 20-21 0-1.4-.2-2.4-.4-3.5z"/>
              <path fill="#34A853" d="M6.3 14.7l6.6 4.8C14.5 16.1 19.4 13 24 13c3.1 0 5.9 1.1 8.1 3.1l6.1-6.1C34.5 5.1 29.5 3 24 3c-7.1 0-13.2 3.7-16.7 9.7z"/>
              <path fill="#FBBC05" d="M24 44c5.5 0 10.4-1.8 14.2-4.9l-6.6-5.4C29.7 35.6 27 36.5 24 36.5c-5.7 0-10.6-3.9-12.3-9.2l-7 5.4C7.8 39.2 15.3 44 24 44z"/>
              <path fill="#EA4335" d="M43.6 20.5H42V20H24v8h11.3c-0.7 2-2.1 3.7-3.9 4.9l6.6 5.4C41.8 37.6 44 31.2 44 24c0-1.4-.2-2.4-.4-3.5z"/>
            </g>
          </svg>
          {loading ? 'Redirecting...' : 'Login with Gmail'}
        </button>
        {error && <div className="text-red-600 text-center mb-2">{error}</div>}
        <div className="text-xs text-gray-500 text-center mt-4">
          🔒 Your data is secure and private. We only access emails you explicitly choose to respond to.
        </div>
      </div>
    </div>
  );
};

export default LoginPage;