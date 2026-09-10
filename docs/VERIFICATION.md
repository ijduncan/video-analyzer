# Verification record

## Result

The rebuild passes its local automated suite and live Gemini compatibility checks. The browser workflow was exercised with actual synthetic media from import through analysis, review and export. Comparative accuracy on customer footage and installed-editor round trips remain unverified.

## Automated checks

| Check | Result |
|---|---|
| Backend/media/export tests | 89 tests passed, with 52 passing parameterized subtests |
| Frontend TypeScript and production build | Passed; Vite production bundle generated |
| Frontend ESLint | Passed |
| Diff whitespace check | Passed |
| Production frontend dependency audit | No vulnerabilities reported at verification time |

Tests use isolated temporary storage and mocked provider responses where appropriate. Actual ffmpeg tests cover local import, ffprobe facts, poster creation and HTTP range playback. Other regressions cover persistent metadata, filters, shot annotations, range validation, model usage, archived reviews, concurrent deletion claims, early cancellation, safe media cleanup and export structure. Two dependency deprecation warnings from Starlette/httpx remain; they do not fail the suite.

The GitHub Actions workflow repeats tests/build/lint on Ubuntu with ffmpeg. Publishing was blocked by GitHub: the configured Git identity `ijduncan-unfold` was denied write access to `ijduncan/video-analyzer` (HTTP 403). Its remote run must be checked after the branch is published; local results do not imply remote CI has already run.

## Live Gemini compatibility

Both presets ran through the real Files API and `generate_content` with `gemini-3.8-flash`, using the replacement key in ignored `.env.local`. The controlled fixture was a six-second 640×360, 24fps silent video: red with `RED SAMPLE` for three seconds, then blue with `BLUE SAMPLE` for three seconds.

| Measure | Fast index | Full creative analysis |
|---|---:|---:|
| Completion | Passed | Passed |
| Logged shots | 2 | 2 |
| Reported intervals | 0–3s, 3–6s | 0–3s, 3–6s |
| Correct overlay strings | 2 / 2 | 2 / 2 |
| Invented spoken transcript | None | None |
| Input tokens | 3,806 | 6,957 |
| Billable output tokens, including thinking | 1,940 | 3,729 |
| Thinking tokens included above | 945 | 1,611 |
| Estimated API cost | $0.010129 | $0.019202 |

Full creative analysis also produced two scene insights, a summary and the related-shot pass. Both runs left generated observations unreviewed. Synthetic provider uploads were deleted after verification. The earlier key's interrupted smoke run was superseded; the evidence above comes from the replacement key.

These results establish the current SDK/request/schema compatibility and expected behavior on an intentionally simple fixture. They do not measure recognition accuracy on real productions, prove exhaustive cut detection, or rank Gemini above competitors. Costs are dated estimates from recorded token usage, not billing guarantees.

Sanitized local evidence is saved under `artifacts/qa/provider-smoke.json` and is excluded from Git together with test media.

## Browser and API workflow

The production frontend was served by FastAPI on loopback. Browser inspection found meaningful content, no framework error overlay and no uncaught page errors. Desktop and 390px mobile inspector layouts were visually inspected.

1. Imported a real six-second 25fps synthetic test-pattern MP4 through the file input. Verified its actual poster, codec facts, source timecode and playable preview.
2. Entered client/project/collection/tags, set review and rights status, and saved. Reloaded the browser and confirmed persisted metadata and project/filter facets.
3. Searched a saved tag and applied cleared-rights filtering. The correct asset remained in results.
4. Downloaded JSON from the inspector; the observed HTTP request returned 200.
5. Started fast indexing from the UI. The observed POST returned 202, the background job completed, and the indexed-shot count and inspector updated through polling.
6. Opened the actual model-generated shot and saved a human tag/review decision. The observed annotation PATCH returned 200.
7. Retrieved JSON, CSV, XMP, EDL and FCPXML exports through the live API; all returned 200. SRT correctly returned 422 because the source has no transcript, rather than turning visual descriptions into captions.
8. Found the saved human tag through shot search. Removed the test asset through the inspector confirmation; DELETE returned 200. Verified the library record, uploaded copy and thumbnails were removed while the separate source fixture remained intact. The working library was left empty for real footage.

