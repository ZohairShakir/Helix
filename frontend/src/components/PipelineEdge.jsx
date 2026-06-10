/**
 * Animated pipeline edge — glows while execution flows through.
 */

import { BaseEdge, getSmoothStepPath } from '@xyflow/react'

export default function PipelineEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}) {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  })

  const active = data?.active
  const completed = data?.completed && !active

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          opacity: completed ? 0.85 : 0.7,
        }}
      />
      {active && (
        <path
          d={edgePath}
          fill="none"
          stroke="#E61919"
          strokeWidth={4}
          strokeOpacity={0.35}
          className="helix-edge-glow"
        />
      )}
      {active && (
        <path
          d={edgePath}
          fill="none"
          stroke="#FCA5A5"
          strokeWidth={2}
          strokeDasharray="8 6"
          className="helix-edge-flow"
        />
      )}
    </>
  )
}
