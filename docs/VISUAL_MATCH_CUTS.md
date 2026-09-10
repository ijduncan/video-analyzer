# Visual match-cut discovery

The **Match cuts** tab is an experimental local visual search workspace. It compares decoded frames, independently of the existing Gemini related-shot suggestions and keyword search. Color search stays local. Shape and composition use billable Gemini image-understanding calls, with cached silhouettes/framing profiles and no fallback to arbitrary edge contours.

## Workflow

1. Open an analyzed local video, then **Match cuts** (or **Explore match cuts** beneath the shot preview).
2. Select an outgoing shot and scrub to the image you want to connect.
3. Choose one or more projects. **Build visual index** creates a saved frame index; indexing can be paused and resumed. Search partial results while indexing continues, then search again to include new frames.
4. For **Shape**, use **Identify shapes**, then select a visible object or part from the **Shape** list, click its outline, or draw around it. The source silhouette is fixed before any candidate is scored. **Match position and size too** additionally requires similar screen placement and occupancy. A drawn region chooses among identified objects; it does not perform an arbitrary crop segmentation. Composition evaluates the whole frame; color compares whole-frame palettes.
5. **Find match cut** returns the best sampled frame per candidate shot, excluding the source shot. Shape and Composition analyze uncached candidate frames through Gemini, covering shots before refining their remaining samples. Results update progressively; polling never initiates paid calls or retries. **Pause** stops background visual analysis. Search again explicitly resumes missing frames. Inspect the silhouette outlines, object labels, and separate position/size scores. Select a candidate to adjust timing and play a silent **A → B** preview. Outlines disappear when the incoming frame is adjusted away from the analyzed sample.
6. **Export cut JSON** saves both source-relative trim ranges, asset/run identifiers, the original discovery scores, search settings, and the discovered source/target outlines. The preview duration control also sets the exported handles. Adjusting the incoming cut does not recalculate the original sampled-frame scores.

## What the first version measures

- **Shape:** Gemini identifies up to six meaningful objects or parts per frame and traces their approximate outer silhouettes. Local geometry rasterizes each silhouette into a centered 64×64 mask, preserving aspect ratio and orientation while normalizing uniform size. Mask overlap ranks form independently of object name, color, screen position, and scale. Shape scores below 0.78 are omitted. Optional alignment requires position ≥0.65 and size ≥0.60 and weights silhouette/position/size 70/20/10. Without that option, position and size are shown separately and do not affect form ranking. Malformed/self-crossing outlines are rejected; other valid shapes are retained. This is approximate model segmentation, not a pixel-perfect mask or semantic category search.
- **Composition:** Gemini identifies the dominant subject/core body box, focal point, facing direction, lead/negative space, framing scale, and principal subject count. Ranking compares focal position and core mass, subject scale, space, direction, framing, and count. Strong position/opposite-direction conflicts are penalized; incompatible subject-vs-landscape structures and person-vs-object substitutions are rejected (use Shape for cross-object graphic transitions). Candidates below a heuristic 0.65 composition threshold are omitted, so fewer than 12 results is normal. The score is not an acceptance probability. Cached model descriptions may still be wrong; inspect the displayed subject box and framing explanation.
- **Color:** intersection of normalized HSV histograms across the whole frame.

Scores are relative heuristic similarities on a 0–100 display scale, not probabilities, editorial approval, or calibrated confidence. Shape search filters weak silhouettes; composition search filters incompatible framing; color search returns relative palette rankings. A high score does not establish that an edit works.

Each shot contributes five interior samples, at 10%, 30%, 50%, 70%, and 90% of its saved range. Short actions between these points can be missed, particularly in long shots. The user-selected source and adjusted incoming frames are decoded on demand. Near-blank candidates are excluded. Existing model-derived shot boundaries and descriptions remain approximate: inspecting the actual frames and preview is essential.

**Not implemented yet:** motion/action matching, learned embeddings, dense automatic cut-point optimization, crop/reframe alignment, a saved-pair collection inside the app, or match-pair FCPXML/EDL timelines. The existing Export tab still exports whole shots to those NLE formats; match-cut JSON is a separate handoff. The browser preview is an editorial aid, not a frame-accurate rendered sequence.

## Storage and execution

Per-asset SQLite indexes and JPEGs live under `backend/uploads/<asset>/visual/<revision>/` (or configured `UPLOAD_DIR`). The revision depends on the algorithm version, source file identity/stat information, analysis run, and shot ranges. Changed sources or analysis runs use a new index and stale source-frame requests are rejected. Old revisions are retained until the asset is deleted. These files remain local and ignored by Git.

