/**
 * n8n-style node canvas — zoom/pan, live execution path, animated edges.
 */

import { useCallback, useEffect, useMemo } from 'react'
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import PipelineNode from './PipelineNode'
import PipelineEdge from './PipelineEdge'
import HelixMiniMap from './HelixMiniMap'
import CanvasToolbar from './CanvasToolbar'
import { buildPipelineGraph } from '../lib/pipelineGraph'

const nodeTypes = { pipeline: PipelineNode }
const edgeTypes = { pipeline: PipelineEdge }

/**
 * @param {{ run: object, selectedNodeId: string|null, onSelectNode: Function }} props
 */
export default function PipelineCanvas({ run, selectedNodeId, onSelectNode }) {
  const graph = useMemo(
    () => buildPipelineGraph(run, selectedNodeId),
    [run, selectedNodeId],
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges)

  useEffect(() => {
    setNodes(graph.nodes)
    setEdges(graph.edges)
  }, [graph, setNodes, setEdges])

  const onNodeClick = useCallback(
    (_event, node) => {
      onSelectNode(selectedNodeId === node.id ? null : node.id)
    },
    [onSelectNode, selectedNodeId],
  )

  const onPaneClick = useCallback(() => {
    onSelectNode(null)
  }, [onSelectNode])

  return (
    <div className="helix-flow-canvas w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.35 }}
        minZoom={0.35}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        panOnScroll
        zoomOnScroll
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          size={1}
          color="rgba(255,255,255,0.07)"
        />
        <CanvasToolbar />
        <HelixMiniMap />
      </ReactFlow>
    </div>
  )
}
