import assert from "node:assert/strict";
import test from "node:test";
import { ESLint } from "eslint";

const eslint = new ESLint();
async function violations(code, filePath = "src/lint-fixture.jsx") {
  const [result] = await eslint.lintText(code, { filePath });
  return result.messages.map((message) => message.ruleId);
}

test("lint blocks undefined JSX components and conditional hooks", async () => {
  const rules = await violations(`import { useState } from 'react';
export function Example({ ready }) {
  if (!ready) return null;
  const [value] = useState(0);
  return <Missing>{value}</Missing>;
}`);
  assert(rules.includes("no-undef"));
  assert(rules.includes("react-hooks/rules-of-hooks"));
});

test("lint checks effect dependencies in plain JS custom hooks too", async () => {
  const rules = await violations(
    `import { useEffect } from 'react';
export function useExample(value) { useEffect(() => { document.title = value; }, []); }`,
    "src/lint-fixture.js",
  );
  assert(rules.includes("react-hooks/exhaustive-deps"));
});

test("lint supports typed React props without requiring legacy React JSX import", async () => {
  assert.deepEqual(
    await violations(
      `import type { ComponentPropsWithoutRef } from 'react';
export function Example(props: ComponentPropsWithoutRef<'button'>) { return <button {...props} />; }`,
      "src/lint-fixture.tsx",
    ),
    [],
  );
});

test("migration preserves DOM, key, duplicate prop and legacy ref enforcement", async () => {
  const rules = await violations(`export function Example() {
    return <div class="wrong">{[1, 2].map(value => <button id="a" id="b" ref="old">{value}</button>)}</div>;
  }`);
  assert(rules.includes("@eslint-react/dom-no-unknown-property"));
  assert(rules.includes("@eslint-react/no-missing-key"));
  assert(rules.includes("react-compat/no-duplicate-props"));
  assert(rules.includes("react-compat/no-string-refs"));
});

test("migration preserves unescaped text guard and accepts escaped entities", async () => {
  assert(
    (
      await violations(`export function Example() { return <p>don't</p>; }`)
    ).includes("react-compat/no-unescaped-entities"),
  );
  assert.deepEqual(
    await violations(`export function Example() { return <p>don&apos;t</p>; }`),
    [],
  );
});
