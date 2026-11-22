import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Landmark, Globe, Menu, X } from 'lucide-react';
import { BackendStatusBadge } from '../common/BackendStatusBadge';

export const Header = ({ backendStatus, backendVersion, onRetryBackend }) => {
  const [selectedLanguage, setSelectedLanguage] = useState('English');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const languages = [
    { code: 'en', label: 'English', native: 'English' },
    { code: 'te', label: 'Telugu', native: 'తెలుగు' },
    { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
  ];

  const navLinks = [
    { label: 'Civic Chat', path: '#chat-section' },
    { label: 'Laws & Rights', path: '#laws-section' },
    { label: 'Explore Schemes', path: '#schemes-section' },
    { label: 'Document Intelligence', path: '#documents-section' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-blue-600 flex items-center justify-center text-slate-950 font-bold shadow-lg shadow-teal-500/10 group-hover:scale-105 transition-transform duration-200">
              <Landmark className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white group-hover:text-teal-400 transition-colors">
                  NitiSetu
                </span>
                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/20">
                  Phase 1
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Bridging Citizens with Knowledge • Multilingual Civic Assistant
              </p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-5">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.path}
                className="text-xs font-semibold text-slate-300 hover:text-teal-300 transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Right Action Bar (Status, Language, Mobile Toggle) */}
          <div className="flex items-center gap-3">
            {/* Backend Connectivity Status */}
            <div className="hidden sm:block">
              <BackendStatusBadge
                status={backendStatus}
                version={backendVersion}
                onRetry={onRetryBackend}
              />
            </div>

            {/* Language Selector */}
            <div className="relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-slate-200">
              <Globe className="w-3.5 h-3.5 text-teal-400" />
              <select
                aria-label="Select Language"
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none cursor-pointer pr-1"
              >
                {languages.map((lang) => (
                  <option
                    key={lang.code}
                    value={lang.label}
                    className="bg-slate-900 text-slate-100"
                  >
                    {lang.native} ({lang.label})
                  </option>
                ))}
              </select>
            </div>

            {/* Mobile menu button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden px-4 pt-2 pb-4 bg-slate-900 border-b border-slate-800 space-y-2">
          <div className="py-2 mb-2 border-b border-slate-800">
            <BackendStatusBadge
              status={backendStatus}
              version={backendVersion}
              onRetry={onRetryBackend}
            />
          </div>
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.path}
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800"
            >
              {link.label}
            </a>
          ))}
        </div>
      )}
    </header>
  );
};
