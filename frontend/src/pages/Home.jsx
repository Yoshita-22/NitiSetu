import React from 'react';
import {
  Sparkles,
  Server,
  Scale,
  Gift,
  FileText,
  MessageSquare,
} from 'lucide-react';
import { BackendStatusBadge } from '../components/common/BackendStatusBadge';
import { LawSearchSection } from '../components/laws/LawSearchSection';
import { SchemeExplorerSection } from '../components/schemes/SchemeExplorerSection';
import { DocumentUploadSection } from '../components/documents/DocumentUploadSection';
import { IntelligentChatSection } from '../components/chat/IntelligentChatSection';

export const Home = ({ backendStatus, backendVersion, onRetryBackend }) => {
  return (
    <div className="space-y-28">
      {/* Hero Section */}
      <section className="relative pt-12 pb-6 sm:pt-20 sm:pb-10 text-center overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl -z-10 pointer-events-none" />
        <div className="absolute top-1/3 left-1/4 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl -z-10 pointer-events-none" />

        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900 border border-slate-700/80 text-xs text-slate-300 mb-6 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-teal-400" />
            <span className="font-medium">NitiSetu Civic Platform</span>
            <span className="text-slate-600">•</span>
            <span className="text-teal-400 font-semibold">Phase 2: LangGraph Orchestration Active</span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Bridging Citizens with{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-blue-500">
              Knowledge & Rights.
            </span>
          </h1>

          {/* Supporting Text */}
          <p className="mt-6 text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
            NitiSetu uses <strong>LangGraph</strong> to intelligently orchestrate citizen queries—classifying
            intent, routing conditionally, running parallel retrievals across Indian statutory laws (NyayKosh)
            and welfare schemes, and conducting sequential eligibility assessments with human-in-the-loop checkpoints.
          </p>

          {/* Quick Pillar Jump Pills */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#chat-section"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition shadow-md shadow-teal-500/10"
            >
              <MessageSquare className="w-4 h-4 text-slate-950" />
              <span>Intelligent Civic Chat</span>
            </a>
            <a
              href="#laws-section"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-750 text-xs font-semibold transition"
            >
              <Scale className="w-4 h-4 text-blue-400" />
              <span>Source A: Law Search (NyayKosh)</span>
            </a>
            <a
              href="#schemes-section"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-750 text-xs font-semibold transition"
            >
              <Gift className="w-4 h-4 text-emerald-400" />
              <span>Source B: Scheme Directory</span>
            </a>
            <a
              href="#documents-section"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-750 text-xs font-semibold transition"
            >
              <FileText className="w-4 h-4 text-cyan-400" />
              <span>Source C: Document Upload</span>
            </a>
          </div>

          {/* Status Bar */}
          <div className="mt-10 p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <Server className="w-4 h-4 text-teal-400" />
              <span>FastAPI Backend: <strong>http://localhost:8000</strong></span>
            </div>
            <span className="hidden sm:inline text-slate-700">|</span>
            <div className="flex items-center gap-2">
              <span>Status:</span>
              <BackendStatusBadge
                status={backendStatus}
                version={backendVersion}
                onRetry={onRetryBackend}
              />
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 1: LANGGRAPH CIVIC CHAT ORCHESTRATION */}
      <section id="chat-section" className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>LangGraph Multi-Intent Orchestrator</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Intelligent Civic Query Assistant
          </h2>
          <p className="mt-2 text-sm text-slate-400 max-w-xl mx-auto">
            Ask any civic question in English, Hindi, or Telugu. LangGraph dynamically routes your request,
            fetches official statutes and welfare data, and pauses to ask missing eligibility details when needed.
          </p>
        </div>

        <IntelligentChatSection
          backendStatus={backendStatus}
          backendVersion={backendVersion}
        />
      </section>

      {/* SECTION 2: SOURCE A - LAWS & RIGHTS SEARCH (NYAYKOSH) */}
      <section id="laws-section" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <LawSearchSection />
      </section>

      {/* SECTION 3: SOURCE B - GOVERNMENT SCHEMES & DETERMINISTIC ELIGIBILITY */}
      <section id="schemes-section" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <SchemeExplorerSection />
      </section>

      {/* SECTION 4: SOURCE C - PDF DOCUMENT INTELLIGENCE */}
      <section id="documents-section" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <DocumentUploadSection />
      </section>
    </div>
  );
};
