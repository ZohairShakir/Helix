/**
 * Floating bottom toolbar — zoom, fit view, canvas controls.
 */

import { Panel, useReactFlow, useViewport } from '@xyflow/react'
import { cn } from '../lib/utils'

function ToolbarButton({ onClick, label, children, active }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={cn(
        'w-9 h-9 flex items-center justify-center rounded-xl border transition-colors',
        'border-transparent text-helix-textMuted hover:text-helix-textPrimary hover:bg-white/[0.06]',
        active && 'bg-white/[0.08] text-helix-textPrimary border-white/[0.08]',
      )}
    >
      {children}
    </button>
  )
}

function IconZoomIn() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.35-4.35M11 8v6M8 11h6" strokeLinecap="round" />
    </svg>
  )
}

function IconZoomOut() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.35-4.35M8 11h6" strokeLinecap="round" />
    </svg>
  )
}

function IconFit() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconCenter() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" />
      <path d="M12 4v3M12 17v3M4 12h3M17 12h3" strokeLinecap="round" />
    </svg>
  )
}

export default function CanvasToolbar() {
  const { zoomIn, zoomOut, fitView, setViewport } = useReactFlow()
  const { zoom } = useViewport()
  const zoomPct = Math.round(zoom * 100)

  const handleReset = () => {
    setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 })
  }

  return (
    <Panel position="bottom-center" className="helix-canvas-toolbar-wrap">
      <div className="helix-canvas-toolbar" role="toolbar" aria-label="Canvas controls">
        <ToolbarButton label="Zoom out" onClick={() => zoomOut({ duration: 200 })}>
          <IconZoomOut />
        </ToolbarButton>

        <span className="helix-canvas-toolbar-zoom" aria-live="polite">
          {zoomPct}%
        </span>

        <ToolbarButton label="Zoom in" onClick={() => zoomIn({ duration: 200 })}>
          <IconZoomIn />
        </ToolbarButton>

        <span className="helix-canvas-toolbar-divider" aria-hidden="true" />

        <ToolbarButton
          label="Fit to view"
          onClick={() => fitView({ padding: 0.35, duration: 300 })}
        >
          <IconFit />
        </ToolbarButton>

        <ToolbarButton label="Reset view" onClick={handleReset}>
          <IconCenter />
        </ToolbarButton>
      </div>
    </Panel>
  )
}
