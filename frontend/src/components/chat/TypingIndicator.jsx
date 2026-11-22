import React from 'react';
import { Sparkles } from 'lucide-react';

export const TypingIndicator = () => {
  return (
    <div className="flex gap-3 py-4 fade-in">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-teal-500/10">
        <Sparkles className="w-4 h-4 text-white" />
      </div>
      <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl bg-slate-800/40 border border-slate-700/30">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
};
