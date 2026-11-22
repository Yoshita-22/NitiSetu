import React from 'react';
import {
  Scale,
  Gift,
  FileText,
  ShieldCheck,
  Sparkles,
  ArrowRight,
} from 'lucide-react';

const WELCOME_TEXT = {
  en: {
    greeting: "Namaste! I'm NitiSetu",
    subtitle: "Your AI-powered civic information assistant. I can help you with:",
    features: [
      { icon: Scale, label: 'Laws & Rights', desc: 'Indian legal provisions, sections, and your citizen rights' },
      { icon: Gift, label: 'Government Schemes', desc: 'Benefits, eligibility, and application process for welfare schemes' },
      { icon: ShieldCheck, label: 'Eligibility Check', desc: 'Interactive assessment to check your scheme eligibility' },
      { icon: FileText, label: 'Document Analysis', desc: 'Upload government notices or PDFs for instant AI explanations' },
    ],
    prompts: [
      'What is Section 498A of IPC?',
      'Am I eligible for PM-KISAN scheme?',
      'Tell me about Ayushman Bharat benefits',
      'Explain Consumer Protection Act rights',
    ],
  },
  te: {
    greeting: "నమస్తే! నేను NitiSetu",
    subtitle: "మీ AI-ఆధారిత పౌర సమాచార సహాయకుడు. నేను మీకు సహాయం చేయగలను:",
    features: [
      { icon: Scale, label: 'చట్టాలు & హక్కులు', desc: 'భారతీయ చట్ట నిబంధనలు, సెక్షన్లు మరియు మీ పౌర హక్కులు' },
      { icon: Gift, label: 'ప్రభుత్వ పథకాలు', desc: 'సంక్షేమ పథకాల ప్రయోజనాలు, అర్హత మరియు దరఖాస్తు ప్రక్రియ' },
      { icon: ShieldCheck, label: 'అర్హత తనిఖీ', desc: 'మీ పథకం అర్హతను తనిఖీ చేయడానికి ఇంటరాక్టివ్ అసెస్మెంట్' },
      { icon: FileText, label: 'పత్ర విశ్లేషణ', desc: 'ప్రభుత్వ నోటీసులు లేదా PDFలను అప్‌లోడ్ చేయండి' },
    ],
    prompts: [
      'IPC సెక్షన్ 498A ఏమిటి?',
      'నేను PM-KISAN పథకానికి అర్హుడను?',
      'ఆయుష్మాన్ భారత్ ప్రయోజనాల గురించి చెప్పండి',
      'వినియోగదారు రక్షణ చట్టం హక్కులు వివరించండి',
    ],
  },
  hi: {
    greeting: "नमस्ते! मैं NitiSetu हूँ",
    subtitle: "आपका AI-संचालित नागरिक सूचना सहायक। मैं इनमें मदद कर सकता हूँ:",
    features: [
      { icon: Scale, label: 'कानून और अधिकार', desc: 'भारतीय कानूनी प्रावधान, धाराएं और आपके नागरिक अधिकार' },
      { icon: Gift, label: 'सरकारी योजनाएं', desc: 'कल्याण योजनाओं के लाभ, पात्रता और आवेदन प्रक्रिया' },
      { icon: ShieldCheck, label: 'पात्रता जांच', desc: 'आपकी योजना पात्रता की जांच के लिए इंटरएक्टिव मूल्यांकन' },
      { icon: FileText, label: 'दस्तावेज़ विश्लेषण', desc: 'सरकारी नोटिस या PDF अपलोड करें' },
    ],
    prompts: [
      'IPC की धारा 498A क्या है?',
      'क्या मैं PM-KISAN योजना के लिए पात्र हूँ?',
      'आयुष्मान भारत के लाभ बताइए',
      'उपभोक्ता संरक्षण अधिनियम के अधिकार समझाइए',
    ],
  },
};

export const WelcomeScreen = ({ onSendMessage, language = 'en' }) => {
  const t = WELCOME_TEXT[language] || WELCOME_TEXT.en;

  return (
    <div className="h-full flex flex-col items-center justify-center px-4 pb-4 overflow-y-auto">
      <div className="max-w-2xl w-full space-y-8 slide-up">
        {/* Greeting */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-teal-500 to-cyan-600 shadow-xl shadow-teal-500/20 mb-2">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {t.greeting}
          </h2>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            {t.subtitle}
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {t.features.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <div
                key={i}
                className="flex items-start gap-3 p-4 rounded-xl bg-slate-800/30 border border-slate-700/40 hover:border-slate-600/50 transition-colors"
              >
                <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4.5 h-4.5 text-teal-400" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-200">{feature.label}</h3>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{feature.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Suggested Prompts */}
        <div className="space-y-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {t.prompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => onSendMessage(prompt)}
                className="group flex items-center justify-between gap-2 px-4 py-3 rounded-xl bg-slate-800/40 border border-slate-700/40 hover:border-teal-500/30 hover:bg-slate-800/60 text-left text-sm text-slate-300 hover:text-white transition-all"
              >
                <span className="line-clamp-1">{prompt}</span>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-teal-400 flex-shrink-0 transition-colors" />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
