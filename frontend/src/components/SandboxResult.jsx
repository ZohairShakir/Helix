/**
 * src/components/SandboxResult.jsx
 * ----------------------------------
 * Displays the Docker sandbox validation result for a Helix run.
 * Shows pass/fail header, exit code badge, terminal-style output,
 * and a retry message with attempt counter on failure.
 */

import { motion } from 'framer-motion'
import { cn } from '../lib/utils'

const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * @param {{ sandboxOutput: object, attempts: number, status: string }} props
 */
export default function SandboxResult({ sandboxOutput, attempts, status }) {
  if (!sandboxOutput) return null

  const { success, output, exit_code } = sandboxOutput
  const isRetrying = !success && status !== 'escalated' && status !== 'fixed'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: prefersReduced ? 0 : 0.3 }}
      className={cn(
        'helix-inner-card overflow-hidden',
        success
          ? 'border-green-500/20 bg-green-500/[0.04]'
          : 'border-red-500/20 bg-red-500/[0.04]',
      )}
    >
      {/* Header */}
      <div className={cn(
        'flex items-center justify-between px-4 py-3 border-b',
        success ? 'border-green-500/15' : 'border-red-500/15',
      )}>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'text-lg select-none',
              success ? 'text-helix-success' : 'text-helix-error',
            )}
            aria-hidden="true"
          >
            {success ? '✓' : '✕'}
          </span>
          <h3 className={cn(
            'text-sm font-semibold',
            success ? 'text-helix-success' : 'text-helix-error',
          )}>
            Sandbox {success ? 'Passed' : 'Failed'}
          </h3>
        </div>

        {/* Exit code badge */}
        <span
          className={cn(
            'text-xs font-mono px-2 py-0.5 rounded border',
            success
              ? 'text-helix-success border-green-700 bg-green-900/50'
              : 'text-helix-error border-red-700 bg-red-900/50',
          )}
          title="Exit code"
        >
          exit {exit_code ?? '—'}
        </span>
      </div>

      {/* Terminal output */}
      <div
        className={cn(
          'p-3 font-mono text-xs leading-relaxed overflow-auto max-h-56',
          'bg-black/40',
        )}
        role="log"
        aria-label="Sandbox output"
      >
        <pre className={cn(
          'whitespace-pre-wrap break-words',
          success ? 'text-green-400' : 'text-red-400',
        )}>
          {output?.trim() || '(no output)'}
        </pre>
      </div>

      {/* Retry indicator */}
      {!success && (
        <div className={cn(
          'px-4 py-2.5 border-t border-red-500/15',
          'flex items-center gap-2',
        )}>
          {isRetrying ? (
            <>
              {!prefersReduced && (
                <svg className="w-3.5 h-3.5 animate-spin text-helix-warning shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              )}
              <p className="text-xs text-helix-warning">
                Helix is retrying… <span className="font-semibold">(attempt {attempts})</span>
              </p>
            </>
          ) : (
            <p className="text-xs text-helix-error font-medium">
              All retry attempts exhausted — escalated to human review.
            </p>
          )}
        </div>
      )}
    </motion.div>
  )
}
