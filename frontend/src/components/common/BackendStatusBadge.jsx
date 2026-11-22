import React from 'react';
import { CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

/**
 * BackendStatusBadge
 * Displays the current backend connectivity status in the UI.
 *
 * @param {Object} props
 * @param {'connected' | 'disconnected' | 'checking'} props.status
 * @param {string | null} [props.version]
 * @param {Function} [props.onRetry]
 */
export const BackendStatusBadge = ({ status, version = '1.0.0', onRetry }) => {
  if (status === 'checking') {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
        </span>
        <span>Checking Backend...</span>
      </div>
    );
  }

  if (status === 'connected') {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-sm shadow-emerald-500/5">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        <span>Backend Connected {version ? `(v${version})` : ''}</span>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20">
      <span className="relative flex h-2 w-2">
        <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
      </span>
      <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
      <span>Backend Disconnected</span>
      {onRetry && (
        <button
          onClick={onRetry}
          title="Retry connection"
          className="ml-1 text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw className="w-3 h-3 hover:rotate-180 transition-transform duration-300" />
        </button>
      )}
    </div>
  );
};
