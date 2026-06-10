/**
 * src/components/DiagnosisCard.jsx
 * ----------------------------------
 * Displays the root-cause diagnosis for a Helix run.
 * Includes: failure type chip, root cause text, affected files,
 * a circular confidence score ring (Recharts), and collapsible agent findings.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts'
import { cn, failureTypeColor, failureTypeLabel } from '../lib/utils'

const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

// ---------------------------------------------------------------------------
// Confidence ring
// ---------------------------------------------------------------------------

function ConfidenceRing({ confidence }) {
  const pct = Math.round((confidence ?? 0) * 100)
  const color = pct >= 75 ? '#22C55E' : pct >= 50 ? '#F59E0B' : '#EF4444'

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-16 h-16">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="100%"
            startAngle={90}
            endAngle={-270}
            data={[{ value: pct, fill: color }]}
            barSize={6}
          >
            <RadialBar
              background={{ fill: 'rgba(255,255,255,0.06)' }}
              dataKey="value"
              cornerRadius={4}
              isAnimationActive={!prefersReduced}
            />
          </RadialBarChart>
        </ResponsiveContainer>
        {/* Centre label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-bold" style={{ color }}>{pct}%</span>
        </div>
      </div>
      <p className="text-[10px] text-helix-textMuted">Confidence</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Collapsible finding
// ---------------------------------------------------------------------------

function FindingAccordion({ finding }) {
  const [open, setOpen] = useState(false)
  const agentLabels = {
    log_agent:  'Log Analysis',
    diff_agent: 'Diff Analysis',
    dep_agent:  'Dependency Check',
  }

  return (
    <div className="border border-white/[0.06] rounded-xl overflow-hidden bg-white/[0.02]">
      <button
        className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-white/5 transition-colors"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        id={`finding-btn-${finding.agent_name}`}
        aria-controls={`finding-panel-${finding.agent_name}`}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-helix-textPrimary">
            {agentLabels[finding.agent_name] ?? finding.agent_name}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-helix-primary/20 text-helix-primary border border-helix-primary/30">
            {Math.round(finding.confidence * 100)}%
          </span>
        </div>
        <span
          className={cn('text-helix-textMuted text-xs transition-transform duration-200', open && 'rotate-180')}
          aria-hidden="true"
        >
          ▾
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={`finding-panel-${finding.agent_name}`}
            role="region"
            aria-labelledby={`finding-btn-${finding.agent_name}`}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: prefersReduced ? 0 : 0.2 }}
            className="overflow-hidden"
          >
            <pre className="px-3 pb-3 text-xs text-helix-textMuted font-mono whitespace-pre-wrap leading-relaxed border-t border-white/[0.06] pt-2">
              {finding.details}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main card
// ---------------------------------------------------------------------------

/**
 * @param {{ diagnosis: object }} props
 */
export default function DiagnosisCard({ diagnosis }) {
  if (!diagnosis) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: prefersReduced ? 0 : 0.3 }}
      className="helix-inner-card p-4 space-y-4"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <h3 className="text-sm font-semibold text-helix-textPrimary">Root Cause</h3>
            {diagnosis.failure_type && (
              <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full border', failureTypeColor(diagnosis.failure_type))}>
                {failureTypeLabel(diagnosis.failure_type)}
              </span>
            )}
          </div>
          <p className="text-sm text-helix-textMuted leading-relaxed">
            {diagnosis.root_cause ?? '—'}
          </p>
        </div>
        <ConfidenceRing confidence={diagnosis.confidence} />
      </div>

      {/* Affected files */}
      {diagnosis.affected_files?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-helix-textMuted uppercase tracking-wider mb-1.5">
            Affected Files
          </p>
          <ul className="space-y-1">
            {diagnosis.affected_files.map((f, i) => (
              <li key={i} className="text-xs font-mono text-blue-300 bg-blue-950/50 px-2 py-0.5 rounded border border-blue-900/50 truncate">
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Agent findings (collapsible) */}
      {diagnosis.findings?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-helix-textMuted uppercase tracking-wider mb-2">
            Specialist Findings
          </p>
          <div className="space-y-2">
            {diagnosis.findings.map((finding, i) => (
              <FindingAccordion key={i} finding={finding} />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
