# WhyBot — Test & Optimization Report

**Result:** 248 backend tests + 13 UI regression scenarios + 1 full happy-path browser run — **all passing**.
13 defects were found and fixed; each one now has a dedicated regression test (`backend/tests/test_regressions.py`).

## How to run
```bash
cd backend
pytest -q                                   # 248 tests, offline, ~13s
FUZZ_EXAMPLES=3000 pytest tests/test_fuzz.py  # deep fuzzing (~30k generated inputs)
pip install pytest-randomly && pytest -p randomly   # random order (order-independence check)
python tests/bench.py .                     # latency benchmark

# Browser tests (needs ./start.sh running; MOCK_MODE=1 is fine; pip install playwright && playwright install chromium)
python tests_e2e/happy_path.py              # every page, profile, settings, live API call
python tests_e2e/ui_regression.py           # 13 bad-condition scenarios (stops/restarts the backend)
```

## What was tested
| Suite | Tests | Covers |
|---|---|---|
| `test_api.py` | 15 | Every endpoint's main behaviour, cache, persistence, concurrency |
| `test_edge_inputs.py` | 138 | Null/empty/missing/wrong-type fields on every endpoint, malformed JSON, hostile strings (XSS, SQL, template, path traversal, NUL bytes, emoji, RTL, CJK), odd filenames, fake/empty/real PDFs, CSV/JSON, bad & internal URLs, wrong methods |
| `test_scale.py` | 16 | Length boundaries (2000/2001 chars), 20 MB upload limit, 1 MB docs, 300k-char single line, 1,000 docs, 3,000-edge graphs, 30k-edge graph BFS, cycles & self-loops, mixed concurrent workload (12 threads), reset during traffic |
| `test_faults.py` | 29 | Live mode against a fake HydraDB SDK (retry, fallback, empty & None-filled responses, BYO-graph payload, memory sync), LLM success/exception/empty, URL timeouts/empty pages/redirects, 8 corrupt state files, unwritable disk |
| `test_fuzz.py` | 10 | Property-based fuzzing of text utils, edge parsing, BFS invariants, and the /ask, /impact, /upload APIs |
| `test_graph.py` | 4 | Graph engine unit tests |
| `test_regressions.py` | 36 | One or more tests per defect below |
| UI (`ui_regression.py`) | 13 | Corrupted localStorage, XSS never executes, readable validation errors, bad uploads, rapid clicks, long content overflow, 375px phone on all 7 pages, settings/profile persistence, 404 page, backend down + recovery, reduce motion, zero JS errors |

## Defects found and fixed
| # | Defect | Fix |
|---|---|---|
| D1 | Validation errors returned as raw lists (UI showed `[object Object]`) | Flattened to one readable sentence; frontend handles arrays too |
| D2 | Binary junk renamed `.txt` was accepted | Byte-level binary check + printable-text check |
| D3 | UTF-16 / Windows-1252 files decoded into garbage | BOM + UTF-16 detection, cp1252 fallback |
| D4 | Blast Radius on a meaningless change still listed people/incidents | Retrieve on the change text itself; skip when it has no meaningful words |
| D5 | Persona labels like `!!!` and `???` overwrote each other; `me` could be hijacked | Collision-free keys with a stable hash suffix; `me` reserved |
| D6 | Zero-width and control characters (NUL) were stored; duplicate memories stored | Unicode normalization + invisible/control stripping on every input; memory de-dup |
| D7 | `persona` on /ask, /compare, /impact had no length limit | Max 80 characters |
| D8 | A document without line breaks became one 300k-character chunk | Whitespace-aware windowing, max 1,000 chars per unit |
| D9 | Re-uploading a file leaked index entries (memory grew forever) | Tombstone compaction in the search index |
| D10 | **Null pointer:** a state file with valid JSON but `null`/wrong shapes crashed startup | Field-by-field shape validation; valid parts survive partial corruption |
| D11 | HydraDB outage during upload returned a raw 500 | Typed upstream error → 503 with a clear message; content kept locally |
| D12 | An empty LLM reply produced an empty answer | Falls back to cited evidence |
| D13 | **Security:** URL fetch followed redirects without re-checking for private addresses (SSRF) | Manual redirect handling with re-validation on every hop (max 4), non-HTML rejected |
| UI | Header stuck on "Connecting…" when the engine was down; proxy errors said "Internal Server Error" | "Engine offline" badge and a clear "Can't reach the WhyBot engine" message |

## Performance (before → after, same machine, offline mode)
| Scenario | Before | After | Change |
|---|---|---|---|
| Question with 5 MB of docs loaded | 19.0 ms | 3.5 ms | 5.4× faster |
| Graph question, 3k relationships | 14.7 ms | 6.5 ms | 2.3× |
| Blast Radius, 3k relationships | 29.1 ms | 15.2 ms | 1.9× |
| Compare (plain + graph) | 16.1 ms | 7.4 ms | 2.2× |
| Repeat question (cache hit) | 7.7 ms | 2.8 ms | 2.8× |
| 300 re-uploads of one file | 1,897 ms | 599 ms | 3.2× |

Main optimizations: debounced state writes (questions no longer rewrite every document to disk), cached graph rebuilt only when relationships change, adjacency-based traversal, precomputed entity tokens, index compaction.

## Not covered here
The real HydraDB service and a real LLM were not reachable from the test environment. The live path is verified against a fake SDK built from `hydradb-sdk` 2.x signatures; run one real question with your keys before the demo.
