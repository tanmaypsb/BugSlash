import test from "node:test";
import assert from "node:assert/strict";
import { supportsAutofixSource, supportsFindingAutofix } from "./fixCapabilities.js";

const sources = [
  ["sample.py", "python"],
  ["sample.js", "javascript"],
  ["sample.tsx", "typescript"],
  ["sample.c", "c"],
  ["sample.cpp", "cpp"],
  ["Sample.java", "java"],
  ["main.go", "go"],
  ["lib.rs", "rust"],
];

test("global action is available for every language family with a tested fixer", () => {
  for (const [name, language] of sources) assert.equal(supportsAutofixSource(name, language), true);
});

test("finding actions appear only for rule classes the fixer can address", () => {
  for (const [name, language, analyzer, category] of [
    ["sample.py", "python", "ruff", "F401"],
    ["sample.js", "javascript", "eslint", "quotes"],
    ["sample.ts", "typescript", "eslint", "quotes"],
    ["sample.c", "c", "clang-tidy", "readability-braces-around-statements"],
    ["sample.cpp", "cpp", "clang-tidy", "readability-braces-around-statements"],
    ["lib.rs", "rust", "clippy", "clippy::let_and_return"],
  ]) assert.equal(supportsFindingAutofix(name, language, analyzer, category), true);

  assert.equal(supportsFindingAutofix("Sample.java", "java", "spotbugs", "NP_ALWAYS_NULL"), false);
  assert.equal(supportsFindingAutofix("main.go", "go", "staticcheck", "SA5009"), false);
  assert.equal(supportsFindingAutofix("main.cpp", "cpp", "clang-tidy", "readability-magic-numbers"), false);
  assert.equal(supportsFindingAutofix("main.ts", "typescript", "eslint", "no-unused-vars"), false);
});

test("mismatched extensions and unknown languages remain unavailable", () => {
  assert.equal(supportsAutofixSource("main.rs", "go"), false);
  assert.equal(supportsAutofixSource("archive.zip", "python"), false);
  assert.equal(supportsAutofixSource("main.rb", "ruby"), false);
});
