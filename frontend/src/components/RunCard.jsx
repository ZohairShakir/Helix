/**
 * src/components/RunCard.jsx
 * ---------------------------
 * Single run summary card for the floating run feed panel.
 */

import { motion } from 'framer-motion'
import { cn, failureTypeColor, failureTypeLabel, formatTimeAgo, truncateRepo } from '../lib/utils'
import StatusBadge from './StatusBadge'

const ACTIVE_STATUSES = new Set(['watching', 'diagnosing', 'fixing', 'validating'])

export default function RunCard({ run, isSelected, onClick, compact = false }) {
  const isActive = ACTIVE_STATUSES.has(run.status)
  const ctx = run.failure_context ?? {}
  const repoName = truncateRepo(ctx.repo ?? '—', 28)
  const branch = ctx.branch ? `/${ctx.branch}` : ''
  const failureType = run.diagnosis?.failure_type

  return (
    <motion.button
      id={`run-card-${run.run_id}`}
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className={cn(
        'w-full text-left rounded-xl border transition-all duration-200',
        compact ? 'px-3 py-2.5' : 'px-4 py-3 rounded-2xl',
        'bg-white/[0.03] focus:outline-none focus-visible:ring-2 focus-visible:ring-helix-primary/60',
        'border-white/[0.06]',
        isSelected
          ? 'border-helix-primary/40 bg-helix-primary/[0.08] shadow-helix-glow'
          : 'hover:bg-white/[0.05] hover:border-white/[0.1]',
        isActive && !isSelected && 'animate-glow-pulse',
      )}
      aria-pressed={isSelected}
      aria-label={`Run for ${ctx.repo ?? 'unknown'} — ${run.status}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-helix-textPrimary truncate font-mono">
            {repoName}
            <span className="text-helix-textMuted font-sans font-normal">{branch}</span>
          </p>
          <p className="text-xs text-helix-textMuted truncate mt-1">
            {ctx.workflow_name ?? 'Unknown workflow'}
          </p>
        </div>
        <StatusBadge status={run.status} className="shrink-0" />
      </div>

      <div className="flex items-center justify-between mt-2.5 gap-2">
        {failureType && (
          <span
            className={cn(
              'text-[10px] font-medium px-1.5 py-0.5 rounded-md border',
              failureTypeColor(failureType),
            )}
          >
            {failureTypeLabel(failureType)}
          </span>
        )}
        <span className="text-[11px] text-helix-textMuted ml-auto">
          {formatTimeAgo(run.started_at)}
        </span>
      </div>
    </motion.button>
  )
}
