import React, { useState, useRef } from 'react';
import {
  FileText,
  Upload,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Check,
  Trash2,
  FileSearch,
  ScanText,
  ChevronLeft,
  ChevronRight,
  Clock,
  Layers,
  Sparkles,
  Send,
  ExternalLink,
  RefreshCw,
  Search,
} from 'lucide-react';
import {
  uploadDocument,
  getDocumentPages,
  deleteDocument,
  indexDocument,
  querySpecificDocument,
  getDocumentChunks,
} from '../../services/api';

export const DocumentUploadSection = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState(null);

  // Document Pages & Viewer State
  const [documentPages, setDocumentPages] = useState(null);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [loadingPages, setLoadingPages] = useState(false);
  const [copied, setCopied] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Phase 3: RAG Q&A State
  const [ragQuery, setRagQuery] = useState('');
  const [ragLoading, setRagLoading] = useState(false);
  const [ragResponse, setRagResponse] = useState(null);
  const [ragError, setRagError] = useState('');
  const [reindexing, setReindexing] = useState(false);

  // Chunks Inspection Modal
  const [showChunksModal, setShowChunksModal] = useState(false);
  const [chunksList, setChunksList] = useState([]);
  const [loadingChunks, setLoadingChunks] = useState(false);

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadError('Please select a valid PDF file (.pdf extension).');
        setSelectedFile(null);
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setUploadError('File size exceeds the 10 MB limit.');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setUploadError('');
      setUploadSuccess(null);
      setDocumentPages(null);
      setRagResponse(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please choose a PDF file to upload.');
      return;
    }

    setUploading(true);
    setUploadError('');
    setUploadSuccess(null);
    setRagResponse(null);

    try {
      const res = await uploadDocument(selectedFile);
      if (res.success && res.data) {
        setUploadSuccess(res.data);
        await loadPages(res.data.document_id);
      } else {
        setUploadError(res.error || 'Document processing failed.');
      }
    } catch {
      setUploadError('An unexpected client error occurred during upload.');
    } finally {
      setUploading(false);
    }
  };

  const loadPages = async (documentId) => {
    setLoadingPages(true);
    try {
      const res = await getDocumentPages(documentId);
      if (res.success && res.data) {
        setDocumentPages(res.data);
        setCurrentPageIndex(0);
      }
    } catch {
      // Ignored
    } finally {
      setLoadingPages(false);
    }
  };

  const handleReindex = async () => {
    if (!uploadSuccess?.document_id) return;
    setReindexing(true);
    setUploadError('');
    try {
      const res = await indexDocument(uploadSuccess.document_id);
      if (res.success && res.data) {
        setUploadSuccess((prev) => ({
          ...prev,
          processing_status: res.data.processing_status,
          chunks_indexed: res.data.chunks_indexed,
        }));
      } else {
        setUploadError(res.error || 'Re-indexing failed.');
      }
    } catch {
      setUploadError('Failed to trigger re-indexing.');
    } finally {
      setReindexing(false);
    }
  };

  const handleInspectChunks = async () => {
    if (!uploadSuccess?.document_id) return;
    setLoadingChunks(true);
    setShowChunksModal(true);
    try {
      const res = await getDocumentChunks(uploadSuccess.document_id);
      if (res.success && res.data) {
        setChunksList(res.data.chunks || []);
      }
    } catch {
      // Ignored
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleRagSearch = async (customQuery = null) => {
    const q = (customQuery || ragQuery).trim();
    if (!q || !uploadSuccess?.document_id) return;

    setRagLoading(true);
    setRagError('');
    setRagResponse(null);

    try {
      const res = await querySpecificDocument(uploadSuccess.document_id, q);
      if (res.success && res.data) {
        setRagResponse(res.data);
      } else {
        setRagError(res.error || 'Failed to generate grounded answer.');
      }
    } catch {
      setRagError('An unexpected error occurred during semantic retrieval.');
    } finally {
      setRagLoading(false);
    }
  };

  const jumpToPage = (pageNum) => {
    if (!documentPages?.pages) return;
    const index = documentPages.pages.findIndex((p) => p.page_number === pageNum);
    if (index !== -1) {
      setCurrentPageIndex(index);
    }
  };

  const handleDelete = async () => {
    if (!uploadSuccess?.document_id) return;
    if (!window.confirm('Are you sure you want to delete this document and its indexed vector chunks?')) return;

    setDeleting(true);
    try {
      const res = await deleteDocument(uploadSuccess.document_id);
      if (res.success) {
        setSelectedFile(null);
        setUploadSuccess(null);
        setDocumentPages(null);
        setRagResponse(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      } else {
        setUploadError(res.error || 'Failed to delete document.');
      }
    } catch {
      setUploadError('Failed to execute document deletion.');
    } finally {
      setDeleting(false);
    }
  };

  const handleCopyText = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 KB';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const currentPage = documentPages?.pages?.[currentPageIndex];

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-semibold mb-3">
          <FileText className="w-3.5 h-3.5" />
          <span>Source C: Document Intelligence (RAG)</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Government Notice Ingestion & RAG Search
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Upload official gazettes or policy circulars. PyMuPDF extracts text page-by-page,
          Sentence Transformers generates multilingual embeddings, and ChromaDB enables semantic Q&A.
        </p>
      </div>

      {/* Upload Drop Zone Card */}
      <div className="max-w-2xl mx-auto">
        <div className="p-8 rounded-2xl bg-slate-900 border-2 border-dashed border-slate-700 hover:border-teal-500/60 transition text-center space-y-4 shadow-sm">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            className="hidden"
            id="pdf-upload-input"
          />

          <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-teal-400">
            <Upload className="w-6 h-6" />
          </div>

          <div>
            <label
              htmlFor="pdf-upload-input"
              className="cursor-pointer text-sm font-semibold text-teal-400 hover:text-teal-300 transition"
            >
              Choose a PDF document
            </label>
            <span className="text-xs text-slate-400"> or drag and drop here</span>
            <p className="text-[11px] text-slate-500 mt-1">
              Supports official government circulars, notices, PDFs up to 10 MB.
            </p>
          </div>

          {selectedFile && (
            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs text-left">
              <div className="flex items-center gap-2.5 truncate">
                <FileSearch className="w-4 h-4 text-teal-400 shrink-0" />
                <span className="font-medium text-white truncate">{selectedFile.name}</span>
                <span className="text-slate-500 shrink-0">({formatFileSize(selectedFile.size)})</span>
              </div>
              <button
                type="button"
                onClick={handleUpload}
                disabled={uploading}
                className="px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition disabled:opacity-40 shrink-0 shadow-sm"
              >
                {uploading ? 'Processing & Indexing...' : 'Upload & Index'}
              </button>
            </div>
          )}

          {uploadError && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2 text-left">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>
      </div>

      {/* Upload Success Banner & Indexing Status */}
      {uploadSuccess && (
        <div className="max-w-4xl mx-auto p-4 sm:p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 font-bold text-sm">
                PDF
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">{uploadSuccess.filename}</h4>
                <p className="text-[11px] text-slate-400">
                  {uploadSuccess.page_count} Page(s) • {formatFileSize(uploadSuccess.file_size_bytes)}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                  uploadSuccess.processing_status === 'INDEXED'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : uploadSuccess.processing_status === 'OCR_REQUIRED'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-teal-500/10 text-teal-400 border border-teal-500/20'
                }`}
              >
                {uploadSuccess.processing_status.replace('_', ' ')}
              </span>

              {uploadSuccess.processing_status === 'INDEXED' && (
                <button
                  onClick={handleInspectChunks}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs border border-slate-700 transition"
                  title="Inspect ChromaDB chunks"
                >
                  Inspect Chunks ({uploadSuccess.chunks_indexed || 0})
                </button>
              )}

              <button
                onClick={handleReindex}
                disabled={reindexing}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 transition disabled:opacity-40"
                title="Re-index document"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${reindexing ? 'animate-spin text-teal-400' : ''}`} />
              </button>

              <button
                onClick={handleDelete}
                disabled={deleting}
                className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition"
                title="Delete document"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* RAG QUESTION ANSWERING INTERFACE */}
          {uploadSuccess.processing_status === 'INDEXED' && (
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-teal-300">
                  <Sparkles className="w-4 h-4 text-teal-400" />
                  <span>Ask Questions About This Document (Semantic RAG)</span>
                </div>
                <span className="text-[10px] text-slate-500">ChromaDB + Groq</span>
              </div>

              {/* RAG Input */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleRagSearch();
                }}
                className="flex items-center gap-2"
              >
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={ragQuery}
                    onChange={(e) => setRagQuery(e.target.value)}
                    placeholder="e.g., What are the penalties, rules, or eligibility dates in this circular?"
                    disabled={ragLoading}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-750 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-400"
                  />
                </div>
                <button
                  type="submit"
                  disabled={ragLoading || !ragQuery.trim()}
                  className="px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition disabled:opacity-40"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{ragLoading ? 'Searching...' : 'Ask'}</span>
                </button>
              </form>

              {/* RAG Response Display */}
              {ragResponse && (
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-750 space-y-3 animate-in fade-in">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                        ragResponse.grounding_status === 'GROUNDED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : ragResponse.grounding_status === 'PARTIALLY_GROUNDED'
                          ? 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}
                    >
                      {ragResponse.grounding_status}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {ragResponse.chunks_retrieved} chunk(s) retrieved
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                    {ragResponse.answer}
                  </p>

                  {/* Page Citations */}
                  {ragResponse.sources && ragResponse.sources.length > 0 && (
                    <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center gap-2">
                      <span className="text-[11px] font-semibold text-slate-400">Cited Pages:</span>
                      {ragResponse.sources.map((s, idx) => (
                        <button
                          key={idx}
                          onClick={() => jumpToPage(s.page_number)}
                          className="px-2 py-0.5 rounded-md bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 text-[10px] font-mono transition"
                          title="Click to view this page in the viewer below"
                        >
                          Page {s.page_number} {s.similarity_score ? `(${Math.round(s.similarity_score * 100)}%)` : ''}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {ragError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                  {ragError}
                </div>
              )}
            </div>
          )}

          {/* PAGE-BY-PAGE VIEWER */}
          {documentPages && documentPages.pages && documentPages.pages.length > 0 && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between text-xs text-slate-300">
                <span className="font-semibold text-white">Document Page-by-Page Extract:</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPageIndex((prev) => Math.max(0, prev - 1))}
                    disabled={currentPageIndex === 0}
                    className="p-1 rounded-lg bg-slate-800 hover:bg-slate-750 disabled:opacity-30 transition"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="font-mono text-xs">
                    Page {currentPageIndex + 1} of {documentPages.total_pages}
                  </span>
                  <button
                    onClick={() =>
                      setCurrentPageIndex((prev) =>
                        Math.min(documentPages.pages.length - 1, prev + 1)
                      )
                    }
                    disabled={currentPageIndex === documentPages.pages.length - 1}
                    className="p-1 rounded-lg bg-slate-800 hover:bg-slate-750 disabled:opacity-30 transition"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Page Content Card */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed relative">
                {currentPage?.text || (
                  <span className="text-slate-500 italic">No extractable text on this page.</span>
                )}
                {currentPage?.text && (
                  <button
                    onClick={() => handleCopyText(currentPage.text)}
                    className="absolute top-3 right-3 p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-750 text-slate-400 hover:text-white transition"
                    title="Copy page text"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-teal-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* CHUNKS INSPECTION MODAL */}
      {showChunksModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-teal-400" />
                <span>Indexed ChromaDB Chunks ({chunksList.length})</span>
              </h4>
              <button
                onClick={() => setShowChunksModal(false)}
                className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded-lg bg-slate-800"
              >
                Close
              </button>
            </div>
            <div className="p-4 overflow-y-auto space-y-3 flex-1">
              {loadingChunks ? (
                <p className="text-xs text-slate-400">Loading chunks from ChromaDB...</p>
              ) : chunksList.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No chunks found.</p>
              ) : (
                chunksList.map((c, i) => (
                  <div key={i} className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] text-teal-400 font-mono">
                      <span>Chunk #{c.metadata.chunk_index} (Page {c.metadata.page_number})</span>
                      <span className="text-slate-500">{c.metadata.token_count} tokens</span>
                    </div>
                    {c.metadata.section_heading && (
                      <p className="text-[10px] text-amber-300 font-semibold">{c.metadata.section_heading}</p>
                    )}
                    <p className="text-slate-300 leading-relaxed font-sans">{c.content}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
