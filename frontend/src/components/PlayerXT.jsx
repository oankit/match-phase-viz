import { useRef, useEffect, useMemo } from 'react'
import * as d3 from 'd3'
import { getTeamColor } from '../utils/matchCatalog'
import './PlayerXT.css'

const PlayerXT = ({
  eventXt,
  shotXg,
  metadata = {},
}) => {
  const svgRef = useRef(null)

  const teams = metadata?.teams || []
  const homeTeam = teams[0] || { id: '', name: 'Home' }
  const awayTeam = teams[1] || { id: '', name: 'Away' }

  const teamColors = {
    [homeTeam.id]: getTeamColor(homeTeam.id),
    [awayTeam.id]: getTeamColor(awayTeam.id),
  }

  // Aggregate per-player xT
  const { homePlayers: homeXt, awayPlayers: awayXt, maxXt } = useMemo(() => {
    if (!eventXt?.xt_events) return { homePlayers: [], awayPlayers: [], maxXt: 0 }

    const homeId = eventXt.home_team_id
    const awayId = eventXt.away_team_id

    const playerMap = {}
    eventXt.xt_events.forEach(e => {
      if (e.xt <= 0) return
      const pid = e.player_id
      if (!playerMap[pid]) {
        playerMap[pid] = { id: pid, name: e.player_name, team_id: e.team_id, totalXt: 0, count: 0 }
      }
      playerMap[pid].totalXt += e.xt
      playerMap[pid].count += 1
    })

    const players = Object.values(playerMap)
    const home = players.filter(p => p.team_id === homeId).sort((a, b) => b.totalXt - a.totalXt).slice(0, 10)
    const away = players.filter(p => p.team_id === awayId).sort((a, b) => b.totalXt - a.totalXt).slice(0, 10)
    const mx = Math.max(...home.map(p => p.totalXt), ...away.map(p => p.totalXt), 0.1)

    return { homePlayers: home, awayPlayers: away, maxXt: mx }
  }, [eventXt])

  // Aggregate per-player xG
  const { homeXg, awayXg, maxXg } = useMemo(() => {
    if (!shotXg?.shots) return { homeXg: [], awayXg: [], maxXg: 0 }

    const homeId = shotXg.home_team_id
    const awayId = shotXg.away_team_id

    const playerMap = {}
    shotXg.shots.forEach(s => {
      const pid = s.player_id
      if (!playerMap[pid]) {
        playerMap[pid] = { id: pid, name: s.player_name, team_id: s.team_id, totalXg: 0, goals: 0, shots: 0 }
      }
      playerMap[pid].totalXg += s.xg
      playerMap[pid].shots += 1
      if (s.is_goal) playerMap[pid].goals += 1
    })

    const players = Object.values(playerMap)
    const home = players.filter(p => p.team_id === homeId).sort((a, b) => b.totalXg - a.totalXg).slice(0, 10)
    const away = players.filter(p => p.team_id === awayId).sort((a, b) => b.totalXg - a.totalXg).slice(0, 10)
    const mx = Math.max(...home.map(p => p.totalXg), ...away.map(p => p.totalXg), 0.05)

    return { homeXg: home, awayXg: away, maxXg: mx }
  }, [shotXg])

  useEffect(() => {
    const hasXt = homeXt.length > 0 || awayXt.length > 0
    const hasXg = homeXg.length > 0 || awayXg.length > 0
    if (!svgRef.current || (!hasXt && !hasXg)) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const containerWidth = svgRef.current.parentElement?.clientWidth || 900
    const margin = { top: 8, right: 12, bottom: 8, left: 12 }
    const midGap = 40
    const nameWidth = 110
    const valueWidth = 40
    const halfWidth = (containerWidth - margin.left - margin.right - midGap) / 2
    const barMaxWidth = halfWidth - nameWidth - valueWidth - 4
    const barHeight = 22
    const barGap = 4
    const sectionGap = 32

    const xtRows = Math.max(homeXt.length, awayXt.length)
    const xgRows = Math.max(homeXg.length, awayXg.length)
    const xtSectionHeight = xtRows * (barHeight + barGap)
    const xgSectionHeight = xgRows * (barHeight + barGap)

    let totalHeight = margin.top + margin.bottom
    if (hasXt) totalHeight += xtSectionHeight + 20 // 20 for sub-header
    if (hasXt && hasXg) totalHeight += sectionGap
    if (hasXg) totalHeight += xgSectionHeight + 20

    svg.attr('width', containerWidth).attr('height', totalHeight)

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const homeId = eventXt?.home_team_id || shotXg?.home_team_id || homeTeam.id
    const awayId = eventXt?.away_team_id || shotXg?.away_team_id || awayTeam.id

    // Helper: render a section of bars
    function renderBars(homePlayers, awayPlayers, maxVal, yOffset, valueFn, formatFn) {
      const barScale = d3.scaleLinear().domain([0, maxVal]).range([0, barMaxWidth])

      // Home team: [value] [bar >>>>] [name |]
      homePlayers.forEach((p, i) => {
        const y = yOffset + i * (barHeight + barGap)
        const val = valueFn(p)
        const barW = barScale(val)
        const nameRightEdge = halfWidth
        const barRight = nameRightEdge - nameWidth
        const barLeft = barRight - barW

        g.append('rect')
          .attr('x', barLeft).attr('y', y)
          .attr('width', barW).attr('height', barHeight)
          .attr('fill', teamColors[homeId]).attr('opacity', 0.75).attr('rx', 2)

        g.append('text')
          .attr('x', nameRightEdge - 4).attr('y', y + barHeight / 2)
          .attr('dy', '0.35em').attr('text-anchor', 'end')
          .attr('font-size', 11).attr('font-weight', 500).attr('fill', '#444')
          .attr('font-family', "'Plus Jakarta Sans', sans-serif")
          .text(p.name)

        g.append('text')
          .attr('x', barLeft - 6).attr('y', y + barHeight / 2)
          .attr('dy', '0.35em').attr('text-anchor', 'end')
          .attr('font-size', 10).attr('font-weight', 600).attr('fill', teamColors[homeId])
          .attr('font-family', "'Plus Jakarta Sans', sans-serif")
          .text(formatFn(p))
      })

      // Away team: [| name] [>>>> bar] [value]
      const awayLeft = halfWidth + midGap

      awayPlayers.forEach((p, i) => {
        const y = yOffset + i * (barHeight + barGap)
        const val = valueFn(p)
        const barW = barScale(val)
        const barStart = awayLeft + nameWidth

        g.append('rect')
          .attr('x', barStart).attr('y', y)
          .attr('width', barW).attr('height', barHeight)
          .attr('fill', teamColors[awayId]).attr('opacity', 0.75).attr('rx', 2)

        g.append('text')
          .attr('x', awayLeft + 4).attr('y', y + barHeight / 2)
          .attr('dy', '0.35em').attr('text-anchor', 'start')
          .attr('font-size', 11).attr('font-weight', 500).attr('fill', '#444')
          .attr('font-family', "'Plus Jakarta Sans', sans-serif")
          .text(p.name)

        g.append('text')
          .attr('x', barStart + barW + 6).attr('y', y + barHeight / 2)
          .attr('dy', '0.35em').attr('text-anchor', 'start')
          .attr('font-size', 10).attr('font-weight', 600).attr('fill', teamColors[awayId])
          .attr('font-family', "'Plus Jakarta Sans', sans-serif")
          .text(formatFn(p))
      })
    }

    // Helper: render sub-header
    function renderSubHeader(label, yOffset) {
      g.append('line')
        .attr('x1', 0).attr('x2', containerWidth - margin.left - margin.right)
        .attr('y1', yOffset).attr('y2', yOffset)
        .attr('stroke', '#ddd9d3').attr('stroke-width', 1)

      g.append('text')
        .attr('x', (containerWidth - margin.left - margin.right) / 2)
        .attr('y', yOffset + 14)
        .attr('text-anchor', 'middle')
        .attr('font-size', 10).attr('font-weight', 700).attr('fill', '#999')
        .attr('letter-spacing', '0.08em')
        .attr('font-family', "'Plus Jakarta Sans', sans-serif")
        .text(label)
    }

    let currentY = 0

    // xT section
    if (hasXt) {
      renderSubHeader('EXPECTED THREAT (xT) -- PASS PROGRESSION', currentY)
      currentY += 20
      renderBars(homeXt, awayXt, maxXt, currentY, p => p.totalXt, p => p.totalXt.toFixed(2))
      currentY += xtSectionHeight
    }

    // xG section
    if (hasXg) {
      currentY += sectionGap / 2
      renderSubHeader('EXPECTED GOALS (xG)', currentY)
      currentY += 20
      renderBars(
        homeXg, awayXg, maxXg, currentY,
        p => p.totalXg,
        p => {
          const label = p.totalXg.toFixed(2)
          return p.goals > 0 ? `${label} (${p.goals}G)` : label
        }
      )
    }

  }, [homeXt, awayXt, maxXt, homeXg, awayXg, maxXg, metadata, eventXt, shotXg])

  if (!eventXt?.xt_events && !shotXg?.shots) return null

  return (
    <div>
      <div className="player-xt-header">
        <span className="player-xt-team-label" style={{ color: teamColors[homeTeam.id] }}>
          {homeTeam.name}
        </span>
        <span className="player-xt-title">Player Contributions</span>
        <span className="player-xt-team-label" style={{ color: teamColors[awayTeam.id] }}>
          {awayTeam.name}
        </span>
      </div>
      <svg ref={svgRef} className="player-xt-svg" />
    </div>
  )
}

export default PlayerXT
