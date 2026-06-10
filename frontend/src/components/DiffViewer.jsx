/**
 * src/components/DiffViewer.jsx
 * ------------------------------
 * Monaco Editor in diff mode to display the Helix-generated fix patch.
 * Uses vs-dark theme, read-only, max-height 400px with internal scroll.
 * Gracefully handles Monaco not loading (e.g. ad-blockers, slow CDN).
 */

import { useState } from 'react'
import { DiffEditor } from '@monaco-editor/react'

/**
 * Parse a unified diff string into (original, modified) text pairs.
 * Returns the modified content on the right and removed lines on left.
 * @param {string} patch
 * @returns {{ original: string, modified: string, filename: string }}
 */
function parsePatch(patch) {
  if (!patch) return { original: '', modified: '', filename: '' }

  const lines = patch.split('\n')
  const original = []
  const modified = []
  let filename = ''

  for (const line of lines) {
    if (line.startsWith('+++ b/')) {
      filename = line.slice(6).trim()
    } else if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@') || line.startsWith('diff')) {
      continue
    } else if (line.startsWith('-')) {
      original.push(line.slice(1))
    } else if (line.startsWith('+')) {
      modified.push(line.slice(1))
    } else {
      // Context line — appears in both
      original.push(line)
      modified.push(line)
    }
  }

  return {
    original: original.join('\n'),
    modified: modified.join('\n'),
    filename,
  }
}

/**
 * @param {{ fix: object }} props
 */
export default function DiffViewer({ fix }) {
  const [editorError, setEditorError] = useState(false)

  if (!fix?.patch) return null

  const { original, modified, filename } = parsePatch(fix.patch)

  if (editorError) {
    // Fallback: plain <pre> for when Monaco fails to load
    return (
      <div className="helix-inner-card overflow-hidden">
        <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
          <span className="text-xs font-mono text-blue-300">{filename || 'patch'}</span>
        </div>
        <pre className="text-xs font-mono text-green-300 bg-black p-4 overflow-auto max-h-96 leading-relaxed whitespace-pre-wrap">
          {fix.patch}
        </pre>
      </div>
    )
  }

  return (
    <div className="helix-inner-card overflow-hidden">
      {filename && (
        <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
          <span className="text-[10px] text-helix-textMuted uppercase tracking-wider">File</span>
          <span className="text-xs font-mono text-blue-300 truncate">{filename}</span>
        </div>
      )}

      {/* Monaco diff editor */}
      <div className="h-[400px]">
        <DiffEditor
          height="400px"
          theme="vs-dark"
          language="python"
          original={original}
          modified={modified}
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 12,
            lineHeight: 18,
            fontFamily: 'JetBrains Mono, Fira Code, monospace',
            renderOverviewRuler: false,
            scrollbar: { vertical: 'auto', horizontal: 'auto' },
          }}
          onMount={() => setEditorError(false)}
          loading={
            <div className="h-full flex items-center justify-center bg-helix-bg text-helix-textMuted text-sm">
              Loading diff viewer…
            </div>
          }
        />
      </div>

      {/* Explanation */}
      {fix.explanation && (
        <div className="px-4 py-3 border-t border-white/[0.06]">
          <p className="text-xs font-semibold text-helix-textMuted uppercase tracking-wider mb-1">Explanation</p>
          <p className="text-sm text-helix-textPrimary leading-relaxed">{fix.explanation}</p>
        </div>
      )}
    </div>
  )
}
