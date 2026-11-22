import React, { useState } from 'react';
import { Search, Scale, ExternalLink, ShieldAlert, CheckCircle2, Clock, BookOpen, AlertCircle } from 'lucide-react';
import { searchLaws } from '../../services/api';

export const LawSearchSection = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState(null);
  const [error, setError] = useState('');

  const quickPrompts = [
    'Consumer Rights',
    'Data Privacy (DPDP)',
    'Aadhaar Subsidies',
    'Cyber Compensation',
    'Disability Rights',
  ];

  const handleSearch = async (term = null) => {
    const searchTerm = term || query;
    if (!searchTerm.trim()) {
      setError('Please enter a topic or act to search.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      const res = await searchLaws(searchTerm);
      if (res.success && res.data) {
        setSearchResponse(res.data);
      } else {
        setError(res.error || 'Failed to retrieve legal provisions.');
        setSearchResponse(null);
      }
    } catch {
      setError('An unexpected error occurred while querying law retrieval service.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs font-semibold mb-3">
          <Scale className="w-3.5 h-3.5" />
          <span>Source A: NyayKosh Legal Retrieval</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Indian Laws, Statutes & Citizen Rights
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Query statutory provisions, parliamentary acts, and consumer protections.
          Integrates with the official NeGD <strong>Law as Code</strong> (NyayKosh) open API.
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="max-w-3xl mx-auto">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="relative flex items-center"
        >
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
            <Search className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (error) setError('');
            }}
            placeholder="Search rights, statutes, sections (e.g. 'consumer rights', 'data consent', 'aadhaar')..."
            className="w-full pl-11 pr-32 py-3.5 rounded-xl bg-slate-900 border border-slate-700 focus:border-teal-400 focus:ring-1 focus:ring-teal-400 text-slate-100 placeholder-slate-500 text-sm focus:outline-none transition shadow-sm"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 px-5 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {loading ? 'Searching...' : 'Search Laws'}
          </button>
        </form>

        {/* Suggestion Pills */}
        <div className="mt-3 flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500">Popular queries:</span>
          {quickPrompts.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => {
                setQuery(p);
                handleSearch(p);
              }}
              className="text-xs px-2.5 py-1 rounded-md bg-slate-850 hover:bg-slate-800 text-slate-300 border border-slate-750 transition"
            >
              {p}
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Results Section */}
      {searchResponse && (
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Metadata & Source Transparency Bar */}
          <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-slate-400">Search results for:</span>
              <span className="font-semibold text-white">"{searchResponse.query}"</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-400">{searchResponse.total_results} provision(s) retrieved</span>
            </div>

            {/* Source Label */}
            <div>
              {searchResponse.is_live_data ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>NeGD NyayKosh Live API</span>
                </div>
              ) : (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 font-medium">
                  <ShieldAlert className="w-3.5 h-3.5 text-blue-400" />
                  <span>NyayKosh Mock Adapter (Dev Fallback)</span>
                </div>
              )}
            </div>
          </div>

          {searchResponse.message && (
            <p className="text-xs text-slate-400 italic px-1">
              ℹ️ {searchResponse.message}
            </p>
          )}

          {/* Provisions Cards List */}
          <div className="space-y-4">
            {searchResponse.results.map((item, idx) => (
              <div
                key={`${item.act_name}-${item.section_number}-${idx}`}
                className="p-5 sm:p-6 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition shadow-sm space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-teal-500/10 text-teal-300 border border-teal-500/20">
                        {item.section_number}
                      </span>
                      {item.category && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                          {item.category}
                        </span>
                      )}
                    </div>
                    <h3 className="text-base font-bold text-white mt-1.5">
                      {item.law_name}
                    </h3>
                  </div>

                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-teal-400 hover:text-teal-300 transition shrink-0 underline"
                  >
                    <span>Official Gazette / NeGD Source</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>

                {/* Provision Statutory Text */}
                <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-850">
                  <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-line">
                    {item.content}
                  </p>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                  <span>Act Reference: {item.act_name}</span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>Retrieved: {new Date(item.retrieval_timestamp).toLocaleDateString()}</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