This separate UI test used 640×360 synthetic test-pattern footage with embedded 25fps source timecode and produced one continuous shot. Its estimated model cost was $0.006981. Local screenshots and resulting sidecars are saved under `artifacts/qa/` and excluded from Git.

## Minimal library interface follow-up

Removed the FRAME branding, sidebar, dashboard totals, promotional copy, and onboarding panels. The library now opens with search, Videos/Shots, collapsed filters, Import, and Settings. Secondary metadata and analysis details use disclosure sections.

Production build and ESLint passed. Browser checks at desktop and 390px mobile width covered import, preview, tag saving, keyword search, filter disclosure, analysis controls, and settings. JSON export returned HTTP 200; the automated browser's download capture was canceled, so this check does not establish a saved browser download. The disposable synthetic asset was removed through the UI and the library was left empty. No additional provider calls were needed.

## Progressive analysis follow-up

Indexing now publishes shots and thumbnails after each 30-second processing section. The live provider test used a separate 42-second synthetic source and isolated database: its first ten shots were saved at 16.03 seconds, thumbnails appeared at 16.31 seconds, and all fourteen shots finished at 23.09 seconds. These are observed fixture timings, not a latency guarantee for production footage. The remote test upload was deleted. See [progressive analysis](PROGRESSIVE_ANALYSIS.md) for the implementation, evidence and remaining limits.

Browser verification replayed those saved partial/final snapshots through a separate local server and database, with the provider key disabled. Ten shots and their thumbnails were available while status remained analyzing; playing shot ten sought to 27 seconds and started playback. Unsaved tags, the selected shot and active tab survived the fourteen-shot refresh. With both a project filter excluding all assets and a query returning no shots, polling continued and a newly matching shot appeared automatically. A simulated error displayed saved partial shots with playable cards. The isolated fixture was restored and the QA server/browser stopped. Screenshots are retained under ignored `artifacts/qa/progressive-ui-*.png`. At short viewport heights, the inspector scrolls to reveal live shot cards below the progress controls.

The existing 152-second user asset completed under the previous pipeline. After the local server update, its saved three shots and metadata remained available; it was not reanalyzed during verification.

## Full-window workspace and midpoint thumbnails

Selected footage now occupies the full browser canvas. Desktop uses a large player beside a thumbnail shot grid, with Shots, Analysis and Metadata tabs; narrow screens stack these areas. The library remains mounted but hidden, preserving search/filter/page state and restoring focus and scroll on return. Generated analysis precedes its settings, and live progress stays beside the player.

The isolated browser fixture was inspected at desktop and 390px mobile width. The mobile page and workspace both measured 390px with no horizontal overflow. Captured desktop evidence covers partial shot cards, playback selection, an unsaved metadata draft and restored library filters; no browser page errors were reported. The disposable fixture was restored and its server/browser stopped. Final frontend build and lint passed.

Thumbnail extraction now chooses `start + (end - start) / 2`. Legacy invalid end timestamps fall back to a valid start; invalid starts are skipped. Images are replaced atomically, and URLs include file modification time so regenerated frames replace cached thumbnails. A real ffmpeg red-to-blue fixture verifies that extraction chooses the blue midpoint rather than the red opening. Additional tests cover fractional timing, fallbacks, extraction failures and thumbnail cache invalidation. The full automated suite passed 89 tests and 52 subtests.

After both real assets finished analysis, their 51 thumbnails were regenerated locally: 48 for the Half-Life teaser and three for Timeline 4. Their analysis and metadata were preserved, with no additional Gemini calls. The updated teaser thumbnails were visually checked in the full-window workspace.

## Remaining validation

- Recognition/retrieval quality on representative agency and filmmaking footage, including difficult audio, fast montage and multilingual material.
- True word-aligned transcription and exact cut/frame verification.
- Fractional/drop-frame and variable-frame-rate NLE adapters.
- Round-trip imports in installed Premiere, Resolve and Final Cut Pro.
- Shared-workspace authentication/authorization, distributed queue recovery and archive-scale load testing.
- Hosted deployment and remote CI once repository write access is available.
