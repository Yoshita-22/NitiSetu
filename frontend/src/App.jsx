import React, { useState, useEffect, useCallback } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { Home } from './pages/Home';
import { checkBackendHealth } from './services/api';

export const App = () => {
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'
  const [backendVersion, setBackendVersion] = useState(null);

  const verifyHealth = useCallback(async () => {
    setBackendStatus('checking');
    try {
      const result = await checkBackendHealth();
      if (result.success && result.data?.status === 'healthy') {
        setBackendStatus('connected');
        setBackendVersion(result.data.version || '1.0.0');
      } else {
        setBackendStatus('disconnected');
        setBackendVersion(null);
      }
    } catch {
      setBackendStatus('disconnected');
      setBackendVersion(null);
    }
  }, []);

  useEffect(() => {
    verifyHealth();
  }, [verifyHealth]);

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 selection:bg-teal-500 selection:text-slate-950">
      <Header
        backendStatus={backendStatus}
        backendVersion={backendVersion}
        onRetryBackend={verifyHealth}
      />
      <main className="flex-1">
        <Routes>
          <Route
            path="/"
            element={
              <Home
                backendStatus={backendStatus}
                backendVersion={backendVersion}
                onRetryBackend={verifyHealth}
              />
            }
          />
        </Routes>
      </main>
      <Footer />
    </div>
  );
};

export default App;
