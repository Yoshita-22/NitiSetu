import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Send,
  Paperclip,
  Mic,
  Square,
  X,
  FileText,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { convertSpeechToText } from '../../services/api';

export const MessageComposer = ({
  onSendMessage,
  onFileUpload,
  isLoading,
  hasActiveDocument,
  language = 'en',
}) => {
  const [inputValue, setInputValue] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioAnalyser, setAudioAnalyser] = useState(null);

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const durationIntervalRef = useRef(null);
  const canvasRef = useRef(null);
  const animFrameRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [inputValue]);

  const handleSubmit = useCallback((e) => {
    e?.preventDefault();

    if (selectedFile) {
      onFileUpload(selectedFile);
      setSelectedFile(null);
      return;
    }

    if (!inputValue.trim() || isLoading) return;
    onSendMessage(inputValue.trim());
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [inputValue, selectedFile, isLoading, onSendMessage, onFileUpload]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // File selection
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    }
    e.target.value = '';
  };

  const removeFile = () => {
    setSelectedFile(null);
  };

  // Voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Audio context for visualization
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      setAudioAnalyser(analyser);

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        cleanup();
        setIsTranscribing(true);
        try {
          const res = await convertSpeechToText(blob, language);
          if (res.success && res.data?.transcript) {
            setInputValue(prev => (prev ? `${prev} ${res.data.transcript}` : res.data.transcript));
          }
        } catch (err) {
          console.error('STT conversion error:', err);
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      setIsRecording(true);
      setRecordingDuration(0);

      durationIntervalRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Microphone access denied:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    cleanup();
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    cleanup();
  };

  const cleanup = () => {
    setIsRecording(false);
    setRecordingDuration(0);
    setAudioAnalyser(null);

    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
      durationIntervalRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
  };

  // Draw waveform
  useEffect(() => {
    if (!audioAnalyser || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const bufferLength = audioAnalyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      audioAnalyser.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const barWidth = 3;
      const gap = 2;
      const totalBars = Math.floor(canvas.width / (barWidth + gap));
      const step = Math.floor(bufferLength / totalBars);

      for (let i = 0; i < totalBars; i++) {
        const value = dataArray[i * step] || 0;
        const barHeight = Math.max(2, (value / 255) * canvas.height * 0.8);

        const x = i * (barWidth + gap);
        const y = (canvas.height - barHeight) / 2;

        ctx.fillStyle = `rgba(20, 184, 166, ${0.4 + (value / 255) * 0.6})`;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 1);
        ctx.fill();
      }
    };

    draw();

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [audioAnalyser]);

  const formatDuration = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const canSend = (inputValue.trim() || selectedFile) && !isLoading;

  return (
    <div className="flex-shrink-0 border-t border-slate-800/60 bg-navy-950/80 backdrop-blur-sm">
      {/* Active document indicator */}
      {hasActiveDocument && (
        <div className="px-4 pt-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-[10px] text-cyan-400">
            <FileText className="w-3 h-3" />
            <span>Document active — questions will reference uploaded PDF</span>
          </div>
        </div>
      )}

      {/* File preview */}
      {selectedFile && (
        <div className="px-4 pt-2">
          <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/40">
            <FileText className="w-4 h-4 text-teal-400" />
            <div className="text-xs">
              <p className="text-slate-200 font-medium">{selectedFile.name}</p>
              <p className="text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
            </div>
            <button
              onClick={removeFile}
              className="p-1 rounded-md hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Recording UI */}
      {isRecording && (
        <div className="px-4 pt-3">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/40 border border-teal-500/20">
            <div className="w-3 h-3 rounded-full bg-red-500 pulse-glow flex-shrink-0" />
            <span className="text-xs text-slate-300 font-medium">Listening...</span>
            <canvas
              ref={canvasRef}
              width={200}
              height={32}
              className="flex-1 max-w-[200px]"
            />
            <span className="text-xs text-slate-400 font-mono tabular-nums">
              {formatDuration(recordingDuration)}
            </span>
            <button
              onClick={stopRecording}
              className="p-1.5 rounded-lg bg-teal-500 text-slate-950 hover:bg-teal-400 transition-colors"
              title="Stop recording"
            >
              <Square className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={cancelRecording}
              className="p-1.5 rounded-lg bg-slate-700/50 text-slate-300 hover:bg-slate-600/50 transition-colors"
              title="Cancel recording"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Transcribing indicator */}
      {isTranscribing && (
        <div className="px-4 pt-2.5">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-teal-500/10 border border-teal-500/20 text-xs text-teal-300">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
            <span>Transcribing speech with Sarvam AI Saarika...</span>
          </div>
        </div>
      )}

      {/* Composer */}
      <div className="p-3 sm:p-4">
        <div className="max-w-chat mx-auto">
          <form
            onSubmit={handleSubmit}
            className="flex items-end gap-2 p-2 rounded-2xl bg-slate-800/40 border border-slate-700/40 focus-within:border-teal-500/30 transition-colors"
          >
            {/* Left buttons */}
            <div className="flex items-center gap-1 pb-0.5">
              {/* Attachment button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/40 transition-colors"
                title="Attach PDF document"
                disabled={isRecording}
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileChange}
                className="hidden"
              />

              {/* Microphone button */}
              {!isRecording && (
                <button
                  type="button"
                  onClick={startRecording}
                  className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/40 transition-colors"
                  title="Voice input"
                >
                  <Mic className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Text input */}
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading || isRecording}
              placeholder="Ask about Indian laws, schemes, eligibility, or upload a document..."
              rows={1}
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none resize-none max-h-40 py-2 px-1"
            />

            {/* Send button */}
            <div className="pb-0.5">
              <button
                type="submit"
                disabled={!canSend}
                className="p-2 rounded-lg bg-teal-500 hover:bg-teal-400 disabled:opacity-30 disabled:hover:bg-teal-500 text-slate-950 transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>

          <p className="text-center text-[10px] text-slate-600 mt-2">
            NitiSetu uses verified data sources. Always verify critical information with official sources.
          </p>
        </div>
      </div>
    </div>
  );
};
