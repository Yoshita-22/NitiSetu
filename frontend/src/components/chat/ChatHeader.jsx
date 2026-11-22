import React from 'react';
import {
  Landmark,
  Globe,
  PanelLeftOpen,
  PanelLeftClose,
  Plus,
  Wifi,
  WifiOff,
} from 'lucide-react';

const languages = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'te', label: 'Telugu', native: 'తెలుగు' },
  { code: 'hi', label: 'Hindi', native: 'हिंदी' },
];

export const ChatHeader = ({
  language,
  onLanguageChange,
  onNewChat,
  onToggleSidebar,
  backendStatus,
}) => {
  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-slate-800/60 bg-navy-950/80 backdrop-blur-sm flex-shrink-0">
      {/* Left: Sidebar toggle + Logo */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          title="Toggle conversation history"
        >
          <PanelLeftOpen className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center shadow-lg shadow-teal-500/10">
            <Landmark className="w-4 h-4 text-white" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-base font-bold text-white leading-none tracking-tight">
              NitiSetu
            </h1>
            <p className="text-[10px] text-slate-500 leading-none mt-0.5">
              Bridging Citizens with Knowledge
            </p>
          </div>
        </div>
      </div>

      {/* Right: Language + New Chat + Status */}
      <div className="flex items-center gap-2">
        {/* Backend status dot */}
        <div className="hidden sm:flex items-center gap-1.5 mr-1">
          {backendStatus === 'connected' ? (
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-red-400" />
          )}
          <span className="text-[10px] text-slate-500">
            {backendStatus === 'connected' ? 'Connected' : 'Offline'}
          </span>
        </div>

        {/* Language Selector */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-xs">
          <Globe className="w-3.5 h-3.5 text-teal-400" />
          <select
            aria-label="Select Language"
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
          >
            {languages.map((lang) => (
              <option
                key={lang.code}
                value={lang.code}
                className="bg-slate-900 text-slate-100"
              >
                {lang.native}
              </option>
            ))}
          </select>
        </div>

        {/* New Chat Button */}
        <button
          onClick={onNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 text-xs text-slate-300 hover:text-white transition-colors"
          title="Start new conversation"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>
    </header>
  );
};
