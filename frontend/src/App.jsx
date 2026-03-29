import { useState, useEffect, useMemo, useCallback } from 'react'
import ThreatTimeline from './components/ThreatTimeline'
import CumulativeXG from './components/CumulativeXG'
import Timeline from './components/Timeline'
import PitchCanvas from './components/PitchCanvas'
import MetricPanel from './components/MetricPanel'
import MatchStats from './components/MatchStats'
import Lineups from './components/Lineups'
import PhaseFilter from './components/PhaseFilter'
import useMatchData from './hooks/useMatchData'
import './App.css'

const TAB_LABELS = ['Overview', 'Analysis', 'Metrics']

function Collapsible({ title, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="collapsible-section">
      <div className="collapsible-header" onClick={() => setOpen(o => !o)}>
        <span className="collapsible-title">{title}</span>
        <span className={`collapsible-chevron ${open ? 'open' : ''}`}>&#9662;</span>
      </div>
      <div className={`collapsible-body ${open ? 'expanded' : 'collapsed'}`}>
        {children}
      </div>
    </div>
  )
}

function App() {
  const [selectedMatch] = useState('J03WN1')
  const [activeTab, setActiveTab] = useState(1)
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

  const teamNameMap = useMemo(() => {
    const map = {}
    teams.forEach(t => { map[t.id] = t.name })
    return map
  }, [teams])

  const teamIds = useMemo(() => teams.map(t => t.id), [teams])

  const matchDuration = useMemo(() =>
    matchData?.metadata?.duration
    || matchData?.frames?.[matchData.frames.length - 1]?.t
    || 90 * 60
  , [matchData])

  const handleTimeChange = useCallback((time) => {
    if (!matchData?.frames) return
    const frameIndex = matchData.frames.findIndex(f => f.t >= time)
    setCurrentFrame(frameIndex >= 0 ? frameIndex : 0)
  }, [matchData])

  const filteredByType = useMemo(() =>
    phaseFilter.has('all')
      ? matchData?.phases
      : matchData?.phases?.filter(p => phaseFilter.has(p.type))
  , [matchData?.phases, phaseFilter])

  const visiblePhases = useMemo(() =>
    selectedTeam
      ? filteredByType?.filter(p => p.team === selectedTeam)
      : filteredByType
  , [filteredByType, selectedTeam])

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Loading match data...</div>
      </div>
    )
  }

  if (error || !matchData) {
    return (
      <div className="error-container">
        <div className="error-message">{error || 'No match data available'}</div>
      </div>
    )
  }

  const currentVoronoiData = matchData.voronoi?.find(v =>
    v.frame_id === currentFrameData?.frame_id
  ) || null

  return (
    <div className="dashboard-shell">

      {/* ── Top Navigation ── */}
      <nav className="top-nav">
        <span className="nav-brand">PhaseViz</span>
        <div className="nav-tabs">
          {TAB_LABELS.map((label, i) => (
            <button
              key={label}
              className={`nav-tab ${activeTab === i ? 'active' : ''}`}
              onClick={() => setActiveTab(i)}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="nav-actions" />
      </nav>

      {/* ── Score Banner ── */}
      <div className="score-banner">
        <div className="score-row">
          <div className="score-team-block home">
            <span className="score-team-pill home">{homeTeam.name}</span>
            {homeTeam.badge && <img src={homeTeam.badge} alt="" className="score-badge" />}
          </div>
          <span className="score-result">{liveScore.home} - {liveScore.away}</span>
          <div className="score-team-block away">
            <span className="score-team-pill away">{awayTeam.name}</span>
            {awayTeam.badge && <img src={awayTeam.badge} alt="" className="score-badge" />}
          </div>
        </div>
        <div className="score-meta">
          <span className="score-competition">Bundesliga</span>
          <span className="score-date">
            {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')}
          </span>
        </div>
      </div>

      {/* ═══ TAB 0 : Overview ═══ */}
      {activeTab === 0 && (
        <div className="tab-content">
          <div className="dash-card">
            <div className="card-header">
              <h2 className="card-title">Match Stats</h2>
            </div>
            <MatchStats
              matchStats={matchData.metadata?.match_stats}
              homeTeam={homeTeam}
              awayTeam={awayTeam}
            />
          </div>

          <div className="dash-card">
            <div className="card-header">
              <h2 className="card-title">Lineups & Player Stats</h2>
            </div>
            <Lineups
              playerStats={matchData.metadata?.player_stats}
              teams={teams}
            />
          </div>
        </div>
      )}

      {/* ═══ TAB 1 : Analysis (main course) ═══ */}
      {activeTab === 1 && (
        <div className="tab-content">

          {/* Phase Detection */}
          <Collapsible title="Phase Detection" defaultOpen={true}>
            <div className="controls-row" style={{ marginTop: 8 }}>
              <PhaseFilter phaseFilter={phaseFilter} setPhaseFilter={setPhaseFilter} />
              <div className="team-selector">
                <h3>Team View</h3>
                <div className="team-selector-buttons">
                  <button className={`team-btn ${!selectedTeam ? 'active' : ''}`} onClick={() => setSelectedTeam(null)}>Both</button>
                  {teams.map(t => (
                    <button key={t.id} className={`team-btn ${selectedTeam === t.id ? 'active' : ''}`} onClick={() => setSelectedTeam(t.id)}>{t.name}</button>
                  ))}
                </div>
              </div>
            </div>
            <div className="dash-card" style={{ marginTop: 8 }}>
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
            </div>
          </Collapsible>

          {/* Pitch View - full width, centered */}
          <div className="dash-card pitch-card">
            <div className="card-header">
              <h2 className="card-title">Pitch View</h2>
              <div className="sub-tabs">
                {[
                  { value: 'shape_graph', label: 'Shape Graph' },
                  { value: 'convex_hull', label: 'Pitch Control' },
                  { value: 'none', label: 'Clean' },
                ].map(opt => (
                  <button
                    key={opt.value}
                    className={`sub-tab ${overlayMode === opt.value ? 'active' : ''}`}
                    onClick={() => setOverlayMode(opt.value)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <PitchCanvas
              frame={currentFrameData}
              voronoi={currentVoronoiData}
              selectedPhase={selectedPhase}
              overlayMode={overlayMode}
              metadata={matchData.metadata}
            />
            <div className="playback-controls">
              <div className="speed-selector">
                <span className="speed-label">Speed</span>
                <div className="speed-options">
                  {[0.5, 1, 2, 4].map(s => (
                    <button
                      key={s}
                      className={`speed-btn ${playbackSpeed === s ? 'active' : ''}`}
                      onClick={() => setPlaybackSpeed(s)}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              </div>
              <button className="play-pause-btn" onClick={() => setIsPlaying(!isPlaying)} aria-label={isPlaying ? 'Pause' : 'Play'}>
                {isPlaying ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <rect x="3" y="2" width="4" height="12" rx="1" />
                    <rect x="9" y="2" width="4" height="12" rx="1" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M4 2.5v11a.5.5 0 00.77.42l9-5.5a.5.5 0 000-.84l-9-5.5A.5.5 0 004 2.5z" />
                  </svg>
                )}
              </button>
              <span className="playback-time">
                {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')}
              </span>
            </div>
          </div>

          {/* Threat Timeline */}
          <Collapsible title="Threat Timeline" defaultOpen={true}>
            <div className="dash-card" style={{ marginTop: 8 }}>
              <ThreatTimeline
                phases={matchData.phases}
                metadata={matchData.metadata}
                goals={goals}
                currentTime={currentTime}
                duration={matchDuration}
                onTimeChange={handleTimeChange}
              />
            </div>
          </Collapsible>

          {/* Cumulative xG */}
          <Collapsible title="Cumulative xG" defaultOpen={true}>
            <div className="dash-card" style={{ marginTop: 8 }}>
              <CumulativeXG
                shotXg={matchData.shotXg}
                metadata={matchData.metadata}
                currentTime={currentTime}
                duration={matchDuration}
                onTimeChange={handleTimeChange}
              />
            </div>
          </Collapsible>

          {/* Match Metrics - collapsible */}
          <Collapsible title="Match Metrics" defaultOpen={false}>
            <div className="dash-card" style={{ marginTop: 8 }}>
              <MetricPanel
                phases={visiblePhases}
                currentPhase={visiblePhases?.find(p =>
                  currentTime >= p.start && currentTime <= p.end
                )}
                teamNameMap={teamNameMap}
              />
            </div>
          </Collapsible>
        </div>
      )}

      {/* ═══ TAB 2 : Metrics ═══ */}
      {activeTab === 2 && (
        <div className="tab-content">
          <div className="dash-card">
            <div className="card-header">
              <h2 className="card-title">Match Metrics</h2>
            </div>
            <MetricPanel
              phases={visiblePhases}
              currentPhase={visiblePhases?.find(p =>
                currentTime >= p.start && currentTime <= p.end
              )}
              teamNameMap={teamNameMap}
              fullView={true}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default App
