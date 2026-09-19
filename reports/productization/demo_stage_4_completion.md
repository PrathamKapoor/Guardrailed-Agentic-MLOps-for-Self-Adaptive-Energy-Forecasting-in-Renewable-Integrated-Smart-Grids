# Demo Mode + presentation polish (Stage 4 / Stage 4A-2) — completion report

## Phase status

**STAGE 4 + 4A-2 COMPLETE — deterministic Demo Mode with two scenarios,
presentation mode, governance firewall visual, and frontend + backend test
suites that pass 100% with root-caused, proven fixes.**

This report supersedes the previous Stage 4A report, whose "test-isolation
debt" explanation was wrong. The real root causes were found, reproduced,
fixed, and are documented below with evidence.

## Architecture (unchanged from Stage 4)

```
Browser  ->  /demo
  -> Demo.tsx (current step from URL search params)
  -> primary scenario (7 steps)  or  safety scenario (5 steps)
  -> StepBody for the current step
       |   (api_refs) ->  Stage 2 FastAPI service
       |                ->  Existing research artefacts
       -> FinalInterpretation (real PV / LOAD / WIND records)
       -> Non-goals block (no retraining, no crypto, no fake LLM, no quantum)
  -> Next / Previous / Restart
```

Demo is read-only; the only side effect is the URL query string.

## Part 1 — Frontend: actual root cause

### Why the previous report was wrong

The previous report claimed the 8 failures "pass in isolation" and called
them "test-isolation debt". Re-baselining disproved this: `App.test.tsx`
**alone** failed 6 of 9 tests. The failures were deterministic everywhere;
the earlier sessions had simply not run the file alone.

### The failure chain (proven by direct instrumentation)

A temporary diagnostic test that called the installed mock directly and
logged every step of the response path proved:

1. `src/test/apiMocks.ts` resolved the matched endpoint's response via
   `overrideByEndpoint.get(match)` **even when no per-endpoint override was
   registered**. With no override, `Map.get` returns `undefined`, and the
   code never fell back to the typed default in `responses[match]`.
2. `JSON.stringify(undefined)` returns the JS value `undefined` (not the
   string `"undefined"`), so the mocked `Response.text()` resolved to
   `undefined`.
3. The API client (`src/api/client.ts` `_handle`) executed
   `JSON.parse(undefined)`, which threw a `SyntaxError`.
4. `useAsync`'s `.catch` stored the error in `AsyncState.error` and left
   `data: null`.
5. View components dereferenced the data anyway — e.g.
   `Governance.tsx:132 policy.data.policy_checksum.slice(0, 16)` — throwing
   `TypeError: Cannot read properties of undefined (reading 'slice' /
   'length')`, which `PageErrorBoundary` rendered as "Page error". The
   test then timed out waiting for content that never rendered.

Every mock that was not explicitly overridden returned `undefined`; every
view that touched the data crashed. That is why 8 tests failed
deterministically in every configuration.

### Additional mock-infrastructure bugs found and fixed

- **Substring matching with insertion-order precedence** (spec §10):
  replaced with exact normalized-path matching. The URL pathname (query
  string stripped) plus the HTTP method form the lookup key, so
  `GET /api/governance/decisions` (list) and `POST /api/governance/decisions`
  (evaluate) are distinct routes, and `/api/forecasts` can never match
  `/api/forecasts/load/metrics`. Precedence never depends on insertion
  order.
- **`Object.prototype.hasOwnProperty.call(map, key)` on a `Map`** never
  matches Map entries, so every per-test override (including the 503 error
  test) was silently ignored. Replaced with `Map.has` / `Map.get`.
- **Unmocked paths now return a typed 404 error envelope** instead of an
  empty 200 array, so a missing mock surfaces as a visible `ErrorBanner`,
  never as a silent wrong-shape success.
- **Per-test independence** (spec §7): `makeFetchMock()` builds a fully
  independent handle (own response snapshot, own override map);
  `installFetchMock()` is make + install. No mutable global state is
  shared between tests; `setup.ts` unstubbed globals in `afterEach`.

### Speculative production changes reverted (spec §1, §8, §9)

- `src/hooks/useApi.ts`: removed the `if (jsdom) disable health polling`
  branch. Production behavior is no longer environment-dependent. Tests
  stub `setInterval` at the test boundary in their own `beforeEach`
  instead.
- `src/pages/Agents.tsx`: restored `response.confidence.toFixed(2)` (the
  prop is non-null and `confidence: number` per the API contract); the
  `(response?.confidence ?? 0)` wrapper was added only to mask the mock
  bug.
