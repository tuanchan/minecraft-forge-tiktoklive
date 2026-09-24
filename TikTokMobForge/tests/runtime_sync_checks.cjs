const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const count = {value: 1}, label = {}, image = {};
const dropdown = {dataset: {value: 'minecraft:zombie'}, contains: () => false};
const card = {};
const nodes = {max_mobs_total: {value: 4}, golem_teleport_distance: {value: 20}, wolf_teleport_distance: {value: 20}};
let remote = {bridge: {follow_spawn_count: 3, follow_mob_type: 'minecraft:blaze'}, mod: {max_mobs_total: 8, golem_teleport_distance: 35, wolf_teleport_distance: 12}};
const state = {bridge: {follow_spawn_count: 1, follow_mob_type: 'zombie'}, mod: {max_mobs_total: 4, golem_teleport_distance: 20, wolf_teleport_distance: 20}, catalog: {mobs: []}};
const context = {
  state, autoSaveReady: true, saveFlight: null, AbortSignal,
  lastSavedPayload: JSON.stringify({bridge: state.bridge, mod: state.mod}),
  document: {activeElement: {}, getElementById: key => nodes[key] || null, querySelector: selector => selector.includes('follow') ? card : null},
  $: selector => selector === '.event-count' ? count : selector === '.event-mob-dropdown' ? dropdown : selector === '.event-preview' ? image : label,
  $$: () => [], iconUrl: () => '', eventMobImage: () => '', updateEventRule() {}, renderLivePanel() {}, updateSpamEstimate() {}, saveStatus() {}, toast() {}, setTimeout() {},
  api: async () => remote,
  collectPayload: () => ({bridge: {follow_spawn_count: Number(count.value), follow_mob_type: dropdown.dataset.value.replace(/^minecraft:/, '')}, mod: Object.fromEntries(Object.entries(nodes).map(([key, node]) => [key, Number(node.value)]))}),
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../web/runtime-settings.js'), 'utf8'), context);
(async () => {
  await context.pollRuntimeSettings();
  assert.equal(count.value, 3);
  assert.equal(nodes.max_mobs_total.value, 8);
  assert.equal(nodes.golem_teleport_distance.value, 35);
  assert.equal(nodes.wolf_teleport_distance.value, 12);
  assert.equal(dropdown.dataset.value, 'minecraft:blaze');
  remote.bridge.follow_mob_type = 'minecraft:skeleton';
  await context.pollRuntimeSettings();
  assert.equal(dropdown.dataset.value, 'minecraft:skeleton', 'namespace must not turn a synced field into a local draft');
  context.document.activeElement = count;
  remote.bridge.follow_spawn_count = 9;
  await context.pollRuntimeSettings();
  assert.equal(count.value, 3);
  context.document.activeElement = {};
  await context.pollRuntimeSettings();
  assert.equal(count.value, 9, 'update deferred until blur');
  count.value = 6;
  remote.bridge.follow_spawn_count = 10;
  await context.pollRuntimeSettings();
  assert.equal(count.value, 6, 'preserve unsaved local edit');
  console.log('RUNTIME_GUI_SYNC_OK: repeated remote edits, mob namespaces, focus/blur, local drafts');
})().catch(error => { console.error(error); process.exitCode = 1; });
