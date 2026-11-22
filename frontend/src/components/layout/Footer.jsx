import React from 'react';
import { Landmark, Shield, ExternalLink } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 text-sm mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Info */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-blue-600 flex items-center justify-center text-slate-950 font-bold">
                <Landmark className="w-4 h-4 text-slate-950" />
              </div>
              <span className="text-lg font-bold text-white">NitiSetu</span>
            </div>
            <p className="text-slate-400 text-xs sm:text-sm max-w-md leading-relaxed">
              Bridging Citizens with Knowledge. An AI-powered civic information assistant
              translating government notices, welfare schemes, and statutory citizen rights
              into plain, accessible regional languages.
            </p>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700 text-[11px] text-slate-300">
              <Shield className="w-3.5 h-3.5 text-teal-400" />
              <span>Phase 1: Three Independent Data Source Integrations Active</span>
            </div>
          </div>

          {/* Data Sources Architecture */}
          <div>
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">
              Data Strategy Pillars
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a href="#laws-section" className="hover:text-teal-300 transition-colors">
                  Source A: NyayKosh Law Retrieval
                </a>
              </li>
              <li>
                <a href="#schemes-section" className="hover:text-teal-300 transition-colors">
                  Source B: Verified Schemes & Evaluator
                </a>
              </li>
              <li>
                <a href="#documents-section" className="hover:text-teal-300 transition-colors">
                  Source C: PDF Document Intelligence
                </a>
              </li>
              <li className="text-slate-500">
                Future: Intelligent Intent Router (Phase 2)
              </li>
            </ul>
          </div>

          {/* Developer Resources */}
          <div>
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">
              Developer APIs
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-teal-300 transition-colors underline inline-flex items-center gap-1"
                >
                  <span>FastAPI Swagger UI</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="http://localhost:8000/api/v1/health"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-teal-300 transition-colors underline"
                >
                  Health Check (/api/v1/health)
                </a>
              </li>
              <li>
                <a
                  href="http://localhost:8000/api/v1/schemes"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-teal-300 transition-colors underline"
                >
                  Schemes API (/api/v1/schemes)
                </a>
              </li>
              <li>
                <span className="text-slate-500">PyMuPDF Document Parser</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
          <p>© {new Date().getFullYear()} NitiSetu. Built for transparent governance and civic accessibility.</p>
          <p>
            Deterministic scheme evaluation • Official statutory citations
          </p>
        </div>
      </div>
    </footer>
  );
};
