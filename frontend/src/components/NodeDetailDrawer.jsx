/**
 * Expandable inspector — stacks below run context on the left (avoids run picker overlap).
 */

import { motion, AnimatePresence } from 'framer-motion'
import { NODE_LABELS } from '../lib/pipelineGraph'
import { cn, failureTypeColor, failureTypeLabel, formatTimestamp } from '../lib/utils'
import DiagnosisCard from './DiagnosisCard'
import DiffViewer from './DiffViewer'
import SandboxResult from './SandboxResult'
import PRCard from './PRCard'

function DrawerSection({ title, children }) {
  return (
    <div className="space-y-2">
      <h4 className="helix-section-label">{title}</h4>
      {children}
    </div>
  )
}

/**
 * @param {{ run: object, nodeId: string|null, onClose: Function }} props
 */
export default function NodeDetailDrawer({ run, nodeId, onClose }) {
  const ctx = run?.failure_context ?? {}
  const states = run?.trace?.filter((t) => t.node_name === nodeId) ?? []
  const latest = states[states.length - 1]

  return (
    <AnimatePresence>
      {nodeId && (
        <motion.aside
          initial={{ opacity: 0, y: -8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, y: -8, height: 0 }}
          transition={{ duration: 0.2 }}
          className="helix-float-panel flex flex-col min-h-0 max-h-[min(58vh,520px)] overflow-hidden"
          aria-label={`Details for ${NODE_LABELS[nodeId] ?? nodeId}`}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] shrink-0">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-helix-textPrimary truncate">
                {NODE_LABELS[nodeId] ?? nodeId}
              </p>
              {latest && (
                <p className="text-[10px] text-helix-textMuted font-mono mt-0.5">
                  {formatTimestamp(latest.timestamp)}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="w-8 h-8 rounded-lg border border-white/[0.08] text-helix-textMuted hover:text-helix-textPrimary hover:bg-white/[0.05] transition-colors shrink-0"
              aria-label="Close node details"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-5 min-h-0">
            {latest?.summary && (
              <DrawerSection title="Execution log">
                <p className="text-sm text-helix-textMuted leading-relaxed helix-inner-card p-3">
                  {latest.summary}
                </p>
              </DrawerSection>
            )}

            {nodeId === 'assemble_context' && (
              <DrawerSection title="Failure context">
                <div className="helix-inner-card p-3 space-y-2 text-sm">
                  <p><span className="text-helix-textMuted">Repo </span>{ctx.repo ?? '—'}</p>
                  <p><span className="text-helix-textMuted">Workflow </span>{ctx.workflow_name ?? '—'}</p>
                  <p><span className="text-helix-textMuted">Branch </span>{ctx.branch ?? '—'}</p>
                  {ctx.logs && (
                    <pre className="text-[10px] font-mono text-helix-textMuted mt-2 max-h-40 overflow-auto whitespace-pre-wrap">
                      {ctx.logs.slice(-1500)}
                    </pre>
                  )}
                </div>
              </DrawerSection>
            )}

            {nodeId === 'run_specialists' && (
              <DrawerSection title="Analysis swarm">
                <div className="helix-inner-card p-3 space-y-2">
                  {(run?.diagnosis?.findings ?? []).length > 0 ? (
                    run.diagnosis.findings.map((f, i) => {
                      const labels = {
                        log_agent: 'Log Agent',
                        diff_agent: 'Workflow Agent',
                        dep_agent: 'Dependency Agent',
                      }
                      return (
                        <div key={i} className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-helix-textPrimary">
                              {labels[f.agent_name] ?? f.agent_name}
                              <span className="text-helix-textMuted font-normal ml-1.5">
                                {Math.round((f.confidence ?? 0) * 100)}%
                              </span>
                            </p>
                            <pre className="text-[11px] text-helix-textMuted mt-1 whitespace-pre-wrap font-mono line-clamp-4">
                              {f.details}
                            </pre>
                          </div>
                          <span className={cn(
                            'text-sm shrink-0',
                            f.confidence >= 0.2 ? 'text-helix-success' : 'text-helix-error',
                          )}>
                            {f.confidence >= 0.2 ? '✓' : '✕'}
                          </span>
                        </div>
                      )
                    })
                  ) : (
                    <p className="text-xs text-helix-textMuted">Agents running in parallel…</p>
                  )}
                </div>
              </DrawerSection>
            )}

            {nodeId === 'diagnose' && run?.diagnosis && (
              <DrawerSection title="Diagnosis">
                <DiagnosisCard diagnosis={run.diagnosis} />
              </DrawerSection>
            )}

            {nodeId === 'generate_fix' && run?.fix?.patch && (
              <DrawerSection title="Proposed fix">
                <DiffViewer fix={run.fix} />
              </DrawerSection>
            )}

            {nodeId === 'validate' && (
              <DrawerSection title="Validation agents">
                <div className="helix-inner-card p-3 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Docker Agent</span>
                    <span className={run?.sandbox_output?.success != null ? 'text-helix-success' : 'text-helix-textMuted'}>
                      {run?.sandbox_output ? '✓' : run?.trace?.some(t => t.node_name === 'validate' && t.status === 'running') ? '…' : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Test Agent</span>
                    <span className={run?.sandbox_output?.success ? 'text-helix-success' : run?.sandbox_output ? 'text-helix-error' : 'text-helix-textMuted'}>
                      {run?.sandbox_output?.success ? '✓' : run?.sandbox_output ? '✕' : '—'}
                    </span>
                  </div>
                </div>
              </DrawerSection>
            )}

            {nodeId === 'validate' && run?.sandbox_output && (
              <DrawerSection title="Sandbox">
                <SandboxResult
                  sandboxOutput={run.sandbox_output}
                  attempts={run.attempts}
                  status={run.status}
                />
              </DrawerSection>
            )}

            {nodeId === 'open_pr' && run?.pr_url && (
              <DrawerSection title="Pull request">
                <PRCard prUrl={run.pr_url} run={run} />
              </DrawerSection>
            )}

            {nodeId === 'retry_or_escalate' && (
              <DrawerSection title="Retry status">
                <div className={cn(
                  'helix-inner-card p-3 text-sm',
                  run?.status === 'escalated' ? 'text-red-300' : 'text-amber-300',
                )}>
                  {run?.status === 'escalated'
                    ? 'All retry attempts exhausted — escalated to human review.'
                    : `Attempt ${run?.attempts ?? 0} — Helix is retrying with a new fix strategy.`}
                </div>
              </DrawerSection>
            )}

            {nodeId === 'triage' && run?.diagnosis?.failure_type && (
              <DrawerSection title="Triage result">
                <span className={cn(
                  'text-xs font-medium px-2 py-1 rounded-full border inline-block',
                  failureTypeColor(run.diagnosis.failure_type),
                )}>
                  {failureTypeLabel(run.diagnosis.failure_type)}
                </span>
              </DrawerSection>
            )}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
