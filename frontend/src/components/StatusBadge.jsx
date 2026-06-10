/**
 * src/components/StatusBadge.jsx
 * --------------------------------
 * Animated status pill component.
 * Displays the current Helix run status with appropriate colour,
 * icon, and animation for each state.
 */

import { motion } from 'framer-motion'
import { cn } from '../lib/utils'

// Respect prefers-reduced-motion
const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

const STATUS_CONFIG = {
  watching: {
    label: 'Watching',
    dot: true,
    dotClass: 'bg-helix-textMuted animate-pulse-slow',
    pillClass: 'bg-white/[0.06] text-helix-textMuted border-white/[0.08]',
  },
  diagnosing: {
    label: 'Diagnosing',
    spinner: true,
    pillClass: 'bg-blue-500/10 text-blue-300 border-blue-500/20',
  },
  fixing: {
    label: 'Fixing',
    spinner: true,
    pillClass: 'bg-helix-brand/10 text-red-300 border-helix-brand/25',
  },
  validating: {
    label: 'Validating',
    spinner: true,
    pillClass: 'bg-amber-500/10 text-helix-warning border-amber-500/20',
  },
  fixed: {
    label: 'Fixed',
    icon: '✓',
    pillClass: 'bg-green-500/10 text-helix-success border-green-500/20',
  },
  escalated: {
    label: 'Escalated',
    icon: '⚠',
    pillClass: 'bg-red-500/10 text-helix-error border-red-500/20',
  },
}

function Spinner({ className }) {
  if (prefersReduced) return <span className={cn('w-2.5 h-2.5 rounded-full bg-current', className)} />
  return (
    <svg
      className={cn('w-3 h-3 animate-spin', className)}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

/**
 * @param {{ status: string, className?: string }} props
 */
export default function StatusBadge({ status, className }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.watching

  return (
    <motion.span
      key={status}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: prefersReduced ? 0 : 0.2 }}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full',
        'text-xs font-medium border',
        config.pillClass,
        className,
      )}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      {/* Dot indicator */}
      {config.dot && (
        <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', config.dotClass)} />
      )}

      {/* Spinner */}
      {config.spinner && <Spinner />}

      {/* Static icon */}
      {config.icon && (
        <span className="text-xs leading-none" aria-hidden="true">{config.icon}</span>
      )}

      {config.label}
    </motion.span>
  )
}