- Kept: `Array.isArray(...)` checks in views — these are not speculative;
  `useAsync` returns `data: T | null`, so checking before array operations
  is type-required by the component state design.

### Test changes, each with a reason (spec §12)

| Change | Reason |
| --- | --- |
| `App.test.tsx` 503 test rewritten to use the mock's public `set()` API with Response-like overrides | The old test monkey-patched `h.install` after the fact — the anti-pattern spec §10 forbids; the public API now supports response-level overrides cleanly. |
| `demo.test.tsx` non-goals assertions read `document.body.textContent` | The product renders `does <strong>not</strong> retrain`; `getByText` regexes cannot match across element boundaries. Same words must be present — expectation unchanged. |
| `demo.test.tsx` quantum assertion checks the demo page for fabricated-capability phrasing | The old `queryByText(/quantum/i)).toBeNull()` could never pass: the Sidebar legitimately displays "Quantum/QML: NOT PART OF PROJECT" and the non-goals block states they are excluded. The invariant actually required (no quantum/QML/GNN capability claims) is now tested. |
| `apiMocks.ts` per-target metric fixtures (PV 36.12, WIND 778.84) | All three targets previously returned the LOAD metric, so the target-switching test's `36.120` assertion could never pass. Fixtures now mirror the frozen Phase 19 numbers. |
| Added `demo.test.tsx` presentation-mode test | Spec §16 requires verifying presentation mode; adds regression coverage (toggle class, navigation in presentation mode, exit). |

### Frontend verification

- Full suite: **27/27 PASS**.
- 5 consecutive full-suite runs: **5/5 PASS (27/27 each)**.
- Order swap: `App.test.tsx → demo.test.tsx` and `demo.test.tsx →
  App.test.tsx` both fully pass.
- `npx tsc -b`: PASS. `npm run build`: PASS (53 modules, 428 kB JS /
  13 kB CSS).
- `find src -name "*.js" -o -name "*.jsx"`: empty — `noEmit: true` stays in
  `tsconfig.json`; no generated source siblings exist.

## Part 2 — Backend: actual root causes (found during the §15 regression check)

The claimed "280/280 PASS" was never reproduced by this workstream. The
first complete run (wrong interpreter: Windows Store Python 3.13.14 instead
of `.venv` 3.13.2, which caused 26 fixture `AttributeError`s) took
52 minutes and ended `2 failed, 268 passed, 26 errors`. With the correct
`.venv\Scripts\python.exe`, two real failures remained:

1. **`test_landing_result_table_matches_frozen_csv`**: the landing page
   rendered the PV relative difference with the Unicode minus sign
   (`−7.61%`, U+2212) while the test asserts the ASCII hyphen (`-7.61%`)
   that `final_model_comparison.csv` produces. The content was correct;
   the character was not. **Fix**: replaced the single U+2212 with `-` in
   the hand-maintained `hackathon/index.html` result-table cell. (The
   landing page is not a protected Phase 19 artefact; the 20-artefact
   integrity baseline is unaffected and was re-verified.)

2. **`test_pre_freeze_boundary_intact`** had three compounding
   test-infrastructure bugs:
   - **Unbounded recursion**: it spawns `[sys.executable, -m, pytest]` as a
     child. The child re-collects `tests/test_hackathon_readiness.py`,
     reaches the same test, and spawns another pytest — recursing until the
     process tree exhausts memory and dies mid-run (observed as truncated
     child stdout and no summary). This is why the suite took ~50 minutes.
     **Fix**: a `SMARTGRID_NESTED_PYTEST` environment-variable guard — the
     nested invocation skips this one test (`pytest.skip`), the standard
     nested-suite pattern.
   - **`-q` escalation**: the spawned command's own `-q` combined with
     `pyproject.toml` `addopts="-q"` to `-qq`, which suppresses the final
     "N passed" summary line the `'passed' in stdout` assertion depends on.
     **Fix**: the spawned command no longer passes `-q`; `addopts` supplies
     exactly one quiet level.
   - **Broken checksum-target resolution**: the freeze loop used
     `sha_file.with_suffix("")`, which strips only `.sha256` and matched
     none of the actual `<name>.yaml` freeze files (verified: 19/19 fail to
     resolve) — the loop would crash with `FileNotFoundError` as soon as the
     assertion before it passed. **Fix**: `_resolve_freeze_target()` supports
     both sidecar formats used in this repo (`<digest>  <path>` and bare
     digest with same-stem counterpart). This also strengthens the check:
     the freeze verification was previously unreachable code.
   - **Strengthened**: the nested run's summary is parsed for `N failed`
     and must be 0 — the old `'passed' in stdout` check passed even when
     the nested run had failures (exactly what was happening).

