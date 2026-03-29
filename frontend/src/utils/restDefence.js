/**
 * Rest Defence Score (RDS) and Opponent Threat Index (OTI)
 *
 * Based on:
 *   [1] Bauer & Anzer (2021) - counterpressing features
 *   [2] Spearman (2018) - pitch control model
 *   [3] Alai - rest-defense vulnerability framework
 *
 * RDS = 0.40*S_num + 0.30*S_comp + 0.30*S_ctrl   (0-100)
 * OTI = 0.30*S_goal + 0.25*O_num + 0.30*D_space + 0.15*M_kin   (0-100)
 *
 * S_ctrl and D_space use a lightweight reach-time grid computed from
 * player positions, since the pipeline's control_grid only covers
 * the attacking team's convex hull and not the full pitch.
 */

const PITCH_W = 105 // metres
const PITCH_H = 68
const MAX_SPEED_NORM = 0.076 // ~8 m/s in normalized coords

// --------------------------------------------------------------------------
//  GEOMETRY HELPERS
// --------------------------------------------------------------------------

function getDefendingSide(teamPlayers) {
  if (teamPlayers.length === 0) return 'left'
  const cx = teamPlayers.reduce((s, p) => s + p.x, 0) / teamPlayers.length
  return cx < 0.5 ? 'left' : 'right'
}

function convexHullArea(points) {
  if (points.length < 3) return 0
  const hull = convexHull2D(points)
  if (hull.length < 3) return 0
  let area = 0
  for (let i = 0; i < hull.length; i++) {
    const j = (i + 1) % hull.length
    area += hull[i][0] * hull[j][1]
    area -= hull[j][0] * hull[i][1]
  }
  return Math.abs(area) / 2
}

function convexHull2D(points) {
  const pts = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1])
  if (pts.length <= 2) return pts
  const cross = (o, a, b) =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
  const lower = []
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0)
      lower.pop()
    lower.push(p)
  }
  const upper = []
  for (let i = pts.length - 1; i >= 0; i--) {
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], pts[i]) <= 0)
      upper.pop()
    upper.push(pts[i])
  }
  lower.pop()
  upper.pop()
  return lower.concat(upper)
}

/**
 * Generate a coarse reach-time grid over a rectangular zone and determine
 * which team controls each cell (nearest player by Euclidean distance).
 *
 * Returns per-cell: { teamId, reachTime, isCentral }
 */
function computeZoneControl(allPlayers, xMin, xMax, cols, rows) {
  const cells = []
  const dx = (xMax - xMin) / (cols - 1 || 1)
  const dy = 1.0 / (rows - 1 || 1)

  for (let r = 0; r < rows; r++) {
    const gy = dy * r
    for (let c = 0; c < cols; c++) {
      const gx = xMin + dx * c
      let minDist = Infinity
      let nearestTeam = null

      for (const p of allPlayers) {
        const ddx = (p.x - gx) * PITCH_W
        const ddy = (p.y - gy) * PITCH_H
        const d = Math.sqrt(ddx * ddx + ddy * ddy)
        if (d < minDist) {
          minDist = d
          nearestTeam = p.team
        }
      }

      cells.push({
        x: gx,
        y: gy,
        teamId: nearestTeam,
        reachTime: minDist / 8.0, // 8 m/s max sprint
        isCentral: gy > 0.25 && gy < 0.75,
      })
    }
  }
  return cells
}

// --------------------------------------------------------------------------
//  REST DEFENCE SCORE (RDS)
// --------------------------------------------------------------------------

/**
 * Component A: Numerical Balance (S_num, 40%)
 * Ratio of defenders in rest-def unit to opponent outlets.
 * Both are players between the ball and the defending team's goal.
 */
function computeNumericalBalance(defPlayers, oppPlayers, ballX, defSide) {
  const isBetweenBallAndGoal = defSide === 'left'
    ? (px) => px < ballX
    : (px) => px > ballX

  const defBehind = defPlayers.filter(p => isBetweenBallAndGoal(p.x)).length
  const oppOutlets = oppPlayers.filter(p => isBetweenBallAndGoal(p.x)).length

  const eps = 0.5
  const ratio = defBehind / (oppOutlets + eps)
  // ratio > 1.5 is stable; cap contribution at ratio = 3
  return Math.min(ratio / 3.0, 1.0)
}

/**
 * Component B: Spatial Compactness (S_comp, 30%)
 * Inverse of convex hull area of the rest-defence unit.
 */
function computeSpatialCompactness(defPlayers, ballX, defSide) {
  const isBetweenBallAndGoal = defSide === 'left'
    ? (px) => px < ballX
    : (px) => px > ballX

  const restDefUnit = defPlayers.filter(p => isBetweenBallAndGoal(p.x))
  if (restDefUnit.length < 3) {
    return restDefUnit.length >= 2 ? 0.3 : 0.0
  }

  const area = convexHullArea(restDefUnit.map(p => [p.x, p.y]))
  // Normalized coords: ideal compact area ~0.03, stretched ~0.15
  const idealArea = 0.03
  const maxArea = 0.15
  if (area <= idealArea) return 1.0
  if (area >= maxArea) return 0.0
  return 1.0 - (area - idealArea) / (maxArea - idealArea)
}

