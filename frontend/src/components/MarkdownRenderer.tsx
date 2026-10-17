"use client";

import React, { useMemo } from "react";
import { marked } from "marked";
import katex from "katex";
import DOMPurify from "dompurify";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Normalizes and pre-processes LaTeX expressions in text before Markdown parsing.
 * Supports:
 * - Block display math: \[ ... \] or $$ ... $$
 * - Inline math: \( ... \) or $ ... $
 * Also normalizes double-escaped commands like \\( \\text{NaCl} \\) or \\( \\ext{NaCl} \\)
 */
function processMathAndMarkdown(rawText: string): string {
  if (!rawText) return "";

  // 1. First normalize common escaped sequences from AI or JSON strings
  // E.g., replace `\ext{...}` with `\text{...}` if typo occurred
  let text = rawText.replace(/\\ext\{/g, "\\text{");

  // Fix escaped backslashes in math delimiters: `\\(` -> `\(` and `\\)` -> `\)`
  text = text.replace(/\\\\\(/g, "\\(").replace(/\\\\\)/g, "\\)");
  text = text.replace(/\\\\\[/g, "\\[").replace(/\\\\\]/g, "\\]");

  const mathPlaceholders: { placeholder: string; rendered: string }[] = [];
  let placeholderCount = 0;

  // Helper to safely render KaTeX
  const renderKaTeX = (math: string, displayMode: boolean): string => {
    try {
      const trimmed = math.trim();
      return katex.renderToString(trimmed, {
        displayMode,
        throwOnError: false,
        output: "htmlAndMathml",
      });
    } catch {
      // Fallback: Return raw math escaped
      return `<code class="katex-fallback">${math}</code>`;
    }
  };

  // 2. Extract block math: \[ ... \] and $$ ... $$
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => {
    const placeholder = `%%KATEX_BLOCK_${placeholderCount++}%%`;
    mathPlaceholders.push({
      placeholder,
      rendered: `<div class="katex-display my-2 overflow-x-auto">${renderKaTeX(math, true)}</div>`,
    });
    return placeholder;
  });

  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, math) => {
    const placeholder = `%%KATEX_BLOCK_${placeholderCount++}%%`;
    mathPlaceholders.push({
      placeholder,
      rendered: `<div class="katex-display my-2 overflow-x-auto">${renderKaTeX(math, true)}</div>`,
    });
    return placeholder;
  });

  // 3. Extract inline math: \( ... \)
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => {
    const placeholder = `%%KATEX_INLINE_${placeholderCount++}%%`;
    mathPlaceholders.push({
      placeholder,
      rendered: renderKaTeX(math, false),
    });
    return placeholder;
  });

  // 4. Extract inline math: $...$ (avoiding currency amounts like $50 or $100 by checking for non-digit or math operators)
  text = text.replace(/(^|[^\\])\$([^\$\n]+?)\$/g, (match, prefix, math) => {
    // If it looks like a currency ($50 or $100), skip
    if (/^\d+(\.\d+)?$/.test(math.trim())) {
      return match;
    }
    const placeholder = `%%KATEX_INLINE_${placeholderCount++}%%`;
    mathPlaceholders.push({
      placeholder,
      rendered: renderKaTeX(math, false),
    });
    return `${prefix}${placeholder}`;
  });

  // 5. Parse Markdown with marked
  marked.setOptions({
    gfm: true,
    breaks: true,
  });

  let html = marked.parse(text) as string;

  // 6. Restore KaTeX placeholders
  for (const item of mathPlaceholders) {
    // Some placeholders might be wrapped in <p> if marked treated them as paragraphs
    html = html.replace(new RegExp(item.placeholder, "g"), item.rendered);
  }

  // 7. Sanitize HTML with DOMPurify while allowing KaTeX tags and mathml
  if (typeof window !== "undefined") {
    html = DOMPurify.sanitize(html, {
      ADD_TAGS: [
        "math", "semantics", "mrow", "mi", "mo", "mn", "ms", "mspace", "mtext",
        "annotation", "annotation-xml", "span", "div", "svg", "path", "line"
      ],
      ADD_ATTR: [
        "aria-hidden", "style", "viewBox", "preserveAspectRatio", "height", "width",
        "d", "fill", "stroke", "stroke-width", "class", "xmlns", "display"
      ],
    });
  }

  return html;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const renderedHtml = useMemo(() => {
    return processMathAndMarkdown(content);
  }, [content]);

  return (
    <div
      className={`markdown-content ${className}`}
      dangerouslySetInnerHTML={{ __html: renderedHtml }}
    />
  );
}
