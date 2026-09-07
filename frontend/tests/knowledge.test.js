import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { searchDocuments } from '../src/services/knowledge.js';

const read = name => JSON.parse(readFileSync(new URL(`../public/demo/${name}`, import.meta.url), 'utf8'));
const { documents } = read('knowledge.json');
for (const entry of read('search-parity.json')) {
  test(`browser/Python search parity: ${JSON.stringify(entry.query)}`, () => {
    assert.deepEqual(searchDocuments(documents, entry.query).items, entry.items);
  });
}
test('empty corpus and result limit', () => {
  assert.deepEqual(searchDocuments([], 'UDP').items, []);
  assert.equal(searchDocuments(documents, 'LONG_SESSION', 1).items.length, 1);
});
