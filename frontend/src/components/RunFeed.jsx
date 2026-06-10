/**
 * src/components/RunFeed.jsx
 * ---------------------------
 * Compact floating glass run picker — top-right, collapsible.
 */

import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import RunCard from './RunCard'
import HelixLogo from './HelixLogo'
import { cn, truncateRepo } from '../lib/utils'
import StatusBadge from './StatusBadge'

export default function RunFeed({ runs, selectedRunId, setSelectedRunId, selectedRun, collapseForInspector = false }) {
  const [open, setOpen] = useState(true)

  useEffect(() => {
    if (collapseForInspector) setOpen(false)
  }, [collapseForInspector])

  const sorted = Array.from(runs.values()).sort(
    (a, b) => new Date(b.started_at) - new Date(a.started_at),
  )

  const ctx = selectedRun?.failure_context ?? {}
  const selectedLabel = selectedRun
    ? truncateRepo(ctx.repo ?? 'Unknown', 22)
    : 'No run selected'

  return (
    <div className="helix-float-panel flex flex-col overflow-hidden" aria-label="Helix run feed">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2.5 w-full px-4 py-3 text-left hover:bg-white/[0.03] transition-colors"
        aria-expanded={open}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold text-helix-textPrimary">Pipeline runs</h2>
            {sorted.length > 0 && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-white/[0.06] text-helix-textMuted border border-white/[0.08]">
                {sorted.length}
              </span>
            )}
          </div>
          {!open && selectedRun && (
            <p className="text-[11px] text-helix-textMuted font-mono truncate mt-0.5">
              {selectedLabel}
            </p>
          )}
        </div>
        {selectedRun && !open && (
          <StatusBadge status={selectedRun.status} className="shrink-0 scale-90" />
        )}
        <span className={cn('text-helix-textMuted text-xs transition-transform', open && 'rotate-180')}>
          ▾
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-white/[0.06]"
          >
            <div
              className="max-h-[min(42vh,320px)] overflow-y-auto px-3 py-3 space-y-2"
              role="list"
              aria-label="CI/CD run list"
            >
              <AnimatePresence initial={false}>
                {sorted.length === 0 ? (
                  <EmptyState />
                ) : (
                  sorted.map((run) => (
                    <div key={run.run_id} role="listitem">
                      <RunCard
                        run={run}
                        isSelected={run.run_id === selectedRunId}
                        onClick={() => setSelectedRunId(run.run_id)}
                        compact
                      />
                    </div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function EmptyState() {
  return (
    <motion.div
      key="empty"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center py-8 gap-3 text-center px-3"
      role="status"
      aria-label="No runs yet"
    >
      <HelixLogo size="md" className="opacity-70" />
      <p className="text-xs font-medium text-helix-textPrimary">Waiting for failures</p>
      <p className="text-[11px] text-helix-textMuted leading-relaxed">
        Runs appear when GitHub Actions pipelines fail.
      </p>
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-helix-brand/50"
            animate={{ scale: [1, 1.4, 1], opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.3 }}
          />
        ))}
      </div>
    </motion.div>
  )
}
