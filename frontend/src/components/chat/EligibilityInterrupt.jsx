import React, { useState } from 'react';
import { CheckCircle2, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react';

export const EligibilityInterrupt = ({
  questions = [],
  onSubmit,
  onNaturalLanguage,
  isLoading,
}) => {
  const [answers, setAnswers] = useState(() => {
    const defaults = {};
    questions.forEach((q) => {
      if (q.input_type === 'boolean') {
        defaults[q.field] = null;
      } else {
        defaults[q.field] = '';
      }
    });
    return defaults;
  });
  const [showForm, setShowForm] = useState(true);

  const handleChange = (field, value) => {
    setAnswers(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = () => {
    const formatted = {};
    questions.forEach((q) => {
      const val = answers[q.field];
      if (q.input_type === 'boolean') {
        formatted[q.field] = val === true;
      } else if (q.input_type === 'number') {
        formatted[q.field] = val !== '' ? Number(val) : '';
      } else {
        formatted[q.field] = val;
      }
    });
    onSubmit(formatted);
  };

  const allAnswered = questions.every(q => {
    const val = answers[q.field];
    if (q.input_type === 'boolean') return val !== null;
    return val !== '' && val !== undefined;
  });

  return (
    <div className="ml-11 mt-2 mb-2 fade-in">
      <div className="rounded-xl bg-slate-800/40 border border-amber-500/20 overflow-hidden max-w-lg">
        {/* Header */}
        <button
          onClick={() => setShowForm(!showForm)}
          className="w-full flex items-center justify-between gap-2 px-4 py-3 bg-amber-500/5 border-b border-amber-500/10 text-left"
        >
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-amber-500/10 flex items-center justify-center">
              <MessageSquare className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <span className="text-xs font-semibold text-amber-300">
              Eligibility Questions
            </span>
            <span className="text-[10px] text-amber-400/60">
              ({questions.length} {questions.length === 1 ? 'question' : 'questions'})
            </span>
          </div>
          {showForm ? (
            <ChevronUp className="w-4 h-4 text-amber-400/60" />
          ) : (
            <ChevronDown className="w-4 h-4 text-amber-400/60" />
          )}
        </button>

        {showForm && (
          <div className="p-4 space-y-3">
            <p className="text-xs text-slate-400 leading-relaxed">
              You can answer using the form below, or simply type your answers naturally in the chat.
            </p>

            {questions.map((q) => (
              <div key={q.field} className="space-y-1.5">
                <label className="text-xs font-medium text-slate-200 block">
                  {q.question}
                </label>
                {q.help_text && (
                  <p className="text-[11px] text-slate-500">{q.help_text}</p>
                )}

                {q.input_type === 'boolean' ? (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleChange(q.field, true)}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        answers[q.field] === true
                          ? 'bg-teal-500 text-slate-950 font-bold'
                          : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      Yes
                    </button>
                    <button
                      type="button"
                      onClick={() => handleChange(q.field, false)}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        answers[q.field] === false
                          ? 'bg-rose-500 text-white font-bold'
                          : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      No
                    </button>
                  </div>
                ) : q.input_type === 'select' && q.options ? (
                  <select
                    value={answers[q.field] || ''}
                    onChange={(e) => handleChange(q.field, e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-700/50 border border-slate-600/50 text-xs text-white focus:outline-none focus:border-teal-400/50 transition-colors"
                  >
                    <option value="" className="bg-slate-800">Select...</option>
                    {q.options.map((opt) => (
                      <option key={opt} value={opt} className="bg-slate-800">{opt}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={q.input_type === 'number' ? 'number' : 'text'}
                    value={answers[q.field] || ''}
                    onChange={(e) => handleChange(q.field, e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-700/50 border border-slate-600/50 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-400/50 transition-colors"
                    placeholder={q.input_type === 'number' ? 'Enter amount...' : 'Enter value...'}
                  />
                )}
              </div>
            ))}

            <button
              onClick={handleSubmit}
              disabled={isLoading || !allAnswered}
              className="w-full py-2.5 rounded-lg bg-teal-500 hover:bg-teal-400 disabled:opacity-40 disabled:hover:bg-teal-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-colors mt-2"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{isLoading ? 'Processing...' : 'Submit Answers'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
