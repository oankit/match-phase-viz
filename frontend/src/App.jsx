import { useState, useEffect, useMemo } from 'react'
import ThreatTimeline from './components/ThreatTimeline'
import Timeline from './components/Timeline'
import PitchCanvas from './components/PitchCanvas'
import MetricPanel from './components/MetricPanel'

import MatchStats from './components/MatchStats'
import Lineups from './components/Lineups'
import PhaseFilter from './components/PhaseFilter'
import useMatchData from './hooks/useMatchData'
import './App.css'

const TEAM_COLORS = {
  'DFL-CLU-00000S': '#C8102E',
  'DFL-CLU-00000B': '#6CABDD',
}

function App() {
  const [selectedMatch] = useState('J03WN1')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [phaseFilter, setPhaseFilter] = useState(new Set(['all']))
  const [selectedPhase, setSelectedPhase] = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [overlayMode, setOverlayMode] = useState('shape_graph')

  const { matchData, loading, error } = useMatchData(selectedMatch)

  const currentFrameData = matchData?.frames?.[currentFrame] || null
  const currentTime = currentFrameData?.t || 0
  const goals = matchData?.metadata?.goals || []
  const teams = matchData?.metadata?.teams || []
  const homeTeam = teams[0] || { id: '', name: 'Home' }
  const awayTeam = teams[1] || { id: '', name: 'Away' }

  useEffect(() => {
    if (isPlaying && matchData?.frames) {
      const interval = setInterval(() => {
        setCurrentFrame(prev => {
          const next = prev + 1
          return next >= matchData.frames.length ? 0 : next
        })
      }, 250 / playbackSpeed)
      return () => clearInterval(interval)
    }
  }, [isPlaying, playbackSpeed, matchData])

  const liveScore = useMemo(() => {
    const home = goals.filter(g => g.team_id === homeTeam.id && g.match_seconds <= currentTime).length
    const away = goals.filter(g => g.team_id === awayTeam.id && g.match_seconds <= currentTime).length
    return { home, away }
  }, [goals, currentTime, homeTeam.id, awayTeam.id])

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Loading match data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">Error: {error}</div>
      </div>
    )
  }

  if (!matchData) {
    return (
      <div className="error-container">
        <div className="error-message">No match data available</div>
      </div>
    )
  }

  const currentVoronoiData = matchData.voronoi?.find(v =>
    v.frame_id === currentFrameData?.frame_id
  ) || null

  const teamNameMap = {}
  teams.forEach(t => { teamNameMap[t.id] = t.name })
  const teamIds = teams.map(t => t.id)

  const matchDuration = matchData.metadata?.duration
    || matchData.frames?.[matchData.frames.length - 1]?.t
    || 90 * 60

  const handleTimeChange = (time) => {
    const frameIndex = matchData.frames.findIndex(f => f.t >= time)
    setCurrentFrame(frameIndex >= 0 ? frameIndex : 0)
  }

  const filteredByType = phaseFilter.has('all')
    ? matchData.phases
    : matchData.phases?.filter(p => phaseFilter.has(p.type))

  const visiblePhases = selectedTeam
    ? filteredByType?.filter(p => p.team === selectedTeam)
    : filteredByType

  return (
    <div className="dashboard-container">

      {/* Score Header */}
      <header className="score-header">
        <div className="teams-row">
          <div className="team-block home">
            <span className="team-name">{homeTeam.name}</span>
            {homeTeam.badge && (
              <img src={homeTeam.badge} alt={homeTeam.name} className="team-badge" />
            )}
          </div>

          <div className="score-block">
            <span className="score">{liveScore.home} - {liveScore.away}</span>
            <span className="match-meta">Bundesliga</span>
          </div>

          <div className="team-block away">
            {awayTeam.badge && (
              <img src={awayTeam.badge} alt={awayTeam.name} className="team-badge" />
            )}
            <span className="team-name">{awayTeam.name}</span>
          </div>
        </div>

        <div className="match-time-bar">
          <span className="time-display">
            {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')}
          </span>
        </div>
      </header>

      {/* Threat Timeline */}
      <ThreatTimeline
        phases={matchData.phases}
        metadata={matchData.metadata}
        goals={goals}
        currentTime={currentTime}
        duration={matchDuration}
        onTimeChange={handleTimeChange}
      />

      {/* Match Stats */}
      <MatchStats
        matchStats={matchData.metadata?.match_stats}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
      />

      {/* Phase Timelines */}
      {(!selectedTeam ? teamIds : [selectedTeam]).map(teamId => (
        <Timeline
          key={teamId}
          teamName={teamNameMap[teamId]}
          phases={filteredByType?.filter(p => p.team === teamId)}
          currentTime={currentTime}
          duration={matchDuration}
          onTimeChange={handleTimeChange}
          selectedPhase={selectedPhase}
          onPhaseSelect={setSelectedPhase}
        />
      ))}

      <hr className="section-divider" />

      {/* Controls */}
      <div className="controls-row">
        <PhaseFilter
          phaseFilter={phaseFilter}
          setPhaseFilter={setPhaseFilter}
        />
        <div className="team-selector">
          <h3>Team View</h3>
          <div className="team-selector-buttons">
            <button
              className={`team-btn ${!selectedTeam ? 'active' : ''}`}
              onClick={() => setSelectedTeam(null)}
            >
              Both
            </button>
            {teams.map(t => (
              <button
                key={t.id}
                className={`team-btn ${selectedTeam === t.id ? 'active' : ''}`}
                onClick={() => setSelectedTeam(t.id)}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <hr className="section-divider" />

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        <div className="visualization-panel">
          <div className="visualization-panel-title">Pitch View</div>
          <PitchCanvas
            frame={currentFrameData}
            voronoi={currentVoronoiData}
            selectedPhase={selectedPhase}
            overlayMode={overlayMode}
            metadata={matchData.metadata}
          />
          <div className="playback-controls">
            <button onClick={() => setIsPlaying(!isPlaying)}>
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <label>
              Speed:
              <select value={playbackSpeed} onChange={e => setPlaybackSpeed(Number(e.target.value))}>
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={4}>4x</option>
              </select>
            </label>
            <label>
              Overlay:
              <select value={overlayMode} onChange={e => setOverlayMode(e.target.value)}>
                <option value="none">None</option>
                <option value="shape_graph">Shape Graph</option>
                <option value="convex_hull">Pitch Control</option>
              </select>
            </label>
          </div>
        </div>

        <div className="metrics-panel">
          <MetricPanel
            phases={visiblePhases}
            currentPhase={visiblePhases?.find(p =>
              currentTime >= p.start && currentTime <= p.end
            )}
            teamNameMap={teamNameMap}
          />
        </div>
      </div>

      {/* Lineups */}
      <hr className="section-divider" />
      <Lineups
        playerStats={matchData.metadata?.player_stats}
        teams={teams}
      />
    </div>
  )
}

export default App