### Backend verification

`.venv\Scripts\python.exe -m pytest --tb=short` → **296 passed, 0 failed,
in 154.02s** (280 prior tests + 16 hackathon-readiness tests; the earlier
"280" figure predates the hackathon layer). Suite runtime dropped from
~50 min (recursion) to 2.5 min.

## Regression / governance checks (spec §15)

| Check | Result |
| --- | --- |
| Backend `pytest` (venv interpreter) | **296/296 PASS** |
| Frontend `vitest` | **27/27 PASS**, 5/5 repeated runs |
| `npx tsc -b` | PASS |
| `npm run build` | PASS (428 kB JS / 13 kB CSS, gzip 140 kB / 3.0 kB) |
| Protocol freeze sidecars | **20/20 PASS, 0 FAIL** (3 non-freeze dataset manifests skipped — pre-existing) |
| Protected Phase 19 artefacts | **20/20 byte-identical** vs `phase19_integrity_baseline.json` |
| Diagnostic tests | Removed (`_trace`/`_t` files deleted); no `.js`/`.jsx` siblings in `src/` |

## Demo functionality verified (spec §16)

- **Primary scenario** (7 steps): forecasting → monitoring → agent →
  governance → decision → audit — covered by "renders all 7 primary steps
  in sequence with next/previous/restart" (PASS).
- **Safety scenario** (5 steps): lifecycle recommendation → governance
  blocks it; the demo's governance step renders the real `DENY` decision
  with `BENCHMARK_GATE_FAILED` and `SMARTGRID_DETERMINISTIC_GOVERNANCE`
  from the API (PASS); no Promote/Deploy/Rollback/Retrain buttons exist
  (PASS).
- **Presentation mode**: toggles `demo-page--presentation` (CSS hides the
  sidebar and enlarges cards), navigation works while active, exit restores
  (new test, PASS).
- **Audit wording**: "VALID JSONL", never "cryptographically verified"
  (PASS).

## Stage 4 demo safety invariants (re-verified)

| Invariant | Source of truth |
| --- | --- |
| Demo does NOT retrain models | `src/demo/demoData.ts` is read-only; no API mutation |
| Demo does NOT modify datasets / research metrics | Only `GET`s plus the validating `POST /api/governance/decisions` |
| Demo does NOT modify the Phase 13 policy or model registry | No mutation endpoint is called; registry endpoints are read-only |
| Demo does NOT create fake forecasting results | All numbers come from the Stage 2 API reading `final_model_comparison.csv` |
| Lifecycle commands are not executable from the Demo | No `PROMOTE` / `DEPLOY` / `ROLLBACK` / `RETRAIN` buttons; only descriptive tokens (tested) |
| Governance decision is authoritative; agent is advisory | Decision and recommendation render as separate fields; `agentSafety` tests (6) enforce the firewall |
| No quantum / QML / GNN / LLM capability claims | Tested: demo page contains no such phrasing; sidebar states "Quantum/QML: NOT PART OF PROJECT" |
| Reset is a no-op (only URL state changes) | `Restart` uses local state only (tested) |

## Files modified in Stage 4A-2

Frontend (test infrastructure + reverts):

- `product/frontend/src/test/apiMocks.ts` — exact method+path matching,
  `Map.has` override lookup, response-level overrides, typed 404 for
  unmocked paths, per-test independent handles, per-target metric fixtures
- `product/frontend/src/hooks/useApi.ts` — reverted jsdom-environment
  branch (production behavior restored)
- `product/frontend/src/pages/Agents.tsx` — reverted speculative
  `?? 0` guard
- `product/frontend/src/test/setup.ts` — shared `afterEach` (unstub, clear)
- `product/frontend/src/test/App.test.tsx` — 503 test via public `set()` API
- `product/frontend/src/test/demo.test.tsx` — text-content matchers,
  quantum-invariant assertion, new presentation-mode test
- `product/frontend/tsconfig.json` — `noEmit: true` (unchanged from 4A; no
  generated siblings exist)

Backend / hackathon layer:

- `tests/test_hackathon_readiness.py` — recursion guard, `-q` escalation fix,
  `_resolve_freeze_target()`, nested-run failure parsing
- `hackathon/index.html` — one character: U+2212 → ASCII `-` in the PV
  result cell (byte-match with the frozen CSV)

## NEXT STAGE: DEPLOYMENT HARDENING

Per the spec, no Docker, Kubernetes, cloud deployment, Kafka, Redis,
authentication, live telemetry, production inference, model serving, or LLM
integration was introduced in this stage.
