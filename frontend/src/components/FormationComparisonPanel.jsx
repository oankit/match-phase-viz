import { useRef, useEffect } from 'react'
import * as d3 from 'd3'
import { drawFormationGlyph } from '../utils/drawFormation'
import './FormationComparisonPanel.css'

const POSSESSION_PHASES = new Set(['attacking', 'build_up', 'counter_attack'])
const NO_POSSESSION_PHASES = new Set(['high_press', 'mid_block', 'defensive_block'])

// Team colors (same as PitchCanvas)
const teamColors = {
  'DFL-CLU-00000S': '#DC2626',
  'DFL-CLU-00000B': '#2563EB'
}

/**
 * Get the most frequent formation label from a list of formations.
 */
function getModeFormation(formations) {
  if (!formations || formations.length === 0) return null

  const counts = {}
  formations.forEach(f => {
    const label = f.formation_label || 'unknown'
    counts[label] = (counts[label] || 0) + 1
  })

  let best = null
  let bestCount = 0
  for (const [label, count] of Object.entries(counts)) {
    if (count > bestCount) {
      best = label
      bestCount = count
    }
  }

  return { label: best, count: bestCount, total: formations.length }
}

/**
 * Average the raw_mean_positions (or mean_positions) across multiple formations.
 * Returns a synthetic formation object for rendering.
 */
function averageFormation(formations, teamId) {
  if (!formations || formations.length === 0) return null

  // Prefer raw_mean_positions for proper pitch display
  const useRaw = formations[0].raw_mean_positions != null
  const posKey = useRaw ? 'raw_mean_positions' : 'mean_positions'

  const n = formations[0][posKey].length
  const avgPositions = Array.from({ length: n }, () => [0, 0])
  const avgRawPositions = useRaw ? Array.from({ length: n }, () => [0, 0]) : null
  const avgStability = new Array(n).fill(0)

  formations.forEach(f => {
    const pos = f[posKey]
    pos.forEach((p, i) => {
      avgPositions[i][0] += p[0] / formations.length
      avgPositions[i][1] += p[1] / formations.length
    })
    if (useRaw && f.raw_mean_positions) {
      f.raw_mean_positions.forEach((p, i) => {
        avgRawPositions[i][0] += p[0] / formations.length
        avgRawPositions[i][1] += p[1] / formations.length
      })
    }
    if (f.stability_scores) {
      f.stability_scores.forEach((s, i) => {
        avgStability[i] += s / formations.length
      })
    }
  })

  // Aggregate shape graph edges by frequency (keep edges that appear in >40% of formations)
  const edgeCounts = {}
  formations.forEach(f => {
    if (f.shape_graph_edges) {
      f.shape_graph_edges.forEach(([i, j]) => {
        const key = `${Math.min(i, j)}-${Math.max(i, j)}`
        edgeCounts[key] = (edgeCounts[key] || 0) + 1
      })
    }
  })

  const threshold = formations.length * 0.4
  const avgEdges = []
  for (const [key, count] of Object.entries(edgeCounts)) {
    if (count >= threshold) {
      const [i, j] = key.split('-').map(Number)
      avgEdges.push([i, j])
    }
  }

  // Aggregate band assignments by mode
  const bandCounts = {}
  formations.forEach(f => {
    if (f.band_counts) {
      const key = f.band_counts.join('-')
      bandCounts[key] = (bandCounts[key] || 0) + 1
    }
  })

  let bestBandKey = null
  let bestBandCount = 0
  for (const [key, count] of Object.entries(bandCounts)) {
    if (count > bestBandCount) {
      bestBandKey = key
      bestBandCount = count
    }
  }

  // Find a formation with the mode band counts to get band_assignments
  const modeBandCountsArr = bestBandKey ? bestBandKey.split('-').map(Number) : []
  const modeFormation = formations.find(f =>
    f.band_counts && f.band_counts.join('-') === bestBandKey
  )

  // Also average the centroid-normalized positions for fallback
  const avgCentroidPositions = Array.from({ length: n }, () => [0, 0])
  formations.forEach(f => {
    if (f.mean_positions) {
      f.mean_positions.forEach((p, i) => {
        avgCentroidPositions[i][0] += p[0] / formations.length
        avgCentroidPositions[i][1] += p[1] / formations.length
      })
    }
  })

  return {
    mean_positions: avgCentroidPositions,
    raw_mean_positions: avgRawPositions || avgPositions,
    shape_graph_edges: avgEdges,
    stability_scores: avgStability,
    band_assignments: modeFormation?.band_assignments || [],
    band_counts: modeBandCountsArr,
    formation_label: getModeFormation(formations)?.label || 'unknown',
    team_id: teamId,
  }
}

