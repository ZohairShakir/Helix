/**
 * Run detail — full-viewport pipeline canvas + left inspector stack.
 */

import { useState, useEffect } from 'react'
import { formatTimeAgo } from '../lib/utils'
import StatusBadge from './StatusBadge'
import PipelineCanvas from './PipelineCanvas'
import NodeDetailDrawer from './NodeDetailDrawer'

function EmptyDetail() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-12">
      <div>
        <h2 className="text-base font-medium text-helix-textPrimary">No run selected</h2>
        <p className="text-sm text-helix-textMuted mt-2 max-w-sm leading-relaxed">
          Pick a pipeline run from the panel top-right, or wait for a CI failure.
        </p>
      </div>
    </div>
  )
}

export default function RunDetail({ run, onInspectorOpenChange }) {
  const [selectedNodeId, setSelectedNodeId] = useState(null)

  useEffect(() => {
    setSelectedNodeId(null)
  }, [run?.run_id])

  useEffect(() => {
    onInspectorOpenChange?.(!!selectedNodeId)
  }, [selectedNodeId, onInspectorOpenChange])

  if (!run) return <EmptyDetail />

  const ctx = run.failure_context ?? {}
  const shortSha = ctx.commit_sha ? ctx.commit_sha.slice(0, 8) : '—'

  return (
    <div className="relative h-full w-full" role="main">
      <div
        className="absolute top-[4.25rem] left-6 z-[25] flex flex-col gap-3 w-[min(calc(100vw-22rem),400px)] max-h-[calc(100vh-5.5rem)] pointer-events-none"
      >
        <div className="helix-float-panel px-4 py-3 shrink-0 pointer-events-auto">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-sm font-semibold text-helix-textPrimary font-mono truncate">
              {ctx.repo ?? '—'}
            </h2>
            <StatusBadge status={run.status} />
          </div>
          <p className="text-[11px] text-helix-textMuted font-mono mt-1">
            {ctx.branch ?? '—'} · {shortSha} · {formatTimeAgo(run.started_at)}
          </p>
        </div>

        <div className="pointer-events-auto min-h-0 flex flex-col">
          <NodeDetailDrawer
            run={run}
            nodeId={selectedNodeId}
            onClose={() => setSelectedNodeId(null)}
          />
        </div>
      </div>

      <div className="absolute inset-0 z-10">
        <PipelineCanvas
          run={run}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
        />
      </div>
    </div>
  )
}
