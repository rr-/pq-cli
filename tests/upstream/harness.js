// Runs Progress Quest web's game logic headless, for comparing with pqcli.
//
// Usage: node harness.js UPSTREAM_DIR < requests.json > responses.json
//
// The input is a JSON list of requests; the output is a JSON list with one
// response per request. Upstream's files are loaded from UPSTREAM_DIR
// (see fetch.py) and are not part of this repository.

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const upstreamDir = process.argv[2];
const store = {};

// Just enough browser for upstream to run without a DOM.
global.window = {
  location: { href: "#" },
  localStorage: {
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => {
      store[key] = String(value);
    },
    removeItem: (key) => {
      delete store[key];
    },
  },
};
Object.defineProperty(global, "navigator", {
  value: { userAgent: "node" },
  configurable: true,
});
global.document = null;
let expectedAlert = null;
global.alert = (message) => {
  if (message === expectedAlert) return;
  throw new Error("upstream alert: " + message);
};
// The clock Worker is replaced by explicit ticks, see play().
global.Worker = function () {
  this.postMessage = () => {};
  this.addEventListener = () => {};
};
const $ = (selector) => (selector === "#multiplayer:checked" ? { length: 0 } : null);
$.isFunction = (obj) => typeof obj === "function";
$.each = (obj, callback) => {
  if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) {
      if (callback.call(obj[i], i, obj[i]) === false) break;
    }
  } else {
    for (const key in obj) {
      if (callback.call(obj[key], key, obj[key]) === false) break;
    }
  }
  return obj;
};
$.ajax = () => ({ then: () => {}, done: () => {} });
global.$ = $;

for (const name of ["config.js", "main.js", "newguy.js"]) {
  const file = path.join(upstreamDir, name);
  vm.runInThisContext(fs.readFileSync(file, "utf8"), { filename: file });
}

let now = 0;
global.timeGetTime = () => now;

// FormCreate() tries to load the character named in the URL. There is
// none yet, so upstream alerts and gives up, which is fine here.
expectedAlert = "Error loading game";
FormCreate();
expectedAlert = null;

// Without a DOM, ListBox.rows() has no table to read. WinItem picks a row
// from it once the inventory passes 250 rows, so read the rows from game.
Inventory.rows = () =>
  game.Inventory.map((row) => ({ firstChild: { innerText: row[0] } }));

function newGame(spec) {
  // Mirrors the character creation form: stats.seed is the generator state
  // the stats were rolled from, and the game continues from it.
  stats = Object.assign({}, spec.stats, { seed: spec.seed });
  traits = { Name: spec.name, Race: spec.race, Class: spec.class };
  sold();
  LoadGame(JSON.parse(store.roster)[spec.name]);
}

function snapshot() {
  const bars = {};
  for (const id of ["ExpBar", "PlotBar", "QuestBar", "EncumBar", "TaskBar"]) {
    bars[id] = [game[id].position, game[id].max];
  }
  const statsOut = {};
  for (const key of K.Stats) statsOut[key] = game.Stats[key];
  return {
    caption: game.kill.replace(/\.\.\.$/, ""),
    level: game.Traits.Level,
    act: game.act,
    bars: bars,
    stats: statsOut,
    equipment: game.Equips,
    gold: game.Inventory[0][1],
    inventory: game.Inventory.slice(1),
    spells: game.Spells,
    quests: game.Quests,
    questmonster: game.questmonster,
    queue: game.queue,
    rng: randseed(),
  };
}

function play(request) {
  newGame(request.spec);
  const snapshots = [];
  for (let i = 0; i < request.ticks; i++) {
    const completing = TaskBar.done();
    now += 100;
    clock.lasttick = now - 100;
    Timer1Timer();
    if (completing) {
      // copy, since game's lists keep changing after this tick
      snapshots.push(JSON.parse(JSON.stringify(snapshot())));
      if (snapshots.length >= request.tasks) break;
    }
  }
  return snapshots;
}

function call(request) {
  randseed(request.rng.slice());
  if (request.questmonster !== undefined) {
    game.questmonster = request.questmonster;
    game.questmonsterindex = request.questmonsterindex;
  }
  const fn = global[request.fn];
  const result = fn.apply(null, request.args || []);
  return { result: result, rng: randseed() };
}

function lists() {
  const result = {};
  for (const key of Object.keys(K)) {
    if (Array.isArray(K[key])) result[key] = K[key];
  }
  return result;
}

const handlers = { play: play, call: call, lists: lists };
const requests = JSON.parse(fs.readFileSync(0, "utf8"));
const responses = requests.map((request) => handlers[request.cmd](request));
process.stdout.write(JSON.stringify(responses));
