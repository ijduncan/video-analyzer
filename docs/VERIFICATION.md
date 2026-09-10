# Verification record

## Result

The rebuild passes its local automated suite and live Gemini compatibility checks. The browser workflow was exercised with actual synthetic media from import through analysis, review and export. Comparative accuracy on customer footage and installed-editor round trips remain unverified.

## Automated checks

| Check | Result |
|---|---|
| Backend/media/export tests | 58 tests passed, with 43 passing parameterized subtests |
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

## Remaining validation

- Recognition/retrieval quality on representative agency and filmmaking footage, including difficult audio, fast montage and multilingual material.
- True word-aligned transcription and exact cut/frame verification.
- Fractional/drop-frame and variable-frame-rate NLE adapters.
- Round-trip imports in installed Premiere, Resolve and Final Cut Pro.
- Shared-workspace authentication/authorization, distributed queue recovery and archive-scale load testing.
- Hosted deployment and remote CI once repository write access is available.
