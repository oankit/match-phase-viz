import { useMemo } from 'react'
import './Lineups.css'

const POSITION_ORDER = [
  'GK', 'RB', 'RCB', 'CB', 'LCB', 'LB',
  'RDM', 'LDM', 'CM', 'RCM', 'LCM', 'RM', 'LM',
  'CAM', 'RW', 'LW', 'ST',
]

function positionSortKey(abbr) {
  const idx = POSITION_ORDER.indexOf(abbr)
  return idx >= 0 ? idx : 99
}

function StatIcon({ type, title }) {
  const icons = {
    goal: (
      <svg viewBox="0 0 20 20" width="18" height="18" title={title}>
        <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="10" cy="10" r="3" fill="currentColor" />
      </svg>
    ),
    assist: (
      <svg viewBox="0 0 20 20" width="18" height="18" title={title}>
        <text x="10" y="15" textAnchor="middle" fontSize="16" fontWeight="700" fill="currentColor">A</text>
      </svg>
    ),
    progressive_passes: (
      <svg viewBox="0 0 20 20" width="18" height="18" title={title}>
        <line x1="10" y1="16" x2="10" y2="4" stroke="currentColor" strokeWidth="2" />
        <polyline points="5,9 10,4 15,9" fill="none" stroke="currentColor" strokeWidth="2" />
        <line x1="6" y1="16" x2="14" y2="16" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
    defensive_actions: (
      <svg viewBox="0 0 20 20" width="18" height="18" title={title}>
        <path d="M10 2 L17 6 L17 12 Q17 17 10 19 Q3 17 3 12 L3 6 Z"
              fill="none" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
    touches: (
      <svg viewBox="0 0 20 20" width="18" height="18" title={title}>
        <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="10" cy="10" r="3" fill="none" stroke="currentColor" strokeWidth="1" />
      </svg>
    ),
    xg: (
      <svg viewBox="0 0 20 20" width="18" height="18" title={title}>
        <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <line x1="10" y1="3" x2="10" y2="17" stroke="currentColor" strokeWidth="1" />
        <line x1="3" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="1" />
      </svg>
    ),
  }
  return <span className="stat-icon" title={title}>{icons[type]}</span>
}

function findLeaders(players) {
  if (!players || players.length === 0) return {}

  const metrics = ['progressive_passes', 'defensive_actions', 'touches']
  const leaders = {}

  for (const metric of metrics) {
    const maxVal = Math.max(...players.map(p => p[metric] || 0))
    if (maxVal > 0) {
      leaders[metric] = players
        .filter(p => (p[metric] || 0) === maxVal)
        .map(p => p.id)
    }
  }

  return leaders
}

function TeamLineup({ players, teamName, teamColor, isHome }) {
  const leaders = useMemo(() => findLeaders(players), [players])

  const sorted = useMemo(() => {
    if (!players) return []
    const starters = players.filter(p => p.is_starter)
      .sort((a, b) => positionSortKey(a.position_abbr) - positionSortKey(b.position_abbr))
    const subs = players.filter(p => !p.is_starter && p.minutes > 0)
      .sort((a, b) => (a.sub_on || 99) - (b.sub_on || 99))
    return [...starters, ...subs]
  }, [players])

  if (!sorted.length) return null

  return (
    <div className="team-lineup">
      <div className="lineup-header" style={{ borderBottomColor: teamColor }}>
        <span className="lineup-team-name">{teamName}</span>
      </div>
      <table className="lineup-table">
        <thead>
          <tr>
            <th></th>
            <th className="col-jersey">#</th>
            <th className="col-pos">Pos</th>
            <th className="col-name">Player</th>
            <th className="col-mins">Min</th>
            <th className="col-stats">Key Stats</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(player => {
            const isSub = !player.is_starter
            const statIcons = []

            if (player.goals > 0) {
              for (let i = 0; i < player.goals; i++) {
                statIcons.push(<StatIcon key={`g${i}`} type="goal" title="Goal" />)
              }
            }
            if (player.assists > 0) {
              for (let i = 0; i < player.assists; i++) {
                statIcons.push(<StatIcon key={`a${i}`} type="assist" title="Assist" />)
              }
            }
            if (leaders.progressive_passes?.includes(player.id)) {
              statIcons.push(<StatIcon key="pp" type="progressive_passes" title={`Progressive passes: ${player.progressive_passes}`} />)
            }
            if (leaders.defensive_actions?.includes(player.id)) {
              statIcons.push(<StatIcon key="da" type="defensive_actions" title={`Defensive actions: ${player.defensive_actions}`} />)
            }
            if (leaders.touches?.includes(player.id)) {
              statIcons.push(<StatIcon key="t" type="touches" title={`Touches: ${player.touches}`} />)
            }
            if (player.xg > 0.05) {
              statIcons.push(<StatIcon key="xg" type="xg" title={`xG: ${player.xg.toFixed(2)}`} />)
            }

            return (
              <tr key={player.id} className={isSub ? 'sub-player' : ''}>
                <td className="col-sub-marker">
                  {isSub && <span className="sub-arrow" style={{ color: teamColor }}>&#9650;</span>}
                  {player.sub_off && <span className="sub-arrow off">&#9660;</span>}
                </td>
                <td className="col-jersey">{player.jersey_no || ''}</td>
                <td className="col-pos">{player.position_abbr}</td>
                <td className="col-name">{player.name}</td>
                <td className="col-mins">{player.minutes}'</td>
                <td className="col-stats" style={{ color: teamColor }}>
                  {statIcons}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function Lineups({ playerStats, teams }) {
  const teamGroups = useMemo(() => {
    if (!playerStats || !teams || teams.length < 2) return null

    const nameMap = {}
    for (const team of teams) {
      if (team.players) {
        for (const p of team.players) {
          nameMap[p.id] = p.name
        }
      }
    }

    const fixed = playerStats.map(p => ({
      ...p,
      name: nameMap[p.id] || p.name,
    }))

    const home = fixed.filter(p => p.team_id === teams[0].id)
    const away = fixed.filter(p => p.team_id === teams[1].id)
    return { home, away }
  }, [playerStats, teams])

  if (!teamGroups) return null

  return (
    <div className="lineups-panel">
      <div className="lineups-grid">
        <TeamLineup
          players={teamGroups.home}
          teamName={teams[0].name}
          teamColor="#C8102E"
          isHome={true}
        />
        <TeamLineup
          players={teamGroups.away}
          teamName={teams[1].name}
          teamColor="#2563EB"
          isHome={false}
        />
      </div>
    </div>
  )
}