One index build runs at a time, with up to two frame extractions sharing the decoding gate. Frame descriptors are committed incrementally. Closing the browser leaves indexing running; stopping the server preserves saved descriptors, and the next explicit build resumes. Failed samples can be retried. Deleting an asset cancels its index worker before deleting local files. Matching does not modify source analysis, annotations, or the original video-analysis usage records.

Requirements are included in `backend/requirements.txt`: OpenCV headless and NumPy, plus the existing FFmpeg installation. Shape and composition use the configured Gemini analysis model and the existing server or Settings key. Model usage is stored separately in the visual-index database, including completed responses that fail validation; it does not overwrite the original video-analysis usage. Interrupted requests may have provider charges that cannot be confirmed locally. Cache identity includes model and prompt version. Changing only matching weights does not re-analyze cached frames.

## Verification

Synthetic tests check that shape ranking can prefer a differently colored circle to a rectangle, composition distinguishes changed screen position, and color weighting responds to palette. API tests cover persisted indexing, duplicate/resume behavior, cancel/resume, blank/invalid regions, invalid source ranges, stale analysis, missing assets, and unchanged original analysis records.

The two current local clips indexed 245 samples across 49 shots with no failed frames. A warm cross-project search returned results from both projects in approximately 0.07 seconds on the development machine; this is one smoke measurement, not a feature-film benchmark. Browser checks exercised candidate selection, source-region errors, sequential A/B playback, and JSON trim-range export. Before the composition revision, the full backend suite passed 150 tests and 50 subtests; frontend production build and lint passed.

Next validation should use editor-labeled circle/form transitions and mixed aspect-ratio footage, then compare accepted matches and recall against learned embeddings. Feature-film cost, throughput, and retrieval quality have not been benchmarked.

## Composition revision

The initial edge/layout score incorrectly rewarded incidental details as composition. It has been replaced in the search route by Gemini framing profiles; pure composition searches never expose contour boxes or use contour matching as a fallback. Color-only searches also no longer show arbitrary shape boxes. Source and candidate descriptions are tied to the exact sampled images, independently of existing shot descriptions.

The user's reference frame (shot 34 at 57.292 seconds) was checked with the configured Gemini model. It described a medium shot with the soldier on the right, facing left into open left space. Revised results retrieved other right-weighted subjects with left lead room, instead of the original dam/background-detail candidates. Tests cover this ranking logic, incompatible/unclear subjects, malformed geometry, cached-source reuse, usage persistence, missing Gemini configuration, and zero provider calls during result polling. The full suite passed 156 tests and 50 subtests. Frontend build and lint passed. This is a targeted verification, not a film-corpus quality benchmark.

The teaser composition cache completed 215 nonblank sampled frames plus the exact reference frame in 37 provider requests (251,201 input tokens and 30,637 output/thinking tokens reported). Two repeated searches of the reference frame left that request count unchanged. The revised filter returned nine candidates, excluding the dam. These counts describe this one verification run, not a fixed price or expected workload for other videos.


## Shape revision

The source form no longer changes to suit each candidate. A fixed, named silhouette is selected before ranking; returned overlays follow that actual form. Different objects can match (wheel to moon) without sharing a label. The implementation follows Gemini's documented polygon segmentation capability: [Google image understanding](https://ai.google.dev/gemini-api/docs/image-understanding). Model outlines are approximate, and occlusion, blur, tiny subjects, holes, and lighting can still defeat extraction. Only outer boundaries are compared; holes and topology are not modeled. No automatic rotation, stretch, or crop correction is applied.

Source identification is cached per frame and model/prompt version. Selecting another recognized shape or changing weights reuses that cache. Provider schemas are deliberately simple; geometry and bounds are validated locally. Completed invalid responses still record usage. If every shape in a frame is invalid, the frame is marked for explicit retry while the index continues to other frames. Original footage analysis and its usage totals are untouched.

Tests exercise cross-object silhouettes, scale/position independence, portrait/landscape proportions, fixed source selection, alignment gating, malformed outlines, cache reuse, invalid-frame retry, stale revisions, and zero provider calls during polling. Synthetic shape examples establish geometric behavior; editor-labeled corpus evaluation is still needed to establish retrieval quality.

The revised suite passed 167 tests and 50 subtests; the frontend build and lint passed. Browser verification covered named and click-based selection, drawn regions, progressive results, alignment filtering, A/B playback, and JSON export with both outlines. In the teaser smoke test, a selected helmet remained the source form for every candidate, including a rounded flash and a graphic highlight. Those suggestions had poor screen alignment and were removed by the alignment option; they are form suggestions, not approved edits.

The verification run was paused with 131 of 215 eligible frames indexed and one frame awaiting explicit retry. Two repeated source-identification calls and cached-only searches left the provider request count unchanged at 48. The next explicit search resumes missing candidate frames; this partial cache is not a complete teaser or feature-film benchmark.
