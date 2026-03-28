/**
 * Shape graph computation in JavaScript.
 * Port of pipeline compute_shape_graph() (Brandes et al. 2025).
 *
 * Uses d3-delaunay for triangulation, then iteratively removes
 * edges with low angular stability.
 */
import { Delaunay } from 'd3-delaunay'

/**
 * Compute angle at vertex v in triangle (p, q, v) in degrees.
 */
function angleAtVertex(coords, pIdx, qIdx, vIdx) {
  const vp = [coords[pIdx][0] - coords[vIdx][0], coords[pIdx][1] - coords[vIdx][1]]
  const vq = [coords[qIdx][0] - coords[vIdx][0], coords[qIdx][1] - coords[vIdx][1]]

  const dot = vp[0] * vq[0] + vp[1] * vq[1]
  const magVp = Math.sqrt(vp[0] * vp[0] + vp[1] * vp[1])
  const magVq = Math.sqrt(vq[0] * vq[0] + vq[1] * vq[1])

  if (magVp < 1e-10 || magVq < 1e-10) return 0

  const cosAngle = Math.max(-1, Math.min(1, dot / (magVp * magVq)))
  return Math.acos(cosAngle) * (180 / Math.PI)
}

/**
 * Make a canonical edge key (smaller index first).
 */
function edgeKey(i, j) {
  return i < j ? `${i}-${j}` : `${j}-${i}`
}

/**
 * Compute shape graph edges from player coordinates.
 *
 * @param {Array<[number, number]>} coords - Player [x, y] positions
 * @param {number} angleThreshold - Angular stability threshold in degrees (default 45)
 * @param {number} minEdges - Minimum edges before fallback to full Delaunay (default 5)
 * @returns {Array<[number, number]>} List of [i, j] edge index pairs
 */
export function computeShapeGraph(coords, angleThreshold = 45, minEdges = 5) {
  if (!coords || coords.length < 3) return []

  const delaunay = Delaunay.from(coords)
  const triangles = delaunay.triangles // flat Uint32Array, groups of 3
  const numTriangles = triangles.length / 3

  if (numTriangles === 0) return []

  // Build edge-to-opposite-vertices map
  // For each edge, store the opposite vertex from each triangle it belongs to
  const edgeOpposite = new Map() // key -> [oppositeVertexIdx, ...]

  for (let t = 0; t < numTriangles; t++) {
    const a = triangles[t * 3]
    const b = triangles[t * 3 + 1]
    const c = triangles[t * 3 + 2]

    // Edge a-b, opposite c
    const kAB = edgeKey(a, b)
    if (!edgeOpposite.has(kAB)) edgeOpposite.set(kAB, [])
    edgeOpposite.get(kAB).push(c)

    // Edge b-c, opposite a
    const kBC = edgeKey(b, c)
    if (!edgeOpposite.has(kBC)) edgeOpposite.set(kBC, [])
    edgeOpposite.get(kBC).push(a)

    // Edge a-c, opposite b
    const kAC = edgeKey(a, c)
    if (!edgeOpposite.has(kAC)) edgeOpposite.set(kAC, [])
    edgeOpposite.get(kAC).push(b)
  }

  // Iterative removal
  const activeEdges = new Set(edgeOpposite.keys())
  let changed = true

  while (changed) {
    changed = false
    const toRemove = []

    for (const key of activeEdges) {
      const opposites = edgeOpposite.get(key)
      // Boundary edges (1 triangle) are always kept
      if (!opposites || opposites.length < 2) continue

      const [iStr, jStr] = key.split('-')
      const i = parseInt(iStr)
      const j = parseInt(jStr)

      // Angular stability = 180 - angle_a - angle_b
      // where angle_a and angle_b are at the opposite vertices
      const angleA = angleAtVertex(coords, i, j, opposites[0])
      const angleB = angleAtVertex(coords, i, j, opposites[1])
      const stability = 180 - angleA - angleB

      if (stability < angleThreshold) {
        toRemove.push(key)
      }
    }

    for (const key of toRemove) {
      activeEdges.delete(key)
      changed = true
    }
  }

  // Fallback: if too few edges, revert to full Delaunay
  if (activeEdges.size < minEdges) {
    const allEdges = []
    for (const key of edgeOpposite.keys()) {
      const [iStr, jStr] = key.split('-')
      allEdges.push([parseInt(iStr), parseInt(jStr)])
    }
    return allEdges
  }

  // Convert to edge list
  const edges = []
  for (const key of activeEdges) {
    const [iStr, jStr] = key.split('-')
    edges.push([parseInt(iStr), parseInt(jStr)])
  }
  return edges
}
