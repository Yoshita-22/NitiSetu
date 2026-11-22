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
} from 'lucide-react';
import { uploadDocument, getDocumentPages, deleteDocument } from '../../services/api';

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

    try {
      const res = await uploadDocument(selectedFile);
      if (res.success && res.data) {
        setUploadSuccess(res.data);
        // Automatically fetch extracted pages
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
      // Handled silently or displays error
    } finally {
      setLoadingPages(false);
    }
  };

  const handleDelete = async () => {
    if (!uploadSuccess?.document_id) return;
    if (!window.confirm('Are you sure you want to delete this document from memory?')) return;

    setDeleting(true);
    try {
      const res = await deleteDocument(uploadSuccess.document_id);
      if (res.success) {
        setSelectedFile(null);
        setUploadSuccess(null);
        setDocumentPages(null);
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
          <span>Source C: Document Intelligence</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Government Notice & Circular Ingestion
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Upload official gazettes, department circulars, or policy orders.
          Extracts full text page-by-page using PyMuPDF and detects scanned documents.
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
                {uploading ? 'Extracting Text...' : 'Process Document'}
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

      {/* Processing Status Banner */}
      {uploadSuccess && (
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white truncate max-w-md">
                  {uploadSuccess.filename}
                </h3>
                <span className="text-xs text-slate-500">
                  ({formatFileSize(uploadSuccess.file_size_bytes)})
                </span>
              </div>
              <p className="text-xs text-slate-400">{uploadSuccess.message}</p>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              {uploadSuccess.processing_status === 'COMPLETED' ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-xs font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>COMPLETED ({uploadSuccess.page_count} Pages)</span>
                </div>
              ) : uploadSuccess.processing_status === 'OCR_REQUIRED' ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs font-semibold">
                  <ScanText className="w-3.5 h-3.5 text-amber-400" />
                  <span>OCR_REQUIRED (Scanned Document)</span>
                </div>
              ) : (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-xs">
                  <span>{uploadSuccess.processing_status}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                title="Delete document"
                className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-rose-400 hover:bg-slate-750 transition"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* OCR Required Explanation Alert */}
          {uploadSuccess.processing_status === 'OCR_REQUIRED' && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 flex items-start gap-3">
              <ScanText className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-white">Scanned PDF Detected (OCR Required)</p>
                <p className="text-[11px] text-amber-200/90 mt-1 leading-relaxed">
                  This PDF consists of scanned raster images or has less than the minimum digital text threshold.
                  In Phase 1, PyMuPDF digital text extraction is active. Optical Character Recognition (OCR)
                  for scanned vernacular gazettes is designated for Phase 2.
                </p>
              </div>
            </div>
          )}

          {/* Page-by-Page Interactive Viewer */}
          {documentPages && documentPages.pages.length > 0 && (
            <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
              {/* Viewer Navigation Bar */}
              <div className="px-5 py-3 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <Layers className="w-4 h-4 text-teal-400" />
                  <span className="font-semibold text-white">
                    Page {currentPageIndex + 1} of {documentPages.total_pages}
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="text-slate-400">
                    {currentPage?.word_count || 0} words ({currentPage?.character_count || 0} chars)
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleCopyText(currentPage?.text)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs border border-slate-700 transition"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copied ? 'Copied' : 'Copy Page Text'}</span>
                  </button>

                  <div className="flex items-center gap-1 border-l border-slate-750 pl-2">
                    <button
                      type="button"
                      disabled={currentPageIndex <= 0}
                      onClick={() => setCurrentPageIndex((prev) => Math.max(0, prev - 1))}
                      className="p-1.5 rounded bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 transition"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      disabled={currentPageIndex >= documentPages.total_pages - 1}
                      onClick={() => setCurrentPageIndex((prev) => Math.min(documentPages.total_pages - 1, prev + 1))}
                      className="p-1.5 rounded bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 transition"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Text Extract Box */}
              <div className="p-6 bg-slate-950/70 max-h-96 overflow-y-auto font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap selection:bg-teal-500 selection:text-slate-950">
                {currentPage?.text ? (
                  currentPage.text
                ) : (
                  <span className="text-slate-500 italic font-sans">
                    [No digital text extracted from this page. May contain scanned stamps, images, or signatures.]
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