/**
 * Draw a mini half-pitch with simplified markings (vertical orientation).
 * Goal at top, center line at bottom.
 */
function drawMiniHalfPitch(svg, width, height) {
  const g = svg.append('g').attr('class', 'mini-pitch')
  const pad = 4

  // Background
  g.append('rect')
    .attr('width', width)
    .attr('height', height)
    .attr('fill', '#4ade80')
    .attr('rx', 4)

  // Pitch boundary
  g.append('rect')
    .attr('x', pad).attr('y', pad)
    .attr('width', width - pad * 2).attr('height', height - pad * 2)
    .attr('fill', 'none')
    .attr('stroke', 'white')
    .attr('stroke-width', 1.5)

  // Center line at bottom (represents halfway line)
  g.append('line')
    .attr('x1', pad).attr('y1', height - pad)
    .attr('x2', width - pad).attr('y2', height - pad)
    .attr('stroke', 'white').attr('stroke-width', 1.5)

  // Center circle arc at bottom
  g.append('path')
    .attr('d', d3.arc()({
      innerRadius: 0,
      outerRadius: width * 0.15,
      startAngle: -Math.PI / 2,
      endAngle: Math.PI / 2,
    }))
    .attr('transform', `translate(${width / 2}, ${height - pad}) rotate(180)`)
    .attr('fill', 'none')
    .attr('stroke', 'white')
    .attr('stroke-width', 1)

  // Penalty area at top
  const penaltyW = width * 0.55
  const penaltyH = height * 0.18
  g.append('rect')
    .attr('x', (width - penaltyW) / 2).attr('y', pad)
    .attr('width', penaltyW).attr('height', penaltyH)
    .attr('fill', 'none')
    .attr('stroke', 'white').attr('stroke-width', 1)

  // Goal area at top
  const goalW = width * 0.3
  const goalH = height * 0.07
  g.append('rect')
    .attr('x', (width - goalW) / 2).attr('y', pad)
    .attr('width', goalW).attr('height', goalH)
    .attr('fill', 'none')
    .attr('stroke', 'white').attr('stroke-width', 1)

  // Penalty spot
  g.append('circle')
    .attr('cx', width / 2).attr('cy', pad + penaltyH * 0.75)
    .attr('r', 2)
    .attr('fill', 'white')

  // Goal line representation
  const goalPostW = width * 0.12
  g.append('line')
    .attr('x1', (width - goalPostW) / 2).attr('y1', pad)
    .attr('x2', (width + goalPostW) / 2).attr('y2', pad)
    .attr('stroke', 'white').attr('stroke-width', 3)
}

