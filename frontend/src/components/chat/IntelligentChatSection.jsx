import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Clock,
  ExternalLink,
  Layers,
  ArrowRight,
  ShieldCheck,
  FileText,
  Scale,
  Gift,
  Bot,
  User,
} from 'lucide-react';
import { sendChatQuery, resumeChatQuery } from '../../services/api';

export const IntelligentChatSection = ({ backendStatus, backendVersion }) => {
  const [conversationId, setConversationId] = useState(() => `conv-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      content:
        'Namaste! I am NitiSetu, your LangGraph-orchestrated civic assistant. You can ask me about Indian laws and rights (NyayKosh), government welfare schemes (verified dataset), or check your personal scheme eligibility with interactive questions. How can I assist you today?',
      intent: 'GENERAL_QUERY',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [pendingInterrupt, setPendingInterrupt] = useState(null); // { questions: [], prompt: '' }
  const [questionAnswers, setQuestionAnswers] = useState({});
  const chatBottomRef = useRef(null);

  const samplePrompts = [
    { label: 'Law Provision', text: 'What is Section 498A of Indian Penal Code?' },
    { label: 'Scheme Info', text: 'Tell me about PM-KISAN benefits and ministry' },
    { label: 'Eligibility (HITL)', text: 'Am I eligible for PM-KISAN scheme?' },
    { label: 'Multi-Intent Parallel', text: 'Explain Ayushman Bharat scheme and Consumer Protection Act rights' },
  ];

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, pendingInterrupt]);

  const handleStartNewConversation = () => {
    const newId = `conv-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setConversationId(newId);
    setPendingInterrupt(null);
    setQuestionAnswers({});
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        sender: 'bot',
        content:
          'Started a fresh conversation thread. Ask about laws, schemes, or eligibility assessment.',
        intent: 'GENERAL_QUERY',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  const handleSend = async (textToSend = null) => {
    const query = (textToSend || inputValue).trim();
    if (!query) return;

    setErrorMessage('');
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputValue('');
    setIsLoading(true);
    setPendingInterrupt(null);

    const res = await sendChatQuery(conversationId, query);
    setIsLoading(false);

    if (!res.success) {
      setErrorMessage(res.error || 'Failed to process query with orchestration engine.');
      return;
    }

    const data = res.data;
    if (data.status === 'waiting_for_user') {
      // LangGraph paused at interrupt()
      setPendingInterrupt({
        questions: data.pending_questions || [],
        prompt: data.answer,
      });

      // Initialize default answers dictionary
      const defaults = {};
      (data.pending_questions || []).forEach((q) => {
        if (q.input_type === 'boolean') {
          defaults[q.field] = false;
        } else {
          defaults[q.field] = '';
        }
      });
      setQuestionAnswers(defaults);

      setMessages((prev) => [
        ...prev,
        {
          id: `bot-interrupt-${Date.now()}`,
          sender: 'bot',
          content: data.answer,
          isInterrupt: true,
          intent: data.intent,
          pendingQuestions: data.pending_questions,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } else {
      // Completed response
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          content: data.answer,
          intent: data.intent,
          sources: data.sources || [],
          execution: data.execution,
          results: data.results,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }
  };

  const handleResumeSubmit = async () => {
    if (!pendingInterrupt) return;
    setIsLoading(true);
    setErrorMessage('');

    // Format boolean answers properly
    const answersToSend = { ...questionAnswers };

    const res = await resumeChatQuery(conversationId, answersToSend);
    setIsLoading(false);

    if (!res.success) {
      setErrorMessage(res.error || 'Failed to resume workflow.');
      return;
    }

    const data = res.data;
    setPendingInterrupt(null);
    setQuestionAnswers({});

    if (data.status === 'waiting_for_user') {
      setPendingInterrupt({
        questions: data.pending_questions || [],
        prompt: data.answer,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-interrupt-${Date.now()}`,
          sender: 'bot',
          content: data.answer,
          isInterrupt: true,
          intent: data.intent,
          pendingQuestions: data.pending_questions,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } else {
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          content: data.answer,
          intent: data.intent,
          sources: data.sources || [],
          execution: data.execution,
          results: data.results,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden flex flex-col h-[700px]">
      {/* Chat Header */}
      <div className="px-5 py-3.5 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-300 font-bold text-sm shadow-sm">
            <Sparkles className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-white">LangGraph Civic Orchestrator</h4>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-500/10 text-teal-300 border border-teal-500/20">
                Phase 2 Active
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Thread: <span className="text-slate-300">{conversationId.substring(0, 18)}...</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleStartNewConversation}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition"
            title="Start new isolated conversation thread"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Thread</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-5">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
            >
              {/* Message bubble */}
              <div
                className={`max-w-[90%] sm:max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed ${
                  isUser
                    ? 'bg-teal-600 text-white rounded-br-none shadow-md shadow-teal-600/10'
                    : 'bg-slate-800 text-slate-200 border border-slate-700/70 rounded-bl-none shadow-sm'
                }`}
              >
                {/* Assistant Metadata Headers */}
                {!isUser && msg.intent && (
                  <div className="mb-2.5 flex flex-wrap items-center gap-2 border-b border-slate-700/60 pb-2">
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-teal-300 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20">
                      Intent: {msg.intent.replace('_', ' ')}
                    </span>
                    {msg.isInterrupt && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        <Clock className="w-3 h-3" />
                        Human-in-the-Loop Paused
                      </span>
                    )}
                    {msg.execution?.partial_failure && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                        Partial Upstream Failure
                      </span>
                    )}
                  </div>
                )}

                {/* Text content */}
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Citations & Sources Card */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-700/60">
                    <h5 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
                      Verified Source Citations ({msg.sources.length})
                    </h5>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {msg.sources.map((src, i) => {
                        const isNyay = src.type?.includes('nyaykosh');
                        const isDoc = src.type?.includes('pdf') || src.type?.includes('document');

                        return (
                          <div
                            key={i}
                            className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-750 text-xs flex flex-col justify-between"
                          >
                            <div className="flex items-start gap-2">
                              {isNyay ? (
                                <Scale className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                              ) : isDoc ? (
                                <FileText className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                              ) : (
                                <Gift className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                              )}
                              <div className="min-w-0">
                                <p className="font-semibold text-slate-200 truncate">{src.title}</p>
                                <p className="text-[10px] text-slate-400 mt-0.5">{src.details}</p>
                              </div>
                            </div>
                            {src.url && !src.url.startsWith('document://') && (
                              <a
                                href={src.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-2 inline-flex items-center gap-1 text-[10px] text-teal-400 hover:text-teal-300 font-medium self-end"
                              >
                                <span>Official Source</span>
                                <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
            </div>
          );
        })}

        {/* Interactive Pending Questionnaire (HITL interrupt) */}
        {pendingInterrupt && (
          <div className="p-4 sm:p-5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-slate-200 space-y-4 max-w-xl mx-auto shadow-lg animate-in fade-in">
            <div className="flex items-center gap-2 text-amber-300 font-semibold text-sm">
              <Clock className="w-4 h-4 text-amber-400" />
              <span>Applicant Questionnaire (Checkpoint Active)</span>
            </div>
            <p className="text-xs text-amber-200/90 leading-relaxed">
              LangGraph has temporarily paused this thread until you provide the required eligibility details:
            </p>

            <div className="space-y-3 pt-1">
              {pendingInterrupt.questions.map((q) => (
                <div key={q.field} className="p-3 rounded-xl bg-slate-900/90 border border-slate-750 space-y-2">
                  <label className="text-xs font-semibold text-slate-200 block">
                    {q.question}
                  </label>
                  {q.help_text && <p className="text-[11px] text-slate-400">{q.help_text}</p>}

                  {q.input_type === 'boolean' ? (
                    <div className="flex items-center gap-3 pt-1">
                      <button
                        type="button"
                        onClick={() =>
                          setQuestionAnswers((prev) => ({ ...prev, [q.field]: true }))
                        }
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                          questionAnswers[q.field] === true
                            ? 'bg-teal-500 text-slate-950 font-bold'
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-750'
                        }`}
                      >
                        Yes
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setQuestionAnswers((prev) => ({ ...prev, [q.field]: false }))
                        }
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                          questionAnswers[q.field] === false
                            ? 'bg-rose-500 text-white font-bold'
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-750'
                        }`}
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <input
                      type={q.input_type === 'number' ? 'number' : 'text'}
                      value={questionAnswers[q.field] || ''}
                      onChange={(e) =>
                        setQuestionAnswers((prev) => ({
                          ...prev,
                          [q.field]:
                            q.input_type === 'number' ? Number(e.target.value) : e.target.value,
                        }))
                      }
                      className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-teal-400"
                      placeholder="Enter value..."
                    />
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={handleResumeSubmit}
              disabled={isLoading}
              className="w-full py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition shadow-md shadow-teal-500/10"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{isLoading ? 'Resuming Workflow...' : 'Submit Answers & Resume Evaluation'}</span>
            </button>
          </div>
        )}

        {/* Loading Spinner */}
        {isLoading && (
          <div className="flex items-center gap-3 text-slate-400 text-xs py-2 px-1">
            <div className="w-5 h-5 rounded-full border-2 border-teal-400 border-t-transparent animate-spin" />
            <span>LangGraph orchestration in progress (classifying, routing, retrieving)...</span>
          </div>
        )}

        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Sample prompt pills */}
      <div className="px-4 py-2 bg-slate-850/60 border-t border-slate-800/80 flex items-center gap-2 overflow-x-auto">
        <span className="text-[10px] uppercase font-bold text-slate-500 shrink-0">Try:</span>
        {samplePrompts.map((p, i) => (
          <button
            key={i}
            onClick={() => handleSend(p.text)}
            disabled={isLoading}
            className="shrink-0 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700/60 text-[11px] text-slate-300 transition"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Input box */}
      <div className="p-4 bg-slate-850 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isLoading}
            placeholder="Ask about Indian laws, scheme benefits, or eligibility in simple language..."
            className="flex-1 px-4 py-3 rounded-xl bg-slate-900 border border-slate-750 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-teal-400 transition"
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="px-5 py-3 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-40 disabled:hover:bg-teal-500 text-slate-950 font-bold text-sm flex items-center gap-2 transition shadow-md shadow-teal-500/10"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};
