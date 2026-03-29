import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import MomentumChart from './components/MomentumChart'
import CumulativeXG from './components/CumulativeXG'
import PlayerXT from './components/PlayerXT'
import Timeline from './components/Timeline'
import PitchCanvas from './components/PitchCanvas'
import MetricPanel, { TeamMetricPanel } from './components/MetricPanel'
import { computeRestDefenceScores, computeThreatScores } from './utils/restDefence'
import MatchStats from './components/MatchStats'
import Lineups from './components/Lineups'
import PhaseFilter from './components/PhaseFilter'
import useMatchData from './hooks/useMatchData'
import { MATCH_CATALOG, getMatchInfo, getTeamColor, getTeamBadge, formatMatchDate } from './utils/matchCatalog'
import './App.css'

const TAB_LABELS = ['Overview', 'Analysis']

function MatchSelector({ selectedMatch, onMatchChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const current = getMatchInfo(selectedMatch)

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div className="match-dropdown" ref={ref}>
      <button className="match-dropdown-trigger" onClick={() => setOpen(o => !o)}>
        {current && (
          <>
            <img src={getTeamBadge(current.homeTeam.id)} alt="" className="match-dd-badge" />
            <span className="match-dd-vs">vs</span>
            <img src={getTeamBadge(current.awayTeam.id)} alt="" className="match-dd-badge" />
            <span className="match-dd-date">{formatMatchDate(current.date)}</span>
          </>
        )}
        <svg className={`match-dd-chevron ${open ? 'open' : ''}`} width="10" height="6" viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </button>
      {open && (
        <div className="match-dropdown-menu">
          {MATCH_CATALOG.map(m => {
            const active = m.matchId === selectedMatch
            return (
              <button
                key={m.matchId}
                className={`match-dropdown-item ${active ? 'active' : ''}`}
                onClick={() => { onMatchChange(m.matchId); setOpen(false) }}
              >
                <img src={getTeamBadge(m.homeTeam.id)} alt="" className="match-dd-item-badge" />
                <div className="match-dd-item-info">
                  <span className="match-dd-item-teams">{m.homeTeam.name} vs {m.awayTeam.name}</span>
                  <span className="match-dd-item-meta">{m.competition} &middot; {formatMatchDate(m.date)} &middot; {m.result}</span>
                </div>
                <img src={getTeamBadge(m.awayTeam.id)} alt="" className="match-dd-item-badge" />
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

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
  const [selectedMatch, setSelectedMatch] = useState('J03WN1')
  const [activeTab, setActiveTab] = useState(1)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [phaseFilter, setPhaseFilter] = useState(new Set(['all']))
  const [selectedPhase, setSelectedPhase] = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [overlayMode, setOverlayMode] = useState('shape_graph')
  const [leftPanelOpen, setLeftPanelOpen] = useState(true)
  const [rightPanelOpen, setRightPanelOpen] = useState(true)

  const { matchData, loading, error } = useMatchData(selectedMatch)
  const matchInfo = getMatchInfo(selectedMatch)

  const currentFrameData = matchData?.frames?.[currentFrame] || null
  const currentTime = currentFrameData?.t || 0
  const goals = matchData?.metadata?.goals || []
  const teams = matchData?.metadata?.teams || []
  const homeTeam = teams[0] || { id: matchInfo?.homeTeam?.id || '', name: matchInfo?.homeTeam?.name || 'Home' }
  const awayTeam = teams[1] || { id: matchInfo?.awayTeam?.id || '', name: matchInfo?.awayTeam?.name || 'Away' }

  const homeColor = getTeamColor(homeTeam.id)
  const awayColor = getTeamColor(awayTeam.id)
  const homeBadge = homeTeam.badge || getTeamBadge(homeTeam.id)
  const awayBadge = awayTeam.badge || getTeamBadge(awayTeam.id)

  const handleMatchChange = useCallback((matchId) => {
    setSelectedMatch(matchId)
    setCurrentFrame(0)
    setSelectedPhase(null)
    setSelectedTeam(null)
    setIsPlaying(false)
    setPhaseFilter(new Set(['all']))
  }, [])

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

  const rdsScores = useMemo(() => {
    if (!homeTeam?.id || !awayTeam?.id) return { home: null, away: null }
    return computeRestDefenceScores(currentFrameData?.players, currentFrameData?.ball, [homeTeam.id, awayTeam.id])
  }, [currentFrameData, homeTeam?.id, awayTeam?.id])

  const otiScores = useMemo(() => {
    if (!homeTeam?.id || !awayTeam?.id) return { home: null, away: null }
    return computeThreatScores(currentFrameData?.players, currentFrameData?.ball, [homeTeam.id, awayTeam.id])
  }, [currentFrameData, homeTeam?.id, awayTeam?.id])

  useEffect(() => {
    document.documentElement.style.setProperty('--home-color', homeColor)
    document.documentElement.style.setProperty('--away-color', awayColor)
  }, [homeColor, awayColor])

  const currentVoronoiData = matchData?.voronoi?.find(v =>
    v.frame_id === currentFrameData?.frame_id
  ) || null

  const dataReady = !loading && !error && matchData

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
        <div className="nav-actions">
          <MatchSelector selectedMatch={selectedMatch} onMatchChange={handleMatchChange} />
        </div>
      </nav>

      {/* ── Score Banner ── */}
      <div className="score-banner">
        <div className="score-row">
          <div className="score-team-block home">
            <span className="score-team-pill home">{homeTeam.name}</span>
            {homeBadge && <img src={homeBadge} alt="" className="score-badge" />}
          </div>
          <span className="score-result">
            {dataReady ? `${liveScore.home} - ${liveScore.away}` : (matchInfo?.result || '- - -')}
          </span>
          <div className="score-team-block away">
            <span className="score-team-pill away">{awayTeam.name}</span>
            {awayBadge && <img src={awayBadge} alt="" className="score-badge" />}
          </div>
        </div>
        <div className="score-meta">
          <span className="score-competition">{matchInfo?.competition || 'Bundesliga'}</span>
          {matchInfo?.date && (
            <span className="score-match-date">{formatMatchDate(matchInfo.date)}</span>
          )}
          {dataReady && (
            <span className="score-date">
              {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')}
            </span>
          )}
        </div>
      </div>

      {/* ── Loading / Error states ── */}
      {loading && (
        <div className="data-status">
          <div className="loading-spinner">Loading match data...</div>
        </div>
      )}
      {!loading && (error || !matchData) && (
        <div className="data-status">
          <div className="data-unavailable">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>Match data not yet available. Run the pipeline for this match first.</span>
          </div>
        </div>
      )}

      {/* ═══ TAB 0 : Overview ═══ */}
      {dataReady && activeTab === 0 && (
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

          <Collapsible title="Player Contributions" defaultOpen={true}>
            <div className="dash-card" style={{ marginTop: 8 }}>
              <PlayerXT
                eventXt={matchData.eventXt}
                shotXg={matchData.shotXg}
                metadata={matchData.metadata}
              />
            </div>
          </Collapsible>
        </div>
      )}

      {/* ═══ TAB 1 : Analysis (main course) ═══ */}
      {dataReady && activeTab === 1 && (
        <div className="analysis-layout">

          {/* Left side panel - Home team */}
          <aside className={`side-panel side-panel-left ${leftPanelOpen ? 'open' : ''}`}>
            <div className="side-panel-inner">
              <div className="side-panel-collapse-row">
                <button className="side-panel-collapse-btn" onClick={() => setLeftPanelOpen(false)} aria-label="Collapse" style={{ color: homeColor }}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M10.3 2.3a1 1 0 011.4 1.4L7.4 8l4.3 4.3a1 1 0 01-1.4 1.4l-5-5a1 1 0 010-1.4l5-5z"/></svg>
                </button>
              </div>
              <TeamMetricPanel
                team={homeTeam}
                teamColor={homeColor}
                phases={visiblePhases}
                currentTime={currentTime}
                rdsScore={rdsScores?.home}
                otiScore={otiScores?.home}
              />
            </div>
            <button className="side-panel-tab" onClick={() => setLeftPanelOpen(true)} aria-label="Expand" style={{ color: homeColor }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M5.7 2.3a1 1 0 00-1.4 1.4L8.6 8l-4.3 4.3a1 1 0 001.4 1.4l5-5a1 1 0 000-1.4l-5-5z"/></svg>
            </button>
          </aside>

          {/* Main content */}
          <div className="analysis-main">

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
                {(!selectedTeam ? teamIds : [selectedTeam]).map((teamId, idx, arr) => (
                  <Timeline
                    key={teamId}
                    teamName={teamNameMap[teamId]}
                    phases={filteredByType?.filter(p => p.team === teamId)}
                    currentTime={currentTime}
                    duration={matchDuration}
                    onTimeChange={handleTimeChange}
                    selectedPhase={selectedPhase}
                    onPhaseSelect={setSelectedPhase}
                    showLegend={idx === arr.length - 1}
                  />
                ))}
              </div>
            </Collapsible>

            {/* Pitch View */}
            <div className="dash-card pitch-card">
              <div className="card-header">
                <h2 className="card-title">Pitch View</h2>
                <div className="sub-tabs">
                  {[
                    { value: 'shape_graph', label: 'Shape Graph' },
                    { value: 'convex_hull', label: 'Pitch Control' },
                    { value: 'formation_lines', label: 'Formation Lines' },
                    { value: 'none', label: 'Clean' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      className={`sub-tab ${overlayMode === opt.value ? 'active' : ''}`}
                      onClick={() => setOverlayMode(opt.value)}
                    >
                      {opt.label}
                      {opt.value === 'formation_lines' && <span className="beta-tag">BETA</span>}
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

            {/* Game Momentum */}
            <Collapsible title="Game Momentum" defaultOpen={true}>
              <div className="dash-card" style={{ marginTop: 8 }}>
                <MomentumChart
                  eventXt={matchData.eventXt}
                  shotXg={matchData.shotXg}
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

          </div>

          {/* Right side panel - Away team */}
          <aside className={`side-panel side-panel-right ${rightPanelOpen ? 'open' : ''}`}>
            <div className="side-panel-inner">
              <div className="side-panel-collapse-row">
                <button className="side-panel-collapse-btn" onClick={() => setRightPanelOpen(false)} aria-label="Collapse" style={{ color: awayColor }}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M5.7 2.3a1 1 0 00-1.4 1.4L8.6 8l-4.3 4.3a1 1 0 001.4 1.4l5-5a1 1 0 000-1.4l-5-5z"/></svg>
                </button>
              </div>
              <TeamMetricPanel
                team={awayTeam}
                teamColor={awayColor}
                phases={visiblePhases}
                currentTime={currentTime}
                rdsScore={rdsScores?.away}
                otiScore={otiScores?.away}
              />
            </div>
            <button className="side-panel-tab" onClick={() => setRightPanelOpen(true)} aria-label="Expand" style={{ color: awayColor }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M10.3 2.3a1 1 0 011.4 1.4L7.4 8l4.3 4.3a1 1 0 01-1.4 1.4l-5-5a1 1 0 010-1.4l5-5z"/></svg>
            </button>
          </aside>

        </div>
      )}

      {/* ═══ TAB 2 : Metrics (hidden, no tab button) ═══ */}
    </div>
  )
}

export default App
