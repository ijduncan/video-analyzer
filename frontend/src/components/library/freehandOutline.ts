// Keep a freehand silhouette compact without replacing it with a rectangle.
export function simplifyOutline(points: number[][]): number[][] | null {
  if (points.length < 3) return null
  function simplify(path: number[][], tolerance: number): number[][] {
    if (path.length <= 2) return path
    const a = path[0], b = path[path.length - 1]
    const dx = b[0] - a[0], dy = b[1] - a[1], length = dx * dx + dy * dy
    let furthest = 0, distance = tolerance * tolerance
    for (let i = 1; i < path.length - 1; i++) {
      const p = path[i], t = length ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length)) : 0
      const d = (p[0] - a[0] - t * dx) ** 2 + (p[1] - a[1] - t * dy) ** 2
      if (d > distance) { furthest = i; distance = d }
    }
    return furthest ? [...simplify(path.slice(0, furthest + 1), tolerance).slice(0, -1), ...simplify(path.slice(furthest), tolerance)] : [a, b]
  }
  let result = points
  for (let tolerance = 1.5; tolerance <= 1000; tolerance *= 1.5) {
    result = simplify(points, tolerance)
    if (result.length <= 96) break
  }
  if (Math.hypot(result[0][0] - result[result.length - 1][0], result[0][1] - result[result.length - 1][1]) < 2) result = result.slice(0, -1)
  const area = Math.abs(result.reduce((sum, p, i) => {
    const next = result[(i + 1) % result.length]
    return sum + p[0] * next[1] - next[0] * p[1]
  }, 0)) / 2
  if (result.length < 3 || result.length > 96 || area < 400 || [0, 1].some(axis => Math.max(...result.map(p => p[axis])) - Math.min(...result.map(p => p[axis])) < 10)) return null
  const cross = (a: number[], b: number[], c: number[]) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
  for (let i = 0; i < result.length; i++) {
    for (let j = i + 2; j < result.length; j++) {
      if (i === 0 && j === result.length - 1) continue
      const a = result[i], b = result[(i + 1) % result.length], c = result[j], d = result[(j + 1) % result.length]
      if (cross(a, b, c) * cross(a, b, d) < 0 && cross(c, d, a) * cross(c, d, b) < 0) return null
    }
  }
  return result
}
