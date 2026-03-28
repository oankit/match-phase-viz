/**
 * Draw formation overlay on an SVG selection.
 *
 * Renders shape graph edges, horizontal band lines connecting players
 * in the same defensive/midfield/attack band, player nodes at mean
 * positions, and a formation label (e.g., "4-4-2").
 *
 * Based on Brandes et al. 2025 shape graph algorithm and Sotudeh 2025
 * survey visualization style (Figure 1: horizontal dashed band lines).
 */

/**
 * @param {d3.Selection} svg - D3 selection of the SVG element
 * @param {Object} formation - Formation data from formations.json
 * @param {Function} xScale - D3 scale mapping data coords -> pixel x
 * @param {Function} yScale - D3 scale mapping data coords -> pixel y
 * @param {string} teamColor - Hex color for this team
 * @param {Object} options - Rendering options
 */
export function drawFormationGlyph(svg, formation, xScale, yScale, teamColor, options = {}) {
  const {
    showShapeGraph = true,
    showBandLines = true,
    showLabel = true,
    opacity = 0.6,
    useRawPositions = false,
  } = options

  // Use raw positions (absolute pitch coords) if available and requested
  const positions = useRawPositions && formation.raw_mean_positions
    ? formation.raw_mean_positions
    : formation.mean_positions
  if (!positions || positions.length === 0) return

  let fxScale, fyScale

  if (useRawPositions) {
    // Raw positions are already in meaningful coordinate space (0-1 pitch)
    // Use the provided scales directly
    fxScale = xScale
    fyScale = yScale
  } else {
    // Formation positions are centroid-normalized (range ~-0.3 to +0.35).
    // Compute the data extent and create fitting scales.
    const xs = positions.map(p => p[0])
    const ys = positions.map(p => p[1])
    const xMin = Math.min(...xs)
    const xMax = Math.max(...xs)
    const yMin = Math.min(...ys)
    const yMax = Math.max(...ys)

    // Get the pixel range from the provided scales
    const pxRange = xScale.range()
    const pyRange = yScale.range()

    // Add padding (10% on each side)
    const xPad = (xMax - xMin) * 0.12 || 0.05
    const yPad = (yMax - yMin) * 0.12 || 0.05

    // Create internal scales that map formation coords -> pixel space
    fxScale = xScale.copy().domain([xMin - xPad, xMax + xPad]).range(pxRange)
    fyScale = yScale.copy().domain([yMin - yPad, yMax + yPad]).range(pyRange)
  }

  const g = svg.append('g')
    .attr('class', 'formation-overlay')
    .attr('opacity', opacity)

  // 1. Draw shape graph edges
  if (showShapeGraph) {
    const edges = formation.shape_graph_edges
    if (edges && edges.length > 0) {
      // Use shape graph edges (filtered Delaunay)
      edges.forEach(([i, j]) => {
        if (i < positions.length && j < positions.length) {
          g.append('line')
            .attr('x1', fxScale(positions[i][0]))
            .attr('y1', fyScale(positions[i][1]))
            .attr('x2', fxScale(positions[j][0]))
            .attr('y2', fyScale(positions[j][1]))
            .attr('stroke', teamColor)
            .attr('stroke-width', 2)
            .attr('stroke-opacity', 0.6)
        }
      })
    } else if (formation.mean_adjacency) {
      // Fallback: use old adjacency matrix
      const adjacency = formation.mean_adjacency
      for (let i = 0; i < positions.length; i++) {
        for (let j = i + 1; j < positions.length; j++) {
          if (adjacency[i] && adjacency[i][j] > 0) {
            g.append('line')
              .attr('x1', fxScale(positions[i][0]))
              .attr('y1', fyScale(positions[i][1]))
              .attr('x2', fxScale(positions[j][0]))
              .attr('y2', fyScale(positions[j][1]))
              .attr('stroke', teamColor)
              .attr('stroke-width', adjacency[i][j] * 3)
              .attr('stroke-opacity', adjacency[i][j] * 0.5)
          }
        }
      }
    }
  }

  // 2. Draw horizontal band lines
  if (showBandLines && formation.band_assignments) {
    const bandAssignments = formation.band_assignments
    const numBands = formation.band_counts ? formation.band_counts.length : 0

    for (let b = 0; b < numBands; b++) {
      // Get players in this band
      const bandPlayerIndices = []
      bandAssignments.forEach((band, idx) => {
        if (band === b) bandPlayerIndices.push(idx)
      })

      if (bandPlayerIndices.length < 2) continue

      // Compute mean x of band (the "line height" on the pitch)
      const bandX = bandPlayerIndices.reduce((sum, idx) => sum + positions[idx][0], 0) / bandPlayerIndices.length

      // Get min/max y of players in this band
      const bandYs = bandPlayerIndices.map(idx => positions[idx][1])
      const minY = Math.min(...bandYs)
      const maxY = Math.max(...bandYs)

      // Draw dashed lateral line at band x, spanning from minY to maxY
      // with some padding
      const padding = (maxY - minY) * 0.15
      g.append('line')
        .attr('x1', fxScale(bandX))
        .attr('y1', fyScale(minY - padding))
        .attr('x2', fxScale(bandX))
        .attr('y2', fyScale(maxY + padding))
        .attr('stroke', teamColor)
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '6,4')
        .attr('stroke-opacity', 0.5)

      // Draw short horizontal ticks connecting each player to the band line
      bandPlayerIndices.forEach(idx => {
        g.append('line')
          .attr('x1', fxScale(bandX))
          .attr('y1', fyScale(positions[idx][1]))
          .attr('x2', fxScale(positions[idx][0]))
          .attr('y2', fyScale(positions[idx][1]))
          .attr('stroke', teamColor)
          .attr('stroke-width', 1)
          .attr('stroke-opacity', 0.3)
          .attr('stroke-dasharray', '3,3')
      })
    }
  }

  // 3. Draw player nodes at mean positions
  positions.forEach((pos, i) => {
    g.append('circle')
      .attr('cx', fxScale(pos[0]))
      .attr('cy', fyScale(pos[1]))
      .attr('r', 6)
      .attr('fill', teamColor)
      .attr('stroke', 'white')
      .attr('stroke-width', 2)
      .attr('opacity', formation.stability_scores?.[i] || 0.8)
  })

  // 4. Draw formation label
  if (showLabel && formation.formation_label) {
    // Position label near the team's centroid
    const centroidX = positions.reduce((sum, p) => sum + p[0], 0) / positions.length
    const centroidY = positions.reduce((sum, p) => sum + p[1], 0) / positions.length

    // Draw label with background
    const labelG = g.append('g')
      .attr('transform', `translate(${fxScale(centroidX)}, ${fyScale(centroidY) - 20})`)

    labelG.append('rect')
      .attr('x', -25)
      .attr('y', -10)
      .attr('width', 50)
      .attr('height', 18)
      .attr('rx', 4)
      .attr('fill', 'rgba(0,0,0,0.7)')

    labelG.append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', 'white')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold')
      .attr('font-family', 'Arial, sans-serif')
      .text(formation.formation_label)
  }
}
