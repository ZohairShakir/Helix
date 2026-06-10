/**
 * Styled overview minimap — glass panel, status colors, legend.
 */

import { MiniMap, Panel } from '@xyflow/react'

function nodeColor(node) {
  const status = node.data?.status
  if (status === 'running') return '#E61919'
  if (status === 'done') return '#22C55E'
  if (status === 'failed') return '#DC2626'
  if (node.data?.selected) return '#9CA3AF'
  return '#27272a'
}

function nodeStrokeColor(node) {
  if (node.data?.selected) return '#E61919'
  if (node.data?.status === 'running') return '#FCA5A5'
  return 'rgba(255, 255, 255, 0.12)'
}

function MiniMapNode({ x, y, width, height, color, strokeColor, strokeWidth, selected, id }) {
  const isRunning = id && color === '#E61919'

  return (
    <rect
      x={x}
      y={y}
      width={width}
      height={height}
      rx={5}
      ry={5}
      fill={color}
      stroke={strokeColor}
      strokeWidth={strokeWidth}
      className={isRunning ? 'helix-minimap-node-running' : undefined}
      opacity={selected ? 1 : 0.95}
    />
  )
}

const LEGEND = [
  { color: '#27272a', label: 'Pending' },
  { color: '#E61919', label: 'Running' },
  { color: '#22C55E', label: 'Done' },
  { color: '#DC2626', label: 'Failed' },
]

export default function HelixMiniMap() {
  return (
    <Panel position="bottom-right" className="helix-minimap-wrap">
      <div className="helix-minimap-header">
        <span className="helix-minimap-title">Overview</span>
        <span className="helix-minimap-hint">drag · scroll</span>
      </div>

      <MiniMap
        className="helix-minimap"
        nodeColor={nodeColor}
        nodeStrokeColor={nodeStrokeColor}
        nodeStrokeWidth={2}
        nodeBorderRadius={5}
        nodeComponent={MiniMapNode}
        maskColor="rgba(10, 10, 12, 0.72)"
        maskStrokeColor="rgba(230, 25, 25, 0.55)"
        maskStrokeWidth={1.5}
        pannable
        zoomable
        ariaLabel="Pipeline overview minimap"
      />

      <div className="helix-minimap-legend" aria-hidden="true">
        {LEGEND.map(({ color, label }) => (
          <span key={label} className="helix-minimap-legend-item">
            <span className="helix-minimap-legend-dot" style={{ backgroundColor: color }} />
            {label}
          </span>
        ))}
      </div>
    </Panel>
  )
}
