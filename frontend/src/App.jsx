/**
 * src/App.jsx
 * ------------
 * Full-viewport pipeline canvas with a compact floating run picker (top-right).
 */

import { useMemo, useState } from 'react'
import { useHelixSocket } from './hooks/useHelixSocket'
import RunFeed from './components/RunFeed'
import RunDetail from './components/RunDetail'
import HelixLogo from './components/HelixLogo'
import { cn } from './lib/utils'

const ACTIVE_STATUSES = new Set(['watching', 'diagnosing', 'fixing', 'validating'])

function ActiveRunsBadge({ runs }) {
  const count = useMemo(
    () => Array.from(runs.values()).filter((r) => ACTIVE_STATUSES.has(r.status)).length,
    [runs],
  )

  if (count === 0) return null

  return (
    <span
      className="helix-pill text-helix-brand border-helix-brand/30 bg-helix-brand/10 animate-pulse-slow"
      role="status"
      aria-label={`${count} active run${count === 1 ? '' : 's'}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-helix-brand animate-pulse" />
      {count} active
    </span>
  )
}

function ConnectionPill({ connected }) {
  return (
    <div
      className="helix-pill"
      role="status"
      aria-label={connected ? 'Connected to Helix backend' : 'Disconnected from Helix backend'}
    >
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          connected ? 'bg-helix-success animate-pulse-slow' : 'bg-helix-brand',
        )}
      />
      {connected ? 'Live' : 'Offline'}
    </div>
  )
}

export default function App() {
  const { runs, connected, selectedRunId, setSelectedRunId } = useHelixSocket()
  const [inspectorOpen, setInspectorOpen] = useState(false)

  const selectedRun = selectedRunId ? runs.get(selectedRunId) ?? null : null

  return (
    <div className="relative h-screen helix-canvas overflow-hidden">
      {/* Top bar — logo left only */}
      <header
        className="absolute top-0 left-0 z-30 flex items-center gap-3 px-6 py-4 pointer-events-none"
        role="banner"
      >
        <HelixLogo size="sm" alt="" className="pointer-events-auto" />
        <h1 className="text-sm font-medium text-helix-textPrimary tracking-tight pointer-events-auto">
          Helix Autonomous CI/CD Agent
        </h1>
      </header>

      {/* Status pills — top right, above run picker */}
      <div className="absolute top-4 right-6 z-30 flex items-center gap-2 pointer-events-none">
        <div className="pointer-events-auto flex items-center gap-2">
          <ActiveRunsBadge runs={runs} />
          <ConnectionPill connected={connected} />
        </div>
      </div>

      {/* Floating glass run picker */}
      <div className="absolute top-[4.25rem] right-6 z-30 w-[min(100vw-3rem,320px)] pointer-events-none">
        <div className="pointer-events-auto">
          <RunFeed
            runs={runs}
            selectedRunId={selectedRunId}
            setSelectedRunId={setSelectedRunId}
            selectedRun={selectedRun}
            collapseForInspector={inspectorOpen}
          />
        </div>
      </div>

      {/* Full-viewport pipeline canvas */}
      <main className="absolute inset-0 z-10" aria-label="Pipeline canvas">
        <RunDetail run={selectedRun} onInspectorOpenChange={setInspectorOpen} />
      </main>
    </div>
  )
}