/**
 * Component C: Pitch Control Dominance (S_ctrl, 30%)
 * Computed from player positions via a coarse 8x5 reach-time grid
 * over the defending team's third (vulnerable zone).
 * Includes an outlet penalty when opponents control central cells.
 */
function computePitchControlDominance(allPlayers, defTeamId, defSide) {
  const xMin = defSide === 'left' ? 0.0 : 0.67
  const xMax = defSide === 'left' ? 0.33 : 1.0

  const cells = computeZoneControl(allPlayers, xMin, xMax, 8, 5)
  if (cells.length === 0) return 0.5

  let defControl = 0
  let oppControl = 0
  let outletPenalty = 0

  cells.forEach(cell => {
    const weight = cell.isCentral ? 1.5 : 1.0
    if (cell.teamId === defTeamId) {
      defControl += weight
    } else {
      oppControl += weight
      // Outlet penalty: opponent controls a central cell in the vulnerable zone
      if (cell.isCentral) outletPenalty += 0.15
    }
  })

  const total = defControl + oppControl
  if (total === 0) return 0.5
  const raw = defControl / total
  return Math.max(0, Math.min(1, raw - Math.min(outletPenalty, 0.3)))
}

function computeSingleRDS(defPlayers, oppPlayers, allPlayers, ballX, defTeamId, defSide) {
  const sNum = computeNumericalBalance(defPlayers, oppPlayers, ballX, defSide)
  const sComp = computeSpatialCompactness(defPlayers, ballX, defSide)
  const sCtrl = computePitchControlDominance(allPlayers, defTeamId, defSide)

  const score = Math.round(sNum * 40 + sComp * 30 + sCtrl * 30)
  return {
    score: Math.max(0, Math.min(100, score)),
    label: rdsLabel(score),
  }
}

function rdsLabel(score) {
  if (score >= 80) return 'Excellent'
  if (score >= 65) return 'Good'
  if (score >= 50) return 'Fair'
  if (score >= 35) return 'Poor'
  return 'Critical'
}

// --------------------------------------------------------------------------
//  OPPONENT THREAT INDEX (OTI)
// --------------------------------------------------------------------------

/**
 * Component 1: Spatial Threat (S_goal, 30%)
 * cos(theta_j) / d_j^2 for each opponent in the attacking half.
 * theta_j = angle subtended by the goal from player j's position.
 */
function computeSpatialThreat(oppPlayers, goalCoords, attackSide) {
  const inAttHalf = attackSide === 'right'
    ? (px) => px > 0.5
    : (px) => px < 0.5

  let threat = 0
  let count = 0

  oppPlayers.forEach(p => {
    if (!inAttHalf(p.x)) return

    const dx = (p.x - goalCoords.x) * PITCH_W
    const dy = (p.y - goalCoords.y) * PITCH_H
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist < 1) { threat += 1.0; count++; return }

    // Half-goal width = 3.66m; angle subtended from player position
    const theta = Math.atan2(3.66, dist)
    threat += Math.cos(theta) / (dist * dist) * 1000
    count++
  })

  if (count === 0) return 0
  return Math.min(threat / (count * 1.5), 1.0)
}

/**
 * Component 2: Numerical Overload (O_num, 25%)
 * Divide defensive third into 5 vertical corridors and check for overloads.
 */
function computeNumericalOverload(oppPlayers, defPlayers, attackSide) {
  const isInDefThird = attackSide === 'right'
    ? (px) => px > 0.67
    : (px) => px < 0.33

  const corridors = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
  let overloadScore = 0

  for (let c = 0; c < 5; c++) {
    const yMin = corridors[c]
    const yMax = corridors[c + 1]

    const oppInCorridor = oppPlayers.filter(p =>
      isInDefThird(p.x) && p.y >= yMin && p.y < yMax
    ).length

    const defInCorridor = defPlayers.filter(p =>
      isInDefThird(p.x) && p.y >= yMin && p.y < yMax
    ).length

    const diff = oppInCorridor - defInCorridor
    if (diff > 0) overloadScore += diff
  }

  return Math.min(overloadScore / 3, 1.0)
}

/**
 * Component 3: Space Dominance (D_space, 30%)
 * Reach-time grid over the danger zone (opponent's defensive third).
 * Central cells weighted 1.5x.
 */
function computeSpaceDominance(allPlayers, attTeamId, attackSide) {
  const xMin = attackSide === 'right' ? 0.67 : 0.0
  const xMax = attackSide === 'right' ? 1.0 : 0.33

  const cells = computeZoneControl(allPlayers, xMin, xMax, 8, 5)
  if (cells.length === 0) return 0

  let attControl = 0
  let totalWeight = 0

  cells.forEach(cell => {
    const weight = cell.isCentral ? 1.5 : 1.0
    totalWeight += weight
    if (cell.teamId === attTeamId) {
      attControl += weight
    }
  })

  return totalWeight > 0 ? attControl / totalWeight : 0
}

