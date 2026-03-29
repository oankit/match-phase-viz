import { useRef, useEffect } from 'react'
import * as d3 from 'd3'
import { computeShapeGraph } from '../utils/shapeGraph'
import './PitchCanvas.css'

const PitchCanvas = ({
  frame,
  voronoi,
  selectedPhase,
  overlayMode = 'shape_graph',
  metadata
}) => {
  const canvasRef = useRef(null)

  // Team colors
  const teamColors = {
    'DFL-CLU-00000S': '#2b6da4',
    'DFL-CLU-00000B': '#c83c35',
  }

  useEffect(() => {
    const canvas = canvasRef.current

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
    ctx.fillStyle = '#3a8c3a'
    ctx.fillRect(0, 0, width, height)

    // Draw pitch markings
    drawPitchMarkings(ctx, width, height)

    // Draw Rest Defence / Convex Hull overlay
    if (overlayMode === 'convex_hull' && voronoi) {
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

    // Draw live shape graph edges per team (before players so edges are behind dots)
    if (overlayMode === 'shape_graph' && frame.players) {
      // Build GK ID set from metadata (authoritative source)
      const gkIds = new Set()
      if (metadata?.teams) {
        metadata.teams.forEach(team => {
          team.players?.forEach(p => {
            if (p.position && p.position.toLowerCase().startsWith('goalkeeper')) {
              gkIds.add(p.id)
            }
          })
        })
      }

      // Group players by team
      const teamGroups = {}
      frame.players.forEach(player => {
        if (!teamGroups[player.team]) teamGroups[player.team] = []
        teamGroups[player.team].push(player)
      })

      Object.entries(teamGroups).forEach(([teamId, players]) => {
        if (players.length < 4) return

        // Exclude goalkeeper using metadata position data
        let outfield
        if (gkIds.size > 0) {
          outfield = players.filter(p => !gkIds.has(p.id))
        } else {
          // Fallback: exclude player most isolated from team centroid on x-axis
          const meanX = players.reduce((s, p) => s + p.x, 0) / players.length
          let maxDist = 0, gkIdx = 0
          players.forEach((p, i) => {
            const dist = Math.abs(p.x - meanX)
            if (dist > maxDist) { maxDist = dist; gkIdx = i }
          })
          outfield = players.filter((_, i) => i !== gkIdx)
        }

        if (outfield.length < 4) return

        const coords = outfield.map(p => [p.x, p.y])
        const edges = computeShapeGraph(coords)

        // Draw edges on canvas
        const color = teamColors[teamId] || '#666'
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        ctx.globalAlpha = 0.35
        ctx.setLineDash([])

        edges.forEach(([i, j]) => {
          ctx.beginPath()
          ctx.moveTo(xScale(coords[i][0]), yScale(coords[i][1]))
          ctx.lineTo(xScale(coords[j][0]), yScale(coords[j][1]))
          ctx.stroke()
        })

        ctx.globalAlpha = 1.0
      })
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

        if (player.number) {
          ctx.fillStyle = 'white'
          ctx.font = 'bold 10px Inter, Arial'
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

  }, [frame, voronoi, selectedPhase, overlayMode, metadata])

  const drawPitchMarkings = (ctx, width, height) => {
    ctx.strokeStyle = 'rgba(255,255,255,0.5)'
    ctx.lineWidth = 1.5

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
    ctx.fillStyle = 'rgba(255,255,255,0.5)'
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
        width={940}
        height={612}
        className="pitch-canvas"
      />
    </div>
  )
}

export default PitchCanvas
