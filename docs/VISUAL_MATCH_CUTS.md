# Visual match-cut discovery

The **Match cuts** tab is an experimental local visual search workspace. It compares decoded frames, independently of the existing Gemini related-shot suggestions and keyword search. It does not make provider API calls.

## Workflow

1. Open an analyzed local video, then **Match cuts** (or **Explore match cuts** beneath the shot preview).
2. Select an outgoing shot and scrub to the image you want to connect.
3. Choose one or more projects. **Build visual index** creates a saved frame index; indexing can be paused and resumed. Search partial results while indexing continues, then search again to include new frames.
4. Adjust **Shape**, **Composition**, and **Color** weights. Drag a region around a shape, or use the keyboard-accessible **Center region** control. Region selection restricts source contours; color still compares whole frames. If no clear contour is detected in the selected region, the app asks for a different region instead of inventing a match.
5. **Find match cut** returns the best sampled frame per candidate shot, excluding the source shot. Inspect the outlined regions and individual visual scores. Select a candidate to adjust incoming timing and play a silent **A → B** preview.
6. **Export cut JSON** saves both source-relative trim ranges, asset/run identifiers, the original discovery scores, and search settings. The preview duration control also sets the exported handles. Adjusting the incoming cut does not recalculate the original sampled-frame scores.

## What the first version measures

- **Shape:** Canny contours, Hu moment measurements, circularity, fill, and aspect ratio. This is classical computer vision, not semantic object recognition or learned visual embeddings. Contours can come from textures or background details, and unrelated objects can share an outline.
- **Composition:** spatial Lab color layout, edge distribution, and the position/scale of matched contours in normalized screen coordinates.
- **Color:** intersection of normalized HSV histograms across the whole frame.

Scores are relative heuristic similarities on a 0–100 display scale, not probabilities, editorial approval, or calibrated confidence. The algorithm currently returns ranked candidates even when similarity is weak. A high score does not establish that an edit works.

Each shot contributes five interior samples, at 10%, 30%, 50%, 70%, and 90% of its saved range. Short actions between these points can be missed, particularly in long shots. The user-selected source and adjusted incoming frames are decoded on demand. Near-blank candidates are excluded. Existing model-derived shot boundaries and descriptions remain approximate: inspecting the actual frames and preview is essential.

**Not implemented yet:** motion/action matching, learned embeddings, dense automatic cut-point optimization, crop/reframe alignment, a saved-pair collection inside the app, or match-pair FCPXML/EDL timelines. The existing Export tab still exports whole shots to those NLE formats; match-cut JSON is a separate handoff. The browser preview is an editorial aid, not a frame-accurate rendered sequence.

## Storage and execution

Per-asset SQLite indexes and JPEGs live under `backend/uploads/<asset>/visual/<revision>/` (or configured `UPLOAD_DIR`). The revision depends on the algorithm version, source file identity/stat information, analysis run, and shot ranges. Changed sources or analysis runs use a new index and stale source-frame requests are rejected. Old revisions are retained until the asset is deleted. These files remain local and ignored by Git.

One index build runs at a time, with up to two frame extractions sharing the decoding gate. Frame descriptors are committed incrementally. Closing the browser leaves indexing running; stopping the server preserves saved descriptors, and the next explicit build resumes. Failed samples can be retried. Deleting an asset cancels its index worker before deleting local files. Matching does not modify source analysis, annotations, or provider usage records.

Requirements are included in `backend/requirements.txt`: OpenCV headless and NumPy, plus the existing FFmpeg installation. No new model/key setup is needed.

## Verification

Synthetic tests check that shape ranking can prefer a differently colored circle to a rectangle, composition distinguishes changed screen position, and color weighting responds to palette. API tests cover persisted indexing, duplicate/resume behavior, cancel/resume, blank/invalid regions, invalid source ranges, stale analysis, missing assets, and unchanged original analysis records.

The two current local clips indexed 245 samples across 49 shots with no failed frames. A warm cross-project search returned results from both projects in approximately 0.07 seconds on the development machine; this is one smoke measurement, not a feature-film benchmark. Browser checks exercised candidate selection, source-region errors, sequential A/B playback, and JSON trim-range export. Full backend suite: 150 tests and 50 subtests passed; frontend production build and lint passed.

Next validation should use editor-labeled circle/form transitions and mixed aspect-ratio footage, then compare accepted matches and recall against learned embeddings. Feature-film cost, throughput, and retrieval quality have not been benchmarked.
