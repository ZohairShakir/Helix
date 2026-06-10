/**
 * Custom React Flow node — larger cards, swarm agents, confidence, PR highlight.
 */

import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../lib/utils'

const STATUS_STYLES = {
  pending: {
    border: 'border-white/10',
    bg: 'bg-[#1a1a1c]',
    glow: '',
  },
  running: {
    border: 'border-helix-brand/60',
    bg: 'bg-helix-brand/10',
    glow: 'shadow-[0_0_28px_rgba(230,25,25,0.3)]',
  },
  done: {
    border: 'border-helix-success/50',
    bg: 'bg-green-500/5',
    glow: '',
  },
  failed: {
    border: 'border-helix-error/50',
    bg: 'bg-red-500/10',
    glow: '',
  },
}

const CONFIDENCE_STYLES = {
  high: 'bg-green-500/15 text-green-300 border-green-500/30',
  medium: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  low: 'bg-red-500/15 text-red-300 border-red-500/30',
}

function StatusIcon({ status, large }) {
  const size = large ? 'w-4 h-4' : 'w-3.5 h-3.5'

  if (status === 'running') {
    return (
      <svg className={cn(size, 'animate-spin text-red-300')} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    )
  }
  if (status === 'done') return <span className="text-helix-success text-sm font-bold">✓</span>
  if (status === 'failed') return <span className="text-helix-error text-sm font-bold">✕</span>
  return <span className="w-2.5 h-2.5 rounded-full bg-white/20" />
}

function AgentRow({ label, status }) {
  return (
    <div className="flex items-center justify-between gap-2 py-0.5">
      <span className="text-[11px] text-helix-textMuted truncate">{label}</span>
      <StatusIcon status={status} />
    </div>
  )
}

function PipelineNode({ data }) {
  const {
    label,
    status,
    summary,
    selected,
    expanded,
    variant,
    confidence,
    prNumber,
    swarmAgents,
    validateAgents,
  } = data

  const isSuccessNode = variant === 'success'
  const styles = isSuccessNode && status === 'done'
    ? {
        border: 'border-green-400/60',
        bg: 'bg-green-500/10',
        glow: 'shadow-[0_0_32px_rgba(34,197,94,0.35)]',
      }
    : (STATUS_STYLES[status] ?? STATUS_STYLES.pending)

  const showSwarm = swarmAgents?.length && (expanded || status === 'running' || status === 'done')
  const showValidateAgents = validateAgents?.length && (expanded || status === 'running' || status !== 'pending')

  return (
    <>
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-white/30 !border-0" />

      <motion.div
        layout
        className={cn(
          'w-[260px] rounded-2xl border backdrop-blur-md transition-shadow duration-300',
          styles.border,
          styles.bg,
          styles.glow,
          selected && 'ring-2 ring-helix-brand/50',
          status === 'running' && 'animate-glow-pulse',
          isSuccessNode && status === 'done' && 'helix-node-pr-success',
        )}
      >
        <div className="px-4 py-4">
          <div className="flex items-start gap-3">
            <div className={cn(
              'w-9 h-9 rounded-xl border flex items-center justify-center shrink-0',
              styles.border,
              styles.bg,
              isSuccessNode && status === 'done' && 'border-green-400/50 bg-green-500/15',
            )}>
              <StatusIcon status={status} large />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <p className={cn(
                  'font-semibold text-helix-textPrimary leading-tight',
                  isSuccessNode && status === 'done' ? 'text-sm text-green-300' : 'text-sm',
                )}>
                  {isSuccessNode && status === 'done' ? 'Pull request opened' : label}
                </p>
                {confidence && status !== 'pending' && (
                  <span className={cn(
                    'text-[10px] font-bold px-1.5 py-0.5 rounded-md border tabular-nums',
                    CONFIDENCE_STYLES[confidence.tier],
                  )}>
                    {confidence.pct}%
                  </span>
                )}
              </div>

              {isSuccessNode && status === 'done' && prNumber && (
                <p className="text-xs font-mono text-green-400/90 mt-1">#{prNumber}</p>
              )}

              {!isSuccessNode && (
                <p className="text-[11px] text-helix-textMuted capitalize mt-1">{status}</p>
              )}
            </div>

            {(summary || showSwarm || showValidateAgents) && (
              <span className="text-helix-textMuted text-[10px] mt-1" aria-hidden="true">
                {expanded ? '▴' : '▾'}
              </span>
            )}
          </div>

          <AnimatePresence initial={false}>
            {showSwarm && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-3 pt-3 border-t border-white/[0.06] space-y-0.5"
              >
                {swarmAgents.map((a) => (
                  <AgentRow key={a.id} label={a.label} status={a.status} />
                ))}
              </motion.div>
            )}

            {showValidateAgents && !showSwarm && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-3 pt-3 border-t border-white/[0.06] space-y-0.5"
              >
                {validateAgents.map((a) => (
                  <AgentRow key={a.id} label={a.label} status={a.status} />
                ))}
              </motion.div>
            )}

            {(expanded || status === 'running') && summary && !showSwarm && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="text-xs text-helix-textMuted mt-3 leading-relaxed border-t border-white/[0.06] pt-2 line-clamp-3"
              >
                {summary}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-white/30 !border-0" />
      <Handle type="source" position={Position.Bottom} id="bottom" className="!w-2.5 !h-2.5 !bg-white/30 !border-0" />
      <Handle type="source" position={Position.Top} id="top" className="!w-2.5 !h-2.5 !bg-white/30 !border-0" />
      <Handle type="target" position={Position.Top} id="top" className="!w-2.5 !h-2.5 !bg-white/30 !border-0" />
      <Handle type="target" position={Position.Bottom} id="bottom" className="!w-2.5 !h-2.5 !bg-white/30 !border-0" />
    </>
  )
}

export default memo(PipelineNode)
