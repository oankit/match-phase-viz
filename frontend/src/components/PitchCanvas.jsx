import { useRef, useEffect } from 'react'
import * as d3 from 'd3'
import './PitchCanvas.css'

const PitchCanvas = ({
  frame,
  voronoi,
  formations,
  selectedPhase,
  showVoronoi = true
}) => {
  const canvasRef = useRef(null)
  const svgRef = useRef(null)

  // Team colors
  const teamColors = {
    'DFL-CLU-00000S': '#DC2626', // Red for home
    'DFL-CLU-00000B': '#2563EB'  // Blue for away
  }

  useEffect(() => {
    const canvas = canvasRef.current
    const svg = d3.select(svgRef.current)

    if (!canvas || !frame) return

    const ctx = canvas.getContext('2d')
    const width = canvas.width
    const height = canvas.height

    // Scale coordinates from normalized (0-1) to canvas pixels
    const xScale = d3.scaleLinear().domain([0, 1]).range([0, width])
    const yScale = d3.scaleLinear().domain([0, 1]).range([0, height])

    // Clear canvas
    ctx.clearRect(0, 0, width, height)

    // Draw pitch background
    ctx.fillStyle = '#4ade80'
    ctx.fillRect(0, 0, width, height)

    // Draw pitch markings
    drawPitchMarkings(ctx, width, height)

    // Draw Rest Defence overlay if enabled
    if (showVoronoi && voronoi) {
      // Debug log to verify data
      if (voronoi.control_grid) {
        console.log(`Rest Defence: ${voronoi.control_grid.length} control points`)
      }

      if (voronoi.control_grid && voronoi.control_grid.length > 0) {
        // Clip grid dots to the convex hull polygon
        ctx.save()
        if (voronoi.convex_hull && voronoi.convex_hull.length > 0) {
          ctx.beginPath()
          const firstHullPt = voronoi.convex_hull[0]
          ctx.moveTo(xScale(firstHullPt[0]), yScale(firstHullPt[1]))
          voronoi.convex_hull.forEach(pt => {
            ctx.lineTo(xScale(pt[0]), yScale(pt[1]))
          })
          ctx.closePath()
          ctx.clip()
        }

        // teams array maps index to team_id
        const teams = voronoi.teams || []

        voronoi.control_grid.forEach(pt => {
          // Compact format: [x, y, teamIdx, time]
          const [px, py, teamIdx, timeToReach] = Array.isArray(pt)
            ? pt
            : [pt.x, pt.y, null, pt.time || 0]

          const controllingTeam = teamIdx !== null ? teams[teamIdx] : pt.team_id
          const color = teamColors[controllingTeam] || '#666'

          const maxTime = 3.0
          const normalizedTime = Math.min((timeToReach || 0) / maxTime, 1)
          const opacity = 0.7 * (1 - normalizedTime) + 0.1

          const radius = 14

          const gradient = ctx.createRadialGradient(
            xScale(px), yScale(py), 0,
            xScale(px), yScale(py), radius
          )

          const alphaHex = Math.floor(opacity * 255).toString(16).padStart(2, '0')
          gradient.addColorStop(0, `${color}${alphaHex}`)
          gradient.addColorStop(1, `${color}11`)

          ctx.beginPath()
          ctx.arc(xScale(px), yScale(py), radius, 0, 2 * Math.PI)
          ctx.fillStyle = gradient
          ctx.fill()
        })
        ctx.restore()
      }

      if (voronoi.convex_hull && voronoi.convex_hull.length > 0) {
        // Draw the convex hull outline (Rest Defence border)
        ctx.beginPath()
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)'
        ctx.lineWidth = 2
        ctx.setLineDash([5, 5])
        const firstPt = voronoi.convex_hull[0]
        ctx.moveTo(xScale(firstPt[0]), yScale(firstPt[1]))
        voronoi.convex_hull.forEach(pt => {
          ctx.lineTo(xScale(pt[0]), yScale(pt[1]))
        })
        ctx.closePath()
        ctx.stroke()
        ctx.setLineDash([])
      }
    }

    // Draw players
    if (frame.players) {
      frame.players.forEach(player => {
        const x = xScale(player.x)
        const y = yScale(player.y)

        // Player circle
        ctx.beginPath()
        ctx.arc(x, y, 8, 0, 2 * Math.PI)
        ctx.fillStyle = teamColors[player.team] || '#666'
        ctx.fill()
        ctx.strokeStyle = 'white'
        ctx.lineWidth = 2
        ctx.stroke()

        // Player number (if available)
        if (player.number) {
          ctx.fillStyle = 'white'
          ctx.font = 'bold 10px Arial'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(player.number, x, y)
        }
      })
    }

    // Draw ball
    if (frame.ball) {
      const ballX = xScale(frame.ball.x)
      const ballY = yScale(frame.ball.y)

      ctx.beginPath()
      ctx.arc(ballX, ballY, 5, 0, 2 * Math.PI)
      ctx.fillStyle = 'white'
      ctx.fill()
      ctx.strokeStyle = 'black'
      ctx.lineWidth = 1
      ctx.stroke()
    }

    // Clear SVG for formations
    svg.selectAll('*').remove()

    // Draw formation overlay if available
    if (formations && selectedPhase) {
      const phaseFormations = formations.filter(f => f.phase_id === selectedPhase.id)

      phaseFormations.forEach(formation => {
        const g = svg.append('g')
          .attr('class', 'formation-overlay')
          .attr('opacity', 0.6)

        // Draw formation edges
        if (formation.mean_adjacency) {
          const positions = formation.mean_positions
          const adjacency = formation.mean_adjacency

          for (let i = 0; i < positions.length; i++) {
            for (let j = i + 1; j < positions.length; j++) {
              if (adjacency[i] && adjacency[i][j] > 0) {
                g.append('line')
                  .attr('x1', xScale(positions[i][0]))
                  .attr('y1', yScale(positions[i][1]))
                  .attr('x2', xScale(positions[j][0]))
                  .attr('y2', yScale(positions[j][1]))
                  .attr('stroke', teamColors[formation.team_id] || '#999')
                  .attr('stroke-width', adjacency[i][j] * 3)
                  .attr('stroke-opacity', adjacency[i][j])
              }
            }
          }
        }

        // Draw formation nodes
        if (formation.mean_positions) {
          formation.mean_positions.forEach((pos, i) => {
            g.append('circle')
              .attr('cx', xScale(pos[0]))
              .attr('cy', yScale(pos[1]))
              .attr('r', 6)
              .attr('fill', teamColors[formation.team_id] || '#999')
              .attr('stroke', 'white')
              .attr('stroke-width', 2)
              .attr('opacity', formation.stability_scores?.[i] || 0.8)
          })
        }
      })
    }

  }, [frame, voronoi, formations, selectedPhase, showVoronoi])

  const drawPitchMarkings = (ctx, width, height) => {
    ctx.strokeStyle = 'white'
    ctx.lineWidth = 2

    // Pitch boundary
    ctx.strokeRect(0, 0, width, height)

    // Center line
    ctx.beginPath()
    ctx.moveTo(width / 2, 0)
    ctx.lineTo(width / 2, height)
    ctx.stroke()

    // Center circle
    ctx.beginPath()
    ctx.arc(width / 2, height / 2, width * 0.09, 0, 2 * Math.PI)
    ctx.stroke()

    // Penalty areas
    const penaltyWidth = width * 0.17
    const penaltyHeight = height * 0.4

    // Left penalty area
    ctx.strokeRect(0, (height - penaltyHeight) / 2, penaltyWidth, penaltyHeight)

    // Right penalty area
    ctx.strokeRect(width - penaltyWidth, (height - penaltyHeight) / 2, penaltyWidth, penaltyHeight)

    // Goal areas
    const goalWidth = width * 0.06
    const goalHeight = height * 0.2

    // Left goal area
    ctx.strokeRect(0, (height - goalHeight) / 2, goalWidth, goalHeight)

    // Right goal area
    ctx.strokeRect(width - goalWidth, (height - goalHeight) / 2, goalWidth, goalHeight)

    // Penalty spots
    ctx.beginPath()
    ctx.arc(width * 0.11, height / 2, 3, 0, 2 * Math.PI)
    ctx.fill()

    ctx.beginPath()
    ctx.arc(width * 0.89, height / 2, 3, 0, 2 * Math.PI)
    ctx.fill()
  }

  return (
    <div className="pitch-container">
      <canvas
        ref={canvasRef}
        width={800}
        height={520}
        className="pitch-canvas"
      />
      <svg
        ref={svgRef}
        className="formation-svg"
        width={800}
        height={520}
      />
    </div>
  )
}

export default PitchCanvas