import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Sparkles,
  ArrowRight,
  HelpCircle,
  Clock,
  Terminal,
  Server,
  AlertTriangle,
  Scale,
  Gift,
  FileText,
  MessageSquare,
} from 'lucide-react';
import { sendTestChatMessage } from '../services/api';
import { BackendStatusBadge } from '../components/common/BackendStatusBadge';
import { LawSearchSection } from '../components/laws/LawSearchSection';
import { SchemeExplorerSection } from '../components/schemes/SchemeExplorerSection';
import { DocumentUploadSection } from '../components/documents/DocumentUploadSection';

export const Home = ({ backendStatus, backendVersion, onRetryBackend }) => {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      content:
        'Namaste! Welcome to NitiSetu. In this Phase 1 preview, you can test three independent data pillars below: (1) Official Indian Law Search via NyayKosh, (2) Verified Government Schemes with deterministic eligibility evaluation, and (3) User Document Upload with page-by-page text extraction. You can also send a message below to verify basic connectivity.',
      isDevNotice: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const chatBottomRef = useRef(null);

  const suggestions = [
    'Explain PM Kisan scheme',
    'What are consumer rights in India?',
    'Check Ayushman Bharat criteria',
    'Upload government gazette notice',
  ];

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (customText = null) => {
    const textToSend = customText || inputValue;
    const trimmed = textToSend.trim();

    if (!trimmed) {
      setErrorMessage('Please type a message before sending.');
      return;
    }

    setErrorMessage('');
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInputValue('');
    setIsLoading(true);

    try {
      const response = await sendTestChatMessage(trimmed);
      if (response.success && response.data) {
        const botMsg = {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          content: response.data.message,
          receivedEcho: response.data.received_message,
          isDevResponse: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        const errMsg = {
          id: `err-${Date.now()}`,
          sender: 'system',
          content: response.error || 'Failed to reach backend test endpoint.',
          isError: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, errMsg]);
      }
    } catch {
      const errMsg = {
        id: `err-${Date.now()}`,
        sender: 'system',
        content: 'Unexpected client error occurred while communicating with backend.',
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

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
            <span className="text-teal-400 font-semibold">Phase 1: Data Integration Active</span>
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
            NitiSetu reads government notices, verifies welfare scheme eligibility using
            deterministic rules, and retrieves Indian legal statutes via the official NyayKosh API.
          </p>

          {/* Quick Pillar Jump Pills */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#laws-section"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-750 text-xs font-semibold transition"
            >
              <Scale className="w-4 h-4 text-blue-400" />
              <span>Source A: Law Search</span>
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
            <a
              href="#chat-section"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition shadow-sm"
            >
              <MessageSquare className="w-4 h-4 text-slate-950" />
              <span>Civic Chat Preview</span>
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

      {/* SECTION 1: SOURCE A - LAWS & RIGHTS SEARCH (NYAYKOSH) */}
      <section id="laws-section" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <LawSearchSection />
      </section>

      {/* SECTION 2: SOURCE B - GOVERNMENT SCHEMES & DETERMINISTIC ELIGIBILITY */}
      <section id="schemes-section" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <SchemeExplorerSection />
      </section>

      {/* SECTION 3: SOURCE C - PDF DOCUMENT INTELLIGENCE */}
      <section id="documents-section" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <DocumentUploadSection />
      </section>

      {/* SECTION 4: CIVIC CHAT PREVIEW */}
      <section id="chat-section" className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs font-semibold mb-3">
            <Terminal className="w-3.5 h-3.5" />
            <span>Interactive Chat Preview</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Full-Stack Connectivity Verification
          </h2>
          <p className="mt-2 text-sm text-slate-400 max-w-xl mx-auto">
            Direct client-to-server communication with FastAPI gateway endpoint{' '}
            <code className="text-teal-300 bg-slate-800 px-1 py-0.5 rounded text-xs">
              POST /api/v1/chat/test
            </code>.
          </p>
        </div>

        {/* Chat Window Card */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden flex flex-col h-[520px]">
          {/* Chat Header */}
          <div className="px-5 py-3.5 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-300 font-bold text-xs">
                NS
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">NitiSetu Assistant</h4>
                <p className="text-[11px] text-slate-400">Phase 1 Development Mode</p>
              </div>
            </div>

            <BackendStatusBadge
              status={backendStatus}
              version={backendVersion}
              onRetry={onRetryBackend}
            />
          </div>

          {/* Messages Area */}
          <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4">
            {messages.map((msg) => {
              const isUser = msg.sender === 'user';
              if (msg.isError) {
                return (
                  <div
                    key={msg.id}
                    className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5 max-w-lg mx-auto"
                  >
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold">Communication Error</p>
                      <p className="mt-0.5 text-rose-200/80">{msg.content}</p>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-sm leading-relaxed ${
                      isUser
                        ? 'bg-teal-600 text-white rounded-br-none shadow-md shadow-teal-600/10'
                        : 'bg-slate-800 text-slate-200 border border-slate-700/70 rounded-bl-none shadow-sm'
                    }`}
                  >
                    {msg.isDevNotice && (
                      <div className="mb-2 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-teal-300 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20">
                        Notice
                      </div>
                    )}
                    {msg.isDevResponse && (
                      <div className="mb-2 flex items-center justify-between border-b border-slate-700/60 pb-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          FastAPI Response
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          HTTP 200 OK
                        </span>
                      </div>
                    )}
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    {msg.receivedEcho && (
                      <div className="mt-2 pt-2 border-t border-slate-700/60 text-xs text-slate-300">
                        <span className="text-slate-400 font-mono text-[11px]">Server received: </span>
                        <span className="font-medium text-teal-300">"{msg.receivedEcho}"</span>
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 mt-1 px-1">
                    {msg.timestamp}
                  </span>
                </div>
              );
            })}

            {isLoading && (
              <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-850 px-3.5 py-2 rounded-xl w-fit border border-slate-800">
                <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
                <span>FastAPI endpoint processing request...</span>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick Suggestions */}
          <div className="px-4 py-2 bg-slate-850 border-t border-slate-800/80 overflow-x-auto no-scrollbar">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium text-slate-500 shrink-0">
                Quick prompts:
              </span>
              {suggestions.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleSendMessage(prompt)}
                  disabled={isLoading || backendStatus !== 'connected'}
                  className="shrink-0 text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition disabled:opacity-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Input Form */}
          <div className="p-4 bg-slate-850 border-t border-slate-800">
            {errorMessage && (
              <div className="mb-2 text-xs text-rose-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>{errorMessage}</span>
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputValue}
                onChange={(e) => {
                  setInputValue(e.target.value);
                  if (errorMessage) setErrorMessage('');
                }}
                placeholder="Type a query to test FastAPI communication..."
                disabled={isLoading}
                className="flex-1 bg-slate-800 border border-slate-700 focus:border-teal-500 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !inputValue.trim()}
                className="px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-sm transition flex items-center justify-center gap-1.5 disabled:opacity-40"
              >
                <span>Send</span>
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
};
