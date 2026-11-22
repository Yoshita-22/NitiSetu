import React, { useState, useEffect } from 'react';
import {
  Gift,
  Search,
  ExternalLink,
  CheckCircle,
  XCircle,
  HelpCircle,
  AlertTriangle,
  UserCheck,
  Building,
  FileCheck,
  ChevronRight,
  X,
  ShieldAlert,
} from 'lucide-react';
import {
  getAllSchemes,
  searchSchemes,
  getSchemeById,
  getSchemeEligibilityQuestions,
  evaluateSchemeEligibility,
} from '../../services/api';

export const SchemeExplorerSection = () => {
  const [schemes, setSchemes] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Selected scheme detail modal
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Eligibility questionnaire state
  const [activeQuestionnaire, setActiveQuestionnaire] = useState(null);
  const [answers, setAnswers] = useState({});
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState(null);
  const [evalError, setEvalError] = useState('');

  useEffect(() => {
    loadSchemes();
  }, []);

  const loadSchemes = async () => {
    setLoading(true);
    setError('');
    const res = await getAllSchemes();
    if (res.success && res.data) {
      setSchemes(res.data);
    } else {
      setError(res.error || 'Failed to load welfare schemes.');
    }
    setLoading(false);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const res = await searchSchemes(searchQuery);
    if (res.success && res.data) {
      setSchemes(res.data);
    } else {
      setError(res.error || 'Failed to search schemes.');
    }
    setLoading(false);
  };

  const handleOpenSchemeDetails = async (schemeId) => {
    setDetailLoading(true);
    const res = await getSchemeById(schemeId);
    if (res.success && res.data) {
      setSelectedScheme(res.data);
    }
    setDetailLoading(false);
  };

  const handleStartEligibility = async (schemeId) => {
    setEvaluating(false);
    setEvalResult(null);
    setEvalError('');
    setAnswers({});

    const res = await getSchemeEligibilityQuestions(schemeId);
    if (res.success && res.data) {
      setActiveQuestionnaire(res.data);
    } else {
      setEvalError(res.error || 'Failed to load eligibility questionnaire.');
    }
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  };

  const handleEvaluateSubmit = async (e) => {
    e.preventDefault();
    if (!activeQuestionnaire) return;

    setEvaluating(true);
    setEvalError('');
    try {
      const res = await evaluateSchemeEligibility(activeQuestionnaire.scheme_id, answers);
      if (res.success && res.data) {
        setEvalResult(res.data);
      } else {
        setEvalError(res.error || 'Evaluation failed.');
      }
    } catch {
      setEvalError('Unexpected error evaluating eligibility.');
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-semibold mb-3">
          <Gift className="w-3.5 h-3.5" />
          <span>Source B: Verified Welfare Scheme Directory</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Explore Government Welfare Schemes
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Browse verified central and state welfare initiatives. Run our deterministic
          eligibility engine to check requirements without algorithmic ambiguity.
        </p>
      </div>

      {/* Search Bar */}
      <div className="max-w-2xl mx-auto">
        <form onSubmit={handleSearch} className="relative flex items-center">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
            <Search className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search schemes by name, keyword, or beneficiary (e.g. 'farmer', 'health', 'Telangana')..."
            className="w-full pl-11 pr-28 py-3 rounded-xl bg-slate-900 border border-slate-700 focus:border-teal-400 focus:ring-1 focus:ring-teal-400 text-slate-100 placeholder-slate-500 text-sm focus:outline-none transition shadow-sm"
          />
          <button
            type="submit"
            className="absolute right-2 px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition shadow-sm"
          >
            Search
          </button>
        </form>

        {error && (
          <div className="mt-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
            {error}
          </div>
        )}
      </div>

      {/* Schemes Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm">
          <span className="inline-block w-4 h-4 border-2 border-teal-400 border-t-transparent rounded-full animate-spin mr-2" />
          Loading verified welfare schemes...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {schemes.map((scheme) => (
            <div
              key={scheme.scheme_id}
              className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between shadow-sm group"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-teal-500/10 text-teal-300 border border-teal-500/20">
                    {scheme.state_applicability}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    {scheme.data_source}
                  </span>
                </div>

                <h3 className="text-base font-bold text-white group-hover:text-teal-300 transition-colors">
                  {scheme.scheme_name}
                </h3>
                <p className="text-xs text-slate-400 mt-2 line-clamp-3 leading-relaxed">
                  {scheme.short_description}
                </p>

                <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5 text-xs text-slate-300">
                  <div className="flex items-start gap-1.5">
                    <Building className="w-3.5 h-3.5 text-teal-400 shrink-0 mt-0.5" />
                    <span className="text-[11px] text-slate-400">{scheme.ministry}</span>
                  </div>
                  <div className="flex items-start gap-1.5">
                    <UserCheck className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                    <span className="text-[11px] text-slate-300 font-medium">
                      Beneficiaries: {scheme.target_beneficiaries}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => handleOpenSchemeDetails(scheme.scheme_id)}
                  className="text-xs font-semibold text-slate-300 hover:text-white transition flex items-center gap-1"
                >
                  <span>Details</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>

                <button
                  type="button"
                  onClick={() => handleStartEligibility(scheme.scheme_id)}
                  className="px-3.5 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition shadow-sm"
                >
                  Check My Eligibility
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Scheme Detail Modal */}
      {selectedScheme && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto shadow-2xl relative">
            <button
              onClick={() => setSelectedScheme(null)}
              className="absolute top-5 right-5 p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition"
              aria-label="Close Modal"
            >
              <X className="w-4 h-4" />
            </button>

            <div>
              <span className="px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-teal-500/10 text-teal-300 border border-teal-500/20">
                {selectedScheme.state_applicability}
              </span>
              <h2 className="text-xl sm:text-2xl font-bold text-white mt-2">
                {selectedScheme.scheme_name}
              </h2>
              <p className="text-xs text-teal-400 mt-1">{selectedScheme.ministry}</p>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">
              {selectedScheme.short_description}
            </p>

            {/* Benefits */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Entitlements & Benefits
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-200">
                {selectedScheme.benefits?.map((b, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Eligibility & Exclusions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-2">
                  Eligibility Criteria
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {selectedScheme.eligibility_conditions?.map((c, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="text-teal-400 shrink-0">•</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400 mb-2">
                  Exclusions & Restrictions
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {selectedScheme.exclusion_conditions?.map((ex, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="text-rose-400 shrink-0">•</span>
                      <span>{ex}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Required Documents */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Required Documentation
              </h4>
              <div className="flex flex-wrap gap-2">
                {selectedScheme.required_documents?.map((doc, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs border border-slate-700 flex items-center gap-1.5"
                  >
                    <FileCheck className="w-3 h-3 text-teal-400" />
                    <span>{doc}</span>
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800 flex items-center justify-between gap-4">
              <a
                href={selectedScheme.official_source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-teal-400 hover:text-teal-300 underline"
              >
                <span>Visit Official Portal</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>

              <button
                type="button"
                onClick={() => {
                  const id = selectedScheme.scheme_id;
                  setSelectedScheme(null);
                  handleStartEligibility(id);
                }}
                className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition"
              >
                Check My Eligibility
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Eligibility Questionnaire Modal */}
      {activeQuestionnaire && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto shadow-2xl relative">
            <button
              onClick={() => {
                setActiveQuestionnaire(null);
                setEvalResult(null);
              }}
              className="absolute top-5 right-5 p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition"
              aria-label="Close Questionnaire"
            >
              <X className="w-4 h-4" />
            </button>

            <div>
              <div className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-teal-300 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20">
                Deterministic Rule Engine
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white mt-2">
                Preliminary Eligibility Assessment
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Scheme: <strong className="text-teal-300">{activeQuestionnaire.scheme_name}</strong>
              </p>
            </div>

            {/* Questions Form */}
            {!evalResult ? (
              <form onSubmit={handleEvaluateSubmit} className="space-y-5">
                <p className="text-xs text-slate-300">
                  Please answer the scheme-specific questions below to verify conditions against official guidelines:
                </p>

                <div className="space-y-4">
                  {activeQuestionnaire.questions.map((q) => (
                    <div
                      key={q.id}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2"
                    >
                      <label className="block text-xs font-semibold text-white leading-snug">
                        {q.label}
                      </label>
                      {q.help_text && (
                        <p className="text-[11px] text-slate-400">{q.help_text}</p>
                      )}

                      {q.type === 'boolean' && (
                        <div className="flex items-center gap-4 pt-1">
                          <label className="inline-flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                            <input
                              type="radio"
                              name={q.id}
                              checked={answers[q.id] === true}
                              onChange={() => handleAnswerChange(q.id, true)}
                              className="text-teal-500 focus:ring-teal-400"
                            />
                            <span>Yes</span>
                          </label>
                          <label className="inline-flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                            <input
                              type="radio"
                              name={q.id}
                              checked={answers[q.id] === false}
                              onChange={() => handleAnswerChange(q.id, false)}
                              className="text-teal-500 focus:ring-teal-400"
                            />
                            <span>No</span>
                          </label>
                        </div>
                      )}

                      {q.type === 'number' && (
                        <input
                          type="number"
                          value={answers[q.id] !== undefined ? answers[q.id] : ''}
                          onChange={(e) =>
                            handleAnswerChange(
                              q.id,
                              e.target.value === '' ? undefined : Number(e.target.value)
                            )
                          }
                          placeholder="Enter amount / numeric value in INR..."
                          className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-teal-400"
                        />
                      )}
                    </div>
                  ))}
                </div>

                {evalError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
                    {evalError}
                  </div>
                )}

                <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setActiveQuestionnaire(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={evaluating}
                    className="px-5 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition disabled:opacity-40"
                  >
                    {evaluating ? 'Evaluating Conditions...' : 'Evaluate Eligibility'}
                  </button>
                </div>
              </form>
            ) : (
              /* Evaluation Results Screen */
              <div className="space-y-6">
                {/* Status Result Banner */}
                {evalResult.overall_result === 'LIKELY_ELIGIBLE' && (
                  <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold text-white">
                        Preliminary Assessment: Likely Eligible
                      </h4>
                      <p className="text-xs text-emerald-200/90 mt-1">
                        Based on the information provided, you satisfy the positive criteria and do not trigger statutory disqualifications.
                      </p>
                    </div>
                  </div>
                )}

                {evalResult.overall_result === 'LIKELY_NOT_ELIGIBLE' && (
                  <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-200 flex items-start gap-3">
                    <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold text-white">
                        Preliminary Assessment: Likely Ineligible
                      </h4>
                      <p className="text-xs text-rose-200/90 mt-1">
                        One or more answers trigger statutory exclusion conditions or do not meet baseline qualification standards.
                      </p>
                    </div>
                  </div>
                )}

                {evalResult.overall_result === 'NEEDS_MORE_INFORMATION' && (
                  <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-200 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold text-white">
                        Preliminary Assessment: Needs More Information
                      </h4>
                      <p className="text-xs text-amber-200/90 mt-1">
                        Certain mandatory eligibility questions were not answered. Complete all fields for a conclusive preliminary assessment.
                      </p>
                    </div>
                  </div>
                )}

                {/* Condition Breakdown */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3">
                    Condition Breakdown
                  </h4>
                  <div className="space-y-2.5">
                    {evalResult.conditions.map((cond, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start justify-between gap-3 text-xs"
                      >
                        <div className="space-y-1">
                          <p className="font-semibold text-white">{cond.condition}</p>
                          <p className="text-slate-400 text-[11px]">{cond.explanation}</p>
                        </div>
                        <div className="shrink-0">
                          {cond.status === 'MET' && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              MET
                            </span>
                          )}
                          {cond.status === 'NOT_MET' && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              NOT MET
                            </span>
                          )}
                          {cond.status === 'UNKNOWN' && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              UNKNOWN
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Missing Info List if any */}
                {evalResult.missing_information?.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-slate-850 border border-slate-750 text-xs">
                    <p className="font-semibold text-amber-400">Unanswered Questions:</p>
                    <ul className="list-disc list-inside mt-1 text-slate-400 text-[11px]">
                      {evalResult.missing_information.map((m) => (
                        <li key={m}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Legal Disclaimer */}
                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-850 text-[11px] text-slate-400 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-300">
                    <ShieldAlert className="w-3.5 h-3.5 text-teal-400" />
                    <span>Important Disclaimer</span>
                  </div>
                  <p>{evalResult.disclaimer}</p>
                </div>

                {/* Modal Footer */}
                <div className="pt-4 border-t border-slate-800 flex items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => setEvalResult(null)}
                    className="text-xs text-teal-400 hover:text-teal-300 font-semibold"
                  >
                    ← Edit Answers
                  </button>

                  <div className="flex items-center gap-3">
                    <a
                      href={evalResult.official_source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-slate-300 hover:text-white underline"
                    >
                      <span>Official Scheme Website</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>

                    <button
                      type="button"
                      onClick={() => setActiveQuestionnaire(null)}
                      className="px-4 py-2 rounded-xl bg-slate-800 text-white text-xs font-semibold hover:bg-slate-700 transition"
                    >
                      Done
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
