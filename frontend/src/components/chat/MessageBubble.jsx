import React, { useState, useRef, useEffect } from 'react';
import { FormattedMessage } from './FormattedMessage';
import {
  User,
  Sparkles,
  ExternalLink,
  Scale,
  FileText,
  Gift,
  ShieldCheck,
  AlertTriangle,
  Paperclip,
  Volume2,
  VolumeX,
  Loader2,
} from 'lucide-react';
import { convertTextToSpeech } from '../../services/api';

const intentLabels = {
  LAW_INFORMATION: 'Legal Information',
  SCHEME_INFORMATION: 'Scheme Details',
  SCHEME_ELIGIBILITY: 'Eligibility Assessment',
  DOCUMENT_QA: 'Document Analysis',
  GENERAL_QUERY: 'General',
  MULTI_INTENT: 'Multi-Topic',
};

const intentColors = {
  LAW_INFORMATION: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  SCHEME_INFORMATION: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  SCHEME_ELIGIBILITY: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  DOCUMENT_QA: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  GENERAL_QUERY: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
  MULTI_INTENT: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
};

export const MessageBubble = ({ message, language = 'en' }) => {
  const isUser = message.role === 'user';
  const isError = message.isError;

  // TTS audio playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [speechError, setSpeechError] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handleToggleSpeech = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    if (audioRef.current) {
      audioRef.current.play();
      setIsPlaying(true);
      return;
    }

    setIsLoadingAudio(true);
    try {
      const res = await convertTextToSpeech(message.content, language);
      if (res.success && res.data?.audio_base64) {
        const audio = new Audio(`data:audio/wav;base64,${res.data.audio_base64}`);
        audioRef.current = audio;

        audio.onended = () => {
          setIsPlaying(false);
          audioRef.current = null;
        };
        audio.onerror = () => {
          setIsPlaying(false);
          audioRef.current = null;
        };

        await audio.play();
        setIsPlaying(true);
      } else {
        const errMsg = res.data?.error || res.error || 'TTS generation failed';
        setSpeechError(errMsg);
        setTimeout(() => setSpeechError(null), 5000);
      }
    } catch (err) {
      console.error('TTS playback error:', err);
      setSpeechError('Failed to play speech audio');
      setTimeout(() => setSpeechError(null), 5000);
    } finally {
      setIsLoadingAudio(false);
    }
  };

  return (
    <div className={`flex gap-3 py-3.5 fade-in ${isUser ? 'justify-end' : ''}`}>
      {/* Assistant avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md shadow-teal-500/10">
          {isError ? (
            <AlertTriangle className="w-4 h-4 text-white" />
          ) : (
            <Sparkles className="w-4 h-4 text-white" />
          )}
        </div>
      )}

      {/* Message content */}
      <div className={`max-w-[85%] sm:max-w-[78%] min-w-0 ${isUser ? 'order-first' : ''}`}>
        {/* User message */}
        {isUser && (
          <div className={`rounded-2xl rounded-br-sm px-4 py-3 shadow-sm ${
            message.isUpload
              ? 'bg-slate-800/90 border border-slate-700/60'
              : 'bg-teal-600/90 text-white font-medium'
          }`}>
            {message.isUpload ? (
              <div className="flex items-center gap-2 text-sm text-slate-200">
                <Paperclip className="w-4 h-4 text-teal-400" />
                <span>{message.content}</span>
              </div>
            ) : (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            )}
          </div>
        )}

        {/* Assistant message */}
        {!isUser && (
          <div className="space-y-2">
            {/* Header with intent badge & Voice Listen button */}
            <div className="flex items-center justify-between gap-2 flex-wrap">
              {message.intent && !isError && (
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider border ${
                  intentColors[message.intent] || intentColors.GENERAL_QUERY
                }`}>
                  {intentLabels[message.intent] || message.intent}
                </span>
              )}

              {/* Sarvam TTS Listen Button */}
              {!isError && (
                <div className="flex items-center gap-2">
                  {speechError && (
                    <span className="text-[11px] text-amber-400 max-w-[200px] truncate" title={speechError}>
                      {speechError}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={handleToggleSpeech}
                    disabled={isLoadingAudio}
                    className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                      isPlaying
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`}
                    title="Listen to response (Sarvam AI TTS)"
                  >
                    {isLoadingAudio ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
                        <span className="text-[11px]">Generating audio...</span>
                      </>
                    ) : isPlaying ? (
                      <>
                        <VolumeX className="w-3.5 h-3.5 text-teal-400" />
                        <span className="text-[11px]">Pause speech</span>
                      </>
                    ) : (
                      <>
                        <Volume2 className="w-3.5 h-3.5 text-slate-400 hover:text-teal-400" />
                        <span className="text-[11px]">Listen</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Message body */}
            <div className={`text-sm leading-relaxed ${
              isError ? 'text-red-300' : 'text-slate-200'
            }`}>
              {isError ? (
                <div className="flex items-start gap-2 p-3.5 rounded-xl bg-red-500/10 border border-red-500/20">
                  <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <p>{message.content}</p>
                </div>
              ) : (
                <div className="px-1">
                  <FormattedMessage content={message.content} />
                </div>
              )}
            </div>

            {/* Source Citations */}
            {message.sources && message.sources.length > 0 && (
              <SourceCitations sources={message.sources} />
            )}
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
          <User className="w-4 h-4 text-slate-300" />
        </div>
      )}
    </div>
  );
};

const SourceCitations = ({ sources }) => {
  return (
    <div className="mt-3 pt-3 border-t border-slate-800/80">
      <h5 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
        Verified Sources ({sources.length})
      </h5>
      <div className="flex flex-wrap gap-2">
        {sources.map((src, i) => {
          const isLaw = src.type?.includes('nyaykosh') || src.type?.includes('law');
          const isDoc = src.type?.includes('pdf') || src.type?.includes('document');

          const Icon = isLaw ? Scale : isDoc ? FileText : Gift;
          const iconColor = isLaw ? 'text-blue-400' : isDoc ? 'text-cyan-400' : 'text-emerald-400';

          return (
            <div
              key={i}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-850 border border-slate-750 text-xs shadow-sm hover:border-slate-650 transition-colors"
            >
              <Icon className={`w-3.5 h-3.5 ${iconColor} flex-shrink-0`} />
              <span className="text-slate-300 truncate max-w-[220px]">{src.title}</span>
              {src.url && !src.url.startsWith('document://') && (
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-teal-400 hover:text-teal-300 ml-0.5"
                  title="View official source"
                >
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