const MiniFormation = ({ formation, title, subtitle, width = 220, height = 300 }) => {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    svg.attr('width', width).attr('height', height)

    if (!formation) {
      svg.append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#9CA3AF')
        .attr('font-size', '13px')
        .text('No data')
      return
    }

    drawMiniHalfPitch(svg, width, height)

    const hasRaw = formation.raw_mean_positions != null
    const pad = 20

    // For the half-pitch template view, we want players spread across the display
    // like Stats Perform templates. We use the raw positions but auto-fit to fill
    // the available space, with vertical orientation (goal at top).
    //
    // Raw positions: x = pitch length (0-1), y = pitch width (0-1)
    // Display: x-axis = lateral (pitch y), y-axis = depth (pitch x)
    // Goal at top = defenders near top, attackers near bottom

    const positions = hasRaw ? formation.raw_mean_positions : formation.mean_positions

    // Compute extent of positions
    const pitchXs = positions.map(p => p[0])  // depth
    const pitchYs = positions.map(p => p[1])  // lateral
    const xMin = Math.min(...pitchXs)
    const xMax = Math.max(...pitchXs)
    const yMin = Math.min(...pitchYs)
    const yMax = Math.max(...pitchYs)

    // Add padding around the positions (15% on each side)
    const xPadData = (xMax - xMin) * 0.2 || 0.05
    const yPadData = (yMax - yMin) * 0.2 || 0.05

    // Map: pitch y (lateral) -> display x, pitch x (depth) -> display y
    // Defenders (lower x) at top, attackers (higher x) at bottom
    const displayXScale = d3.scaleLinear()
      .domain([yMin - yPadData, yMax + yPadData])
      .range([pad, width - pad])
    const displayYScale = d3.scaleLinear()
      .domain([xMin - xPadData, xMax + xPadData])
      .range([pad + 15, height - pad])

    // Create a synthetic formation with swapped coordinates for display
    // (since drawFormationGlyph expects [x, y] but we want [pitchY, pitchX] layout)
    const displayFormation = {
      ...formation,
      raw_mean_positions: positions.map(p => [p[1], p[0]]),  // swap to [lateral, depth]
      mean_positions: positions.map(p => [p[1], p[0]]),
    }

    drawFormationGlyph(svg, displayFormation, displayXScale, displayYScale,
      teamColors[formation.team_id] || '#666',
      { showShapeGraph: true, showBandLines: true, showLabel: false, opacity: 0.85, useRawPositions: hasRaw }
    )
  }, [formation, width, height])

  return (
    <div className="mini-formation">
      <div className="mini-formation-header">
        <span className="mini-formation-title">{title}</span>
        {subtitle && <span className="mini-formation-subtitle">{subtitle}</span>}
      </div>
      <svg ref={svgRef}></svg>
    </div>
  )
}

const FormationComparisonPanel = ({
  formations = [],
  phases = [],
  selectedTeam,
  teamNameMap = {},
}) => {
  if (!formations || formations.length === 0 || !selectedTeam) {
    return null
  }

  // Filter formations for selected team
  const teamFormations = formations.filter(f => f.team_id === selectedTeam)

  if (teamFormations.length === 0) {
    return null
  }

  // Split by possession context
  const possessionFormations = teamFormations.filter(f =>
    POSSESSION_PHASES.has(f.phase_type)
  )
  const noPossessionFormations = teamFormations.filter(f =>
    NO_POSSESSION_PHASES.has(f.phase_type)
  )

  const inPossession = averageFormation(possessionFormations, selectedTeam)
  const outPossession = averageFormation(noPossessionFormations, selectedTeam)

  const inPossMode = getModeFormation(possessionFormations)
  const outPossMode = getModeFormation(noPossessionFormations)

  const teamName = teamNameMap[selectedTeam] || selectedTeam

  return (
    <div className="formation-comparison">
      <h3>Formation Comparison - {teamName}</h3>
      <div className="comparison-row">
        <MiniFormation
          formation={inPossession}
          title={`In Possession: ${inPossMode?.label || 'N/A'}`}
          subtitle={inPossMode ? `${inPossMode.count}/${inPossMode.total} phases` : null}
        />
        <MiniFormation
          formation={outPossession}
          title={`Out of Possession: ${outPossMode?.label || 'N/A'}`}
          subtitle={outPossMode ? `${outPossMode.count}/${outPossMode.total} phases` : null}
        />
      </div>
    </div>
  )
}

export default FormationComparisonPanel
