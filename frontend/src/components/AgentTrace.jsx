/**
 * src/components/AgentTrace.jsx
 * ------------------------------
 * Vertical timeline showing each TraceStep in a Helix run.
 * Steps slide in from below as they arrive.
 * Icons and colours reflect step status (running / done / failed).
 */

import { AnimatePresence, motion } from 'framer-motion'
import { cn, formatTimestamp } from '../lib/utils'

const NODE_LABELS = {
  assemble_context:  'Gathering context',
  triage:            'Triaging failure',
  run_specialists:   'Analysis swarm',
  diagnose:          'Diagnosing root cause',
  generate_fix:      'Generating fix',
  validate:          'Validating in sandbox',
  open_pr:           'Opening pull request',
  retry_or_escalate: 'Retrying…',
}

const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function StepIcon({ status }) {
  const base = 'w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-xs font-bold border-2'

  if (status === 'running') {
    return (
      <span className={cn(base, 'border-helix-brand/50 bg-helix-brand/10 text-red-300')}>
        {prefersReduced ? '…' : (
          <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
        )}
      </span>
    )
  }
  if (status === 'done') {
    return (
      <span className={cn(base, 'border-helix-success bg-green-950 text-helix-success')}>
        ✓
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span className={cn(base, 'border-helix-error bg-red-950 text-helix-error')}>
        ✕
      </span>
    )
  }
  return <span className={cn(base, 'border-white/10 bg-white/[0.04] text-helix-textMuted')}>?</span>
}

/**
 * @param {{ trace: Array<object> }} props
 */
export default function AgentTrace({ trace }) {
  if (!trace || trace.length === 0) {
    return (
      <p className="text-xs text-helix-textMuted italic px-1">No trace steps yet.</p>
    )
  }

  return (
    <ol className="relative space-y-0" aria-label="Agent execution timeline">
      <AnimatePresence initial={false}>
        {trace.map((step, idx) => (
          <motion.li
            key={`${step.node_name}-${idx}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: prefersReduced ? 0 : 0.3, ease: 'easeOut' }}
            className="relative flex gap-3 pb-5 last:pb-0"
          >
            {/* Connector line */}
            {idx < trace.length - 1 && (
              <div
                className="absolute left-3 top-6 bottom-0 w-px bg-white/[0.08]"
                aria-hidden="true"
              />
            )}

            {/* Icon */}
            <StepIcon status={step.status} />

            {/* Content */}
            <div className="flex-1 min-w-0 pt-0.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-helix-textPrimary truncate">
                  {NODE_LABELS[step.node_name] ?? step.node_name}
                </p>
                <time
                  className="text-[10px] text-helix-textMuted font-mono shrink-0"
                  dateTime={step.timestamp}
                  aria-label={`At ${formatTimestamp(step.timestamp)}`}
                >
                  {formatTimestamp(step.timestamp)}
                </time>
              </div>
              <p className="text-xs text-helix-textMuted mt-0.5 leading-relaxed">
                {step.summary}
              </p>
            </div>
          </motion.li>
        ))}
      </AnimatePresence>
    </ol>
  )
}
