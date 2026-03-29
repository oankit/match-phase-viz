import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import * as d3 from 'd3'
import { computeShapeGraph } from '../utils/shapeGraph'
import { getTeamColor } from '../utils/matchCatalog'
import './PitchCanvas.css'

const PitchCanvas = ({
  frame,
  voronoi,
  selectedPhase,
  overlayMode = 'shape_graph',
  metadata
}) => {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const [canvasSize, setCanvasSize] = useState({ width: 940, height: 612 })

  const teamColors = useMemo(() => {
    const teams = metadata?.teams || []
    const map = {}
    teams.forEach(t => { map[t.id] = getTeamColor(t.id) })
    return map
  }, [metadata?.teams])

  const measureContainer = useCallback(() => {
    if (containerRef.current) {
      const w = containerRef.current.clientWidth
      const h = Math.round(w * (68 / 105))
      setCanvasSize({ width: w, height: h })
    }
  }, [])

  useEffect(() => {
    measureContainer()
    window.addEventListener('resize', measureContainer)
    return () => window.removeEventListener('resize', measureContainer)
  }, [measureContainer])

  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas || !frame) return

    const dpr = window.devicePixelRatio || 1
    const width = canvasSize.width
    const height = canvasSize.height

    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = width + 'px'
    canvas.style.height = height + 'px'

    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    // Scale coordinates from normalized (0-1) to canvas pixels
    const xScale = d3.scaleLinear().domain([0, 1]).range([0, width])
    const yScale = d3.scaleLinear().domain([0, 1]).range([0, height])

    // Clear canvas
    ctx.clearRect(0, 0, width, height)

    ctx.fillStyle = '#4a8c5c'
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

        const dotRadius = Math.max(7, width * 0.009)

        voronoi.control_grid.forEach(pt => {
          const [px, py, teamIdx, timeToReach] = Array.isArray(pt)
            ? pt
            : [pt.x, pt.y, null, pt.time || 0]

          const controllingTeam = teamIdx !== null ? teams[teamIdx] : pt.team_id
          const color = teamColors[controllingTeam] || '#666'

          const maxTime = 3.0
          const normalizedTime = Math.min((timeToReach || 0) / maxTime, 1)
          const controlStrength = 1 - normalizedTime
          const opacity = 0.35 + 0.55 * controlStrength

          const alphaHex = Math.floor(opacity * 255).toString(16).padStart(2, '0')

          ctx.beginPath()
          ctx.arc(xScale(px), yScale(py), dotRadius, 0, 2 * Math.PI)
          ctx.fillStyle = `${color}${alphaHex}`
          ctx.fill()
        })
        ctx.restore()
      }

      if (voronoi.convex_hull && voronoi.convex_hull.length > 0) {
        // Draw the convex hull outline (Rest Defence border)
        ctx.beginPath()
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)'
        ctx.lineWidth = 1.2
        ctx.setLineDash([4, 3])
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

        const color = teamColors[teamId] || '#666'
        ctx.setLineDash([])
        ctx.globalAlpha = 0.65

        edges.forEach(([i, j]) => {
          const x1 = xScale(coords[i][0]), y1 = yScale(coords[i][1])
          const x2 = xScale(coords[j][0]), y2 = yScale(coords[j][1])

          ctx.strokeStyle = color
          ctx.lineWidth = 2
          ctx.beginPath()
          ctx.moveTo(x1, y1)
          ctx.lineTo(x2, y2)
          ctx.stroke()
        })

        ctx.globalAlpha = 1.0
      })
    }

    // Draw formation lines overlay (defensive / midfield / attack lines)
    if (overlayMode === 'formation_lines' && frame.players) {
      const playerLineMap = {}
      if (metadata?.teams) {
        metadata.teams.forEach(team => {
          team.players?.forEach(p => {
            const pos = (p.position || '').toLowerCase()
            if (pos.startsWith('goalkeeper')) {
              playerLineMap[p.id] = 'gk'
            } else if (pos.includes('back') || pos.includes('center back')) {
              playerLineMap[p.id] = 'def'
            } else if (pos.includes('midfield')) {
              playerLineMap[p.id] = 'mid'
            } else if (pos.includes('wing') || pos.includes('striker') || pos.includes('forward') || pos.includes('attacking')) {
              playerLineMap[p.id] = 'att'
            } else {
              playerLineMap[p.id] = 'unknown'
            }
          })
        })
      }

      const teamGroups = {}
      frame.players.forEach(player => {
        if (!teamGroups[player.team]) teamGroups[player.team] = []
        teamGroups[player.team].push(player)
      })

      Object.entries(teamGroups).forEach(([teamId, players]) => {
        if (players.length < 4) return

        const lineGroups = { def: [], mid: [], att: [] }
        players.forEach(p => {
          const line = playerLineMap[p.id]
          if (line && lineGroups[line]) {
            lineGroups[line].push(p)
          } else if (line !== 'gk') {
            lineGroups.mid.push(p)
          }
        })

        const color = teamColors[teamId] || '#666'
        ctx.setLineDash([])
        ctx.globalAlpha = 0.7

        Object.values(lineGroups).forEach(line => {
          if (line.length < 2) return
          const sortedByY = [...line].sort((a, b) => a.y - b.y)

          ctx.strokeStyle = color
          ctx.lineWidth = 2.5
          ctx.beginPath()
          ctx.moveTo(xScale(sortedByY[0].x), yScale(sortedByY[0].y))
          for (let i = 1; i < sortedByY.length; i++) {
            ctx.lineTo(xScale(sortedByY[i].x), yScale(sortedByY[i].y))
          }
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

        const r = 13
        ctx.beginPath()
        ctx.arc(x, y, r, 0, 2 * Math.PI)
        ctx.fillStyle = teamColors[player.team] || '#666'
        ctx.fill()
ctx.strokeStyle = 'rgba(255,255,255,0.7)'
      ctx.lineWidth = 1
        ctx.stroke()

        if (player.number != null) {
          ctx.font = "bold 11px 'Plus Jakarta Sans', sans-serif"
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillStyle = 'white'
          ctx.fillText(player.number, x, y + 0.5)
        }
      })
    }

    // Draw ball
    if (frame.ball) {
      const ballX = xScale(frame.ball.x)
      const ballY = yScale(frame.ball.y)

      ctx.beginPath()
      ctx.arc(ballX, ballY, 8, 0, 2 * Math.PI)
      ctx.fillStyle = 'white'
      ctx.fill()
      ctx.strokeStyle = '#333'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }

  }, [frame, voronoi, selectedPhase, overlayMode, metadata, canvasSize])

  const drawPitchMarkings = (ctx, width, height) => {
    ctx.strokeStyle = 'rgba(255,255,255,0.3)'
    ctx.lineWidth = 1.2

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
    ctx.fillStyle = 'rgba(255,255,255,0.3)'
    ctx.beginPath()
    ctx.arc(width * 0.11, height / 2, 2, 0, 2 * Math.PI)
    ctx.fill()

    ctx.beginPath()
    ctx.arc(width * 0.89, height / 2, 2, 0, 2 * Math.PI)
    ctx.fill()
  }

  return (
    <div className="pitch-container" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className="pitch-canvas"
      />
    </div>
  )
}

export default PitchCanvas
