import assert from 'node:assert/strict'
import { test } from 'node:test'
import { simplifyOutline } from '../src/components/library/freehandOutline.ts'

test('preserves the neck and shoulders of a traced person instead of a bounding box', () => {
  const person = [[400, 100], [600, 100], [620, 300], [580, 380], [760, 450], [820, 950], [180, 950], [240, 450], [420, 380], [380, 300]]
  assert.deepEqual(simplifyOutline([...person, person[0]]), person)
})

test('reduces a dense continuous trace to the API point limit', () => {
  const points = Array.from({ length: 1000 }, (_, i) => [500 + 300 * Math.cos(i * Math.PI / 500), 500 + 400 * Math.sin(i * Math.PI / 500)])
  const result = simplifyOutline(points)
  assert.ok(result.length > 12 && result.length <= 96)
  assert.ok(Math.max(...result.map(p => p[0])) > 798)
})

test('rejects accidental clicks, tiny drags, and crossed outlines', () => {
  assert.equal(simplifyOutline([[20, 20]]), null)
  assert.equal(simplifyOutline([[20, 20], [22, 20], [22, 22]]), null)
  assert.equal(simplifyOutline([[0, 0], [800, 900], [800, 0], [0, 1000]]), null)
})
