import React, { useState, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ForceGraph2D } from 'react-force-graph'
import { getGraphCommunities } from '../api/client'
import type { GraphCommunity } from '../types/models'

const COMMUNITY_COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#06b6d4', '#22c55e']

// Glow shadow per community color index
const COMMUNITY_GLOWS = [
  'shadow-[0_0_12px_rgba(239,68,68,0.5)]',
  'shadow-[0_0_12px_rgba(245,158,11,0.5)]',
  'shadow-[0_0_12px_rgba(59,130,246,0.5)]',
  'shadow-[0_0_12px_rgba(139,92,246,0.5)]',
  'shadow-[0_0_12px_rgba(6,182,212,0.5)]',
  'shadow-[0_0_12px_rgba(34,197,94,0.5)]',
]

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
  const barClass = score >= 0.7
    ? 'bg-gradient-to-r from-red-600 to-rose-400'
    : score >= 0.4
    ? 'bg-gradient-to-r from-amber-500 to-orange-400'
    : 'bg-gradient-to-r from-green-500 to-emerald-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
        <div className={`h-1.5 rounded-full ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono font-medium text-slate-400 w-8 text-right">{pct}%</span>
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Jaringan Kartel Vendor
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deteksi komunitas bid-rigging menggunakan algoritma Leiden
          </p>
        </div>
        <div className="flex items-center gap-3">
          {graphQuery.isLoading && (
            <span className="text-sm text-slate-500 motion-safe:animate-pulse font-mono">Memuat data...</span>
          )}
          {graphQuery.isError && (
            <span className="text-sm text-red-400">Gagal memuat data jaringan</span>
          )}
          {graphQuery.isSuccess && communities.length === 0 && (
            <span className="text-sm text-slate-500">Belum ada komunitas terdeteksi</span>
          )}
          {graphQuery.isSuccess && communities.length > 0 && (
            <span className="text-xs font-mono text-slate-500 bg-white/5 border border-white/10 px-3 py-1 rounded-full">
              {communities.length} komunitas · {graphData.nodes.length} vendor
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        {/* Graph canvas — wrapped in bg-dot-grid */}
        <div
          className="xl:col-span-3 bg-dot-grid rounded-2xl overflow-hidden border border-white/10 shadow-[0_0_30px_rgba(6,182,212,0.08)]"
          style={{ height: 480 }}
        >
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
            backgroundColor="#020617"
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

        {/* Community list + selected detail — glass sidebar */}
        <div className="xl:col-span-1 space-y-3 overflow-y-auto" style={{ maxHeight: 480 }}>
          <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-white/10">
              <h3 className="text-sm font-semibold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                Komunitas Terdeteksi
              </h3>
              <p className="text-xs font-mono text-slate-500 mt-0.5">{communities.length} komunitas</p>
            </div>
            <div className="divide-y divide-white/5">
              {communities.map((c, ci) => {
                const color = COMMUNITY_COLORS[ci % COMMUNITY_COLORS.length]
                const glow = COMMUNITY_GLOWS[ci % COMMUNITY_GLOWS.length]
                const isSelected = selectedCommunity?.community_id === c.community_id
                return (
                  <button
                    key={String(c.community_id)}
                    onClick={() => setSelectedCommunity(isSelected ? null : c)}
                    className={`w-full text-left px-4 py-3 motion-safe:transition-all motion-safe:duration-200 ${
                      isSelected
                        ? 'bg-white/10 border-l-2 border-cyan-400'
                        : 'hover:bg-white/5 border-l-2 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <span
                        className={`relative flex h-3 w-3 flex-shrink-0`}
                      >
                        <span
                          className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full opacity-60"
                          style={{ backgroundColor: color }}
                        />
                        <span
                          className={`relative inline-flex rounded-full h-3 w-3 ${glow}`}
                          style={{ backgroundColor: color }}
                        />
                      </span>
                      <span className="text-sm font-medium text-slate-200">
                        Komunitas #{String(c.community_id)}
                      </span>
                      <span className="text-xs font-mono text-slate-500 ml-auto">
                        {c.members.length}
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
            <div className="bg-white/5 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.15)] rounded-2xl p-4 space-y-3">
              <h3 className="text-sm font-semibold text-cyan-400">
                Detail Komunitas #{String(selectedCommunity.community_id)}
              </h3>
              <div>
                <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wider">
                  Anggota Vendor
                </p>
                <ul className="space-y-1">
                  {selectedCommunity.members.map((m) => (
                    <li
                      key={m}
                      className={`text-xs px-2 py-1 rounded font-mono ${
                        selectedNode === m
                          ? 'bg-cyan-900/40 text-cyan-300 border border-cyan-500/30'
                          : 'bg-white/5 text-slate-400'
                      }`}
                    >
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
              {(selectedCommunity.tender_ids?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wider">
                    Tender Terkait
                  </p>
                  <ul className="space-y-1">
                    {selectedCommunity.tender_ids?.map((tid) => (
                      <li key={tid} className="text-xs text-cyan-400 font-mono bg-white/5 px-2 py-1 rounded">
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
      <div className="glass-card p-4">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Legenda</p>
        <div className="flex flex-wrap gap-5 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]" />
            <span>Risiko Tinggi (&gt;70%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(245,158,11,0.6)]" />
            <span>Risiko Menengah (40–70%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]" />
            <span>Risiko Rendah (&lt;40%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-px w-6 bg-slate-500" />
            <span>Hubungan penawaran bersama (co-bidding)</span>
          </div>
        </div>
      </div>
    </div>
  )
}
