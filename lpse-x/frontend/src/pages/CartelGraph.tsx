import React, { useState, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ForceGraph2D } from 'react-force-graph'
import { getGraphCommunities } from '../api/client'
import type { GraphCommunity } from '../types/models'

const COMMUNITY_COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#06b6d4', '#22c55e']

// Build force-graph data structure from communities
function buildGraphData(communities: GraphCommunity[]): {
  nodes: Array<{ id: string; communityId: number | string; color: string; size: number }>
  links: Array<{ source: string; target: string; weight: number; color: string }>
} {
  const nodes: Array<{ id: string; communityId: number | string; color: string; size: number }> = []
  const links: Array<{ source: string; target: string; weight: number; color: string }> = []
  const nodeSet = new Set<string>()

  for (const [ci, community] of communities.entries()) {
    const color = COMMUNITY_COLORS[ci % COMMUNITY_COLORS.length]
    for (const member of community.members) {
      if (!nodeSet.has(member)) {
        nodeSet.add(member)
        nodes.push({ id: member, communityId: community.community_id, color, size: 6 })
      }
    }
    if (community.edge_weights && Object.keys(community.edge_weights).length > 0) {
      for (const [edgeKey, weight] of Object.entries(community.edge_weights)) {
        const parts = edgeKey.split('|')
        if (parts.length === 2 && parts[0] && parts[1]) {
          links.push({ source: parts[0], target: parts[1], weight, color })
        }
      }
    } else {
      // Synthetic edges from member pairs when no edge_weights provided
      const w = community.members.length > 1 ? 1.0 / community.members.length : 1.0
      for (let i = 0; i < community.members.length; i++) {
        for (let j = i + 1; j < community.members.length; j++) {
          links.push({ source: community.members[i], target: community.members[j], weight: w, color })
        }
      }
    }
  }

  return { nodes, links }
}

// ============================================================================
// Risk score badge
// ============================================================================

function RiskScoreBar({ score }: { score: number }): React.ReactElement {
  const pct = Math.round(score * 100)
  const color = score >= 0.7 ? 'bg-red-500' : score >= 0.4 ? 'bg-amber-400' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-600 w-8 text-right">{pct}%</span>
    </div>
  )
}

// ============================================================================
// Main CartelGraph page
// ============================================================================

export function CartelGraph(): React.ReactElement {
  const [selectedCommunity, setSelectedCommunity] = useState<GraphCommunity | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const graphRef = useRef(undefined)

  const graphQuery = useQuery({
    queryKey: ['graph-communities'],
    queryFn: () => getGraphCommunities(2, 20),
    staleTime: 300_000,
    retry: 1,
  })

  const communities: GraphCommunity[] = graphQuery.data?.communities ?? []

  const graphData = buildGraphData(communities)

  const handleNodeClick = useCallback(
    (node: { id?: string | number }) => {
      const nodeId = String(node.id ?? '')
      setSelectedNode(nodeId)
      // Find which community this node belongs to
      const comm = communities.find((c) => c.members.includes(nodeId))
      setSelectedCommunity(comm ?? null)
    },
    [communities],
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Jaringan Kartel Vendor</h1>
          <p className="text-sm text-slate-500 mt-1">
            Deteksi komunitas bid-rigging menggunakan algoritma Leiden
          </p>
        </div>
        <div className="flex items-center gap-3">
          {graphQuery.isLoading && (
            <span className="text-sm text-slate-400 animate-pulse">Memuat data...</span>
          )}
          {graphQuery.isError && (
            <span className="text-sm text-red-500">Gagal memuat data jaringan</span>
          )}
          {graphQuery.isSuccess && communities.length === 0 && (
            <span className="text-sm text-slate-400">Belum ada komunitas terdeteksi</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        {/* Graph canvas */}
        <div className="xl:col-span-3 bg-slate-900 rounded-xl overflow-hidden border border-slate-700 shadow-lg" style={{ height: 480 }}>
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeId="id"
            nodeColor={(n) => (n as { color: string }).color}
            nodeVal={(n) => (n as { size: number }).size}
            nodeLabel={(n) => {
              const node = n as { id: string; communityId: number | string }
              return `${node.id} (Komunitas #${String(node.communityId)})`
            }}
            linkColor={(l) => (l as { color: string }).color}
            linkWidth={(l) => Math.max(1, ((l as { weight?: number }).weight ?? 0.5) * 4)}

            backgroundColor="#0f172a"
            onNodeClick={handleNodeClick}
            nodeCanvasObjectMode={() => 'after'}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const n = node as { id: string; x?: number; y?: number }
              const label = n.id
              const fontSize = Math.max(8, 12 / globalScale)
              ctx.font = `${fontSize}px Inter, system-ui, sans-serif`
              ctx.textAlign = 'center'
              ctx.textBaseline = 'top'
              ctx.fillStyle = 'rgba(255,255,255,0.85)'
              ctx.fillText(label, n.x ?? 0, (n.y ?? 0) + 7)
            }}
            cooldownTicks={80}
            d3AlphaDecay={0.03}
            d3VelocityDecay={0.3}
          />
        </div>

        {/* Community list + selected detail */}
        <div className="xl:col-span-1 space-y-3 overflow-y-auto" style={{ maxHeight: 480 }}>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-700">
                {communities.length} Komunitas Terdeteksi
              </h3>
            </div>
            <div className="divide-y divide-gray-100">
              {communities.map((c, ci) => {
                const color = COMMUNITY_COLORS[ci % COMMUNITY_COLORS.length]
                const isSelected = selectedCommunity?.community_id === c.community_id
                return (
                  <button
                    key={String(c.community_id)}
                    onClick={() => setSelectedCommunity(isSelected ? null : c)}
                    className={`w-full text-left px-4 py-3 transition-colors hover:bg-slate-50 ${
                      isSelected ? 'bg-blue-50 border-l-2 border-blue-500' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-sm font-medium text-slate-700">
                        Komunitas #{String(c.community_id)}
                      </span>
                      <span className="text-xs text-slate-400">
                        {c.members.length} vendor
                      </span>
                    </div>
                    {c.risk_score !== undefined && (
                      <RiskScoreBar score={c.risk_score} />
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Selected community detail */}
          {selectedCommunity && (
            <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-700">
                Detail Komunitas #{String(selectedCommunity.community_id)}
              </h3>
              <div>
                <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">
                  Anggota Vendor:
                </p>
                <ul className="space-y-1">
                  {selectedCommunity.members.map((m) => (
                    <li
                      key={m}
                      className={`text-xs px-2 py-1 rounded ${
                        selectedNode === m
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'bg-slate-50 text-slate-600'
                      }`}
                    >
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
              {(selectedCommunity.tender_ids?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">
                    Tender Terkait:
                  </p>
                  <ul className="space-y-1">
                    {selectedCommunity.tender_ids?.map((tid) => (
                      <li key={tid} className="text-xs text-blue-600 font-mono">
                        {tid}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="bg-slate-800 rounded-xl p-4 text-white">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">Legenda</p>
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span>Risiko Tinggi (&gt;70%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-amber-400" />
            <span>Risiko Menengah (40–70%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500" />
            <span>Risiko Rendah (&lt;40%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-1 bg-slate-400" style={{ height: 2 }} />
            <span>Hubungan penawaran bersama (co-bidding)</span>
          </div>
        </div>
      </div>
    </div>
  )
}