/**
 * Component 4: Kinetic/Momentum Threat (M_kin, 15%)
 * Approximation of max(0, v_j . g_j) using speed * proximity to goal.
 * We lack direction vectors, so speed * (1 - dist_to_goal) serves as proxy.
 */
function computeKineticThreat(oppPlayers, goalCoords, attackSide) {
  const inAttHalf = attackSide === 'right'
    ? (px) => px > 0.5
    : (px) => px < 0.5

  let kineticSum = 0
  let count = 0

  oppPlayers.forEach(p => {
    if (!inAttHalf(p.x)) return
    const speed = p.speed || 0
    const normalizedSpeed = Math.min(speed / 30, 1.0)

    const dx = Math.abs(p.x - goalCoords.x)
    const proximityWeight = 1 - Math.min(dx, 1.0)

    kineticSum += normalizedSpeed * proximityWeight
    count++
  })

  return count > 0 ? Math.min(kineticSum / (count * 0.4), 1.0) : 0
}

function computeSingleOTI(attPlayers, defPlayers, allPlayers, attTeamId, attackSide) {
  const goalCoords = attackSide === 'right'
    ? { x: 1.0, y: 0.5 }
    : { x: 0, y: 0.5 }

  const sGoal = computeSpatialThreat(attPlayers, goalCoords, attackSide)
  const oNum = computeNumericalOverload(attPlayers, defPlayers, attackSide)
  const dSpace = computeSpaceDominance(allPlayers, attTeamId, attackSide)
  const mKin = computeKineticThreat(attPlayers, goalCoords, attackSide)

  const score = Math.round(sGoal * 30 + oNum * 25 + dSpace * 30 + mKin * 15)
  return {
    score: Math.max(0, Math.min(100, score)),
    label: otiLabel(score),
  }
}

function otiLabel(score) {
  if (score >= 70) return 'Critical'
  if (score >= 50) return 'Major'
  if (score >= 35) return 'Moderate'
  if (score >= 20) return 'Minor'
  return 'Low'
}

// --------------------------------------------------------------------------
//  PUBLIC API
// --------------------------------------------------------------------------

/**
 * Compute Rest Defence Scores for both teams.
 * Uses player positions directly (not the sparse control_grid).
 *
 * @param {Array} players - frame players [{id, team, x, y, speed, number}]
 * @param {{x,y}} ball - ball position (normalized 0-1)
 * @param {string[]} teamIds - [homeTeamId, awayTeamId]
 * @returns {{ home: {score, label}, away: {score, label} }}
 */
export function computeRestDefenceScores(players, ball, teamIds) {
  const empty = { score: null, label: '--' }
  if (!players || players.length === 0 || !ball || !teamIds || teamIds.length < 2) {
    return { home: empty, away: empty }
  }

  const [homeTeamId, awayTeamId] = teamIds
  const homePlayers = players.filter(p => p.team === homeTeamId)
  const awayPlayers = players.filter(p => p.team === awayTeamId)

  if (homePlayers.length === 0 || awayPlayers.length === 0) {
    return { home: empty, away: empty }
  }

  const homeDefSide = getDefendingSide(homePlayers)
  const awayDefSide = getDefendingSide(awayPlayers)
  const ballX = ball.x

  const homeRDS = computeSingleRDS(homePlayers, awayPlayers, players, ballX, homeTeamId, homeDefSide)
  const awayRDS = computeSingleRDS(awayPlayers, homePlayers, players, ballX, awayTeamId, awayDefSide)

  return { home: homeRDS, away: awayRDS }
}

/**
 * Compute Opponent Threat Index for both teams.
 * Each team's OTI = how threatening they are (attacking the opponent's goal).
 *
 * @param {Array} players - frame players [{id, team, x, y, speed, number}]
 * @param {{x,y}} ball - ball position (normalized 0-1)
 * @param {string[]} teamIds - [homeTeamId, awayTeamId]
 * @returns {{ home: {score, label}, away: {score, label} }}
 */
export function computeThreatScores(players, ball, teamIds) {
  const empty = { score: null, label: '--' }
  if (!players || players.length === 0 || !ball || !teamIds || teamIds.length < 2) {
    return { home: empty, away: empty }
  }

  const [homeTeamId, awayTeamId] = teamIds
  const homePlayers = players.filter(p => p.team === homeTeamId)
  const awayPlayers = players.filter(p => p.team === awayTeamId)

  if (homePlayers.length === 0 || awayPlayers.length === 0) {
    return { home: empty, away: empty }
  }

  const homeAttackSide = getDefendingSide(homePlayers) === 'left' ? 'right' : 'left'
  const awayAttackSide = getDefendingSide(awayPlayers) === 'left' ? 'right' : 'left'

  const homeOTI = computeSingleOTI(homePlayers, awayPlayers, players, homeTeamId, homeAttackSide)
  const awayOTI = computeSingleOTI(awayPlayers, homePlayers, players, awayTeamId, awayAttackSide)

  return { home: homeOTI, away: awayOTI }
}
