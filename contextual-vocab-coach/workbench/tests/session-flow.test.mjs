import assert from "node:assert/strict";
import test from "node:test";

import { getSessionPrompt, nextSessionStep } from "../src/sessionFlow.js";

test("a successful rating completes a one-item session instead of cycling", () => {
  assert.deepEqual(nextSessionStep("good", 0, 1), { kind: "complete", nextIndex: 0 });
});

test("again keeps the same item while successful ratings advance once", () => {
  assert.deepEqual(nextSessionStep("again", 0, 2), { kind: "retry", nextIndex: 0 });
  assert.deepEqual(nextSessionStep("hard", 0, 2), { kind: "next", nextIndex: 1 });
  assert.deepEqual(nextSessionStep("easy", 1, 2), { kind: "complete", nextIndex: 1 });
});

test("recognition and production prompts use opposite directions", () => {
  const base = { term: "water", meaning: "水" };
  const recognition = getSessionPrompt({ ...base, mode: "recognition" });
  const production = getSessionPrompt({ ...base, mode: "production" });

  assert.match(recognition.title, /water/);
  assert.equal(recognition.reference, "水");
  assert.match(production.title, /水/);
  assert.equal(production.reference, "water");
});

test("listening prompt asks for audio recall and keeps both sides in feedback", () => {
  const listening = getSessionPrompt({ term: "water", meaning: "水", mode: "listening" });

  assert.equal(listening.modeLabel, "听音理解");
  assert.match(listening.title, /播放英文/);
  assert.equal(listening.reference, "water · 水");
});
