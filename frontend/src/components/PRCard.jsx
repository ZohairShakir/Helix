/**
 * src/components/PRCard.jsx
 * --------------------------
 * Displays information about the GitHub Pull Request opened by Helix.
 * Green success card with PR title, number, repo/branch info, and a link button.
 */

import { motion } from 'framer-motion'
import { formatTimeAgo } from '../lib/utils'

const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * @param {{ prUrl: string, run: object }} props
 */
export default function PRCard({ prUrl, run }) {
  if (!prUrl) return null

  const ctx = run?.failure_context ?? {}

  // Extract PR number from URL (e.g. https://github.com/org/repo/pull/42)
  const prNumber = prUrl.match(/\/pull\/(\d+)/)?.[1] ?? '—'
  const prTitle = `[Helix] Automated fix for run ${run?.run_id?.slice(0, 8) ?? '...'}`

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: prefersReduced ? 0 : 0.35, ease: 'easeOut' }}
      className="helix-inner-card border-green-500/25 bg-green-500/[0.05] overflow-hidden"
      role="region"
      aria-label="Pull request opened"
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-green-500/15">
        <div
          className="w-8 h-8 rounded-full bg-green-900 border border-green-700 flex items-center justify-center shrink-0"
          aria-hidden="true"
        >
          <svg
            viewBox="0 0 24 24"
            className="w-4 h-4 text-helix-success"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="18" cy="18" r="3" />
            <circle cx="6"  cy="6"  r="3" />
            <path d="M13 6h3a2 2 0 0 1 2 2v7" />
            <line x1="6" y1="9" x2="6" y2="21" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-helix-success">Pull Request Opened</p>
          <p className="text-xs text-green-400/70 mt-0.5">Helix has proposed a fix</p>
        </div>
        <span className="text-xs font-mono text-green-500 bg-green-900/60 border border-green-700 px-2 py-0.5 rounded-full shrink-0">
          #{prNumber}
        </span>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-3">
        {/* PR title */}
        <p className="text-sm text-helix-textPrimary font-medium leading-snug">
          {prTitle}
        </p>

        {/* Meta row */}
        <div className="flex flex-wrap gap-3 text-xs text-helix-textMuted">
          <span>
            <span className="text-helix-textMuted/60">Repo: </span>
            <span className="font-mono text-blue-300">{ctx.repo ?? '—'}</span>
          </span>
          <span>
            <span className="text-helix-textMuted/60">Branch: </span>
            <span className="font-mono text-helix-brand/90">{ctx.branch ?? '—'}</span>
          </span>
          <span>
            <span className="text-helix-textMuted/60">Opened: </span>
            {formatTimeAgo(run?.started_at)}
          </span>
        </div>

        {/* CTA Button */}
        <a
          id={`view-pr-${run?.run_id}`}
          href={prUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
            bg-helix-success text-white text-sm font-semibold
            hover:bg-green-400 active:scale-95
            transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-helix-success"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
          View Pull Request
        </a>
      </div>
    </motion.div>
  )
}
