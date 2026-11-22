import React from 'react';

/**
 * Lightweight, zero-dependency Markdown formatter for chat messages.
 * Handles headings, bold/italic, bullet/numbered lists, inline code,
 * blockquotes, and paragraphs without external bundle dependencies.
 */
export const FormattedMessage = ({ content }) => {
  if (!content) return null;

  // Split into lines for structured block rendering
  const lines = content.split('\n');
  const elements = [];
  let currentList = [];
  let listType = null; // 'ul' | 'ol'

  const flushList = () => {
    if (currentList.length > 0) {
      if (listType === 'ol') {
        elements.push(
          <ol key={`ol-${elements.length}`} className="list-decimal pl-5 space-y-1 my-2 text-slate-200">
            {currentList.map((item, idx) => (
              <li key={idx} className="leading-relaxed">{renderInline(item)}</li>
            ))}
          </ol>
        );
      } else {
        elements.push(
          <ul key={`ul-${elements.length}`} className="list-disc pl-5 space-y-1 my-2 text-slate-200">
            {currentList.map((item, idx) => (
              <li key={idx} className="leading-relaxed">{renderInline(item)}</li>
            ))}
          </ul>
        );
      }
      currentList = [];
      listType = null;
    }
  };

  const renderInline = (text) => {
    // Process bold, italic, code, links
    // First, handle inline code: `code`
    const parts = text.split(/(`[^`]+`)/g);

    return parts.map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`') && part.length > 1) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-teal-300 font-mono text-xs border border-slate-700/60">
            {part.slice(1, -1)}
          </code>
        );
      }

      // Handle bold: **text**
      const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
      return boldParts.map((bPart, j) => {
        if (bPart.startsWith('**') && bPart.endsWith('**') && bPart.length > 3) {
          return <strong key={`${i}-${j}`} className="font-semibold text-white">{bPart.slice(2, -2)}</strong>;
        }

        // Handle italic: *text*
        const italicParts = bPart.split(/(\*[^*]+\*)/g);
        return italicParts.map((itPart, k) => {
          if (itPart.startsWith('*') && itPart.endsWith('*') && itPart.length > 2) {
            return <em key={`${i}-${j}-${k}`} className="italic text-slate-300">{itPart.slice(1, -1)}</em>;
          }
          return itPart;
        });
      });
    });
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Empty lines
    if (!trimmed) {
      flushList();
      elements.push(<div key={`space-${index}`} className="h-2" />);
      return;
    }

    // Headings
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={`h4-${index}`} className="text-sm font-bold text-white mt-3 mb-1.5 flex items-center gap-1.5">
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      return;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={`h3-${index}`} className="text-base font-bold text-teal-300 mt-4 mb-2">
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      return;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={`h2-${index}`} className="text-lg font-bold text-teal-400 mt-4 mb-2">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
      return;
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      flushList();
      elements.push(
        <blockquote key={`quote-${index}`} className="border-l-2 border-teal-500/50 pl-3 py-1 my-1.5 text-slate-300 italic bg-teal-500/5 rounded-r">
          {renderInline(trimmed.slice(2))}
        </blockquote>
      );
      return;
    }

    // Bullet lists: - or *
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (listType !== 'ul') {
        flushList();
        listType = 'ul';
      }
      currentList.push(trimmed.slice(2));
      return;
    }

    // Numbered lists: 1. , 2. , etc.
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numberedMatch) {
      if (listType !== 'ol') {
        flushList();
        listType = 'ol';
      }
      currentList.push(numberedMatch[2]);
      return;
    }

    // Regular paragraph
    flushList();
    elements.push(
      <p key={`p-${index}`} className="my-1 leading-relaxed text-slate-200">
        {renderInline(line)}
      </p>
    );
  });

  flushList();

  return <div className="space-y-0.5">{elements}</div>;
};
