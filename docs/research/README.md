# Video intelligence for agencies and filmmakers

The most useful rebuild is a footage intelligence workspace: make a large body of material easier to discover, judge, correct, and hand off. Recognition quality matters, but its value depends on whether an editor can inspect the exact supporting moment and move reviewed metadata into the next tool without losing context.

## Recommendation

Use Gemini as the first analysis provider, while keeping model identifiers and pricing configurable. The current stable Gemini 3.8 Flash supports native video/audio input and structured output. That makes it a pragmatic starting point for rich descriptions and flexible agency briefs, but documentation alone does not establish that it is the most accurate recognizer for any particular production archive.[1] Both initial presets use the same stable model; the full preset spends more passes on deeper analysis.

Benchmark Twelve Labs separately for archive-scale retrieval and temporal localization. Its video-specific retrieval and segmentation capabilities are a credible alternative, particularly when the problem shifts from describing one video to finding a short moment across many hours. Managed search, embeddings and generative analysis are distinct products with different model availability and economics; the model report describes the integration choices and version transitions.[2]

A single LLM should not supply technical facts, legal clearance, cut-accurate boundaries, calibrated confidence or all transcription timing. Read media facts with ffprobe, keep rights status as a human decision, distinguish model timestamps from source timecode, and evaluate specialist components where they improve measurable outcomes. Gemini's own documentation describes sampling and timestamp limitations; increasing sampling reduces some blind spots without proving exhaustive coverage.[3]

## Product opportunity

General AI visual search is already available inside major editing and asset-management products. The opportunity is the portable work product around it: reviewed scene/shot metadata, accessible evidence, reusable campaign context, rights filters, human corrections and reliable exports. The workflow report examines Premiere, Resolve, Final Cut Pro, Frame.io, iconik, axle and other approaches rather than treating basic tagging as a new category.

For agencies, the central task is finding footage that can actually be reused: the correct client and campaign, the right visual attributes, the right duration, relevant sound or dialogue, and known permission status. For filmmakers, it is moving from hours of material to credible shot logs and usable editorial selects. The same asset/shot evidence model supports both, with different filters and handoff priorities.

## Research package

| Report | Scope | Decisions supported |
|---|---|---|
| [Model landscape](model-landscape.md) | Current Gemini and Twelve Labs APIs, cloud indexers, open models, costs, privacy, limitations and evaluation | Initial provider, adapter boundaries, sampling strategy and benchmark design |
| [Workflows and market](workflows-and-market.md) | Creative-team workflows, competing tools, metadata portability and NLE handoffs | Agency-first product priorities, evidence model and differentiation |
| [Implementation roadmap](../ROADMAP.md) | Implemented behavior, remaining production work and concrete release gates | Honest scope, follow-on development and acceptance criteria |

The reports contain approximately 8,000 words and more than 50 primary-source references in total. Each report includes its own numbered sources. Vendor performance claims are identified as such; no cross-provider accuracy ranking has been fabricated.

## Rebuild decisions and their evidence

| Decision | Why | Current implementation |
|---|---|---|
| Library before per-file report | Agencies reuse footage across projects and campaigns | Persistent asset library, client/project/campaign metadata, collections and keyword search |
| Preserve original media | Technical truth and editorial links depend on source fidelity | Original files retained; derived posters and thumbnails; media range playback |
| Human and AI metadata separated | Corrections must survive analysis and model changes | Separate shot annotations, explicit review status, AI evidence and warnings |
| Native video analysis first | Native audio/video context is useful for creative briefs | Configurable Gemini passes; model/version and usage provenance |
| Portable metadata | Editor-specific indexes are not a durable interchange contract | Versioned JSON, safe UTF-8 CSV, XMP, timed transcript SRT, guarded NLE references |
| No invented timing | A valid-looking 24fps EDL is wrong for many sources | Source facts retained, approximate timestamps labeled, unsupported source timing rejected |
| Local-first initial release | A single-user library can be tested before introducing distributed operations | SQLite persistence, bounded background jobs, restart recovery, loopback deployment |

## Evaluation before a provider switch

Create a rights-cleared test set spanning commercials, interviews, social edits, documentary footage, narrative scenes, product close-ups, fast montage, multilingual dialogue and silent b-roll. Label true shot boundaries, retrieval queries with relevant in/out ranges, essential visible objects/text/logos, and a sample of transcripts. Reserve a held-out portion to compare models without repeatedly tuning prompts to the same clips.

Measure temporal intersection-over-union, retrieval recall at fixed ranks, tag precision/recall, unsupported-claim rate, transcript word error, timing error, actual cost and end-to-end latency. Assess missed events separately from wrong tags. An attractive summary can mask poor coverage; a provider that wins on broad visual similarity may still lose on exact dialogue or fast cuts. Proposed thresholds and sample design appear in the full reports.

Do not label a provider “best” until it performs on this corpus with the application's real prompts, frame sampling, input lengths and budget. Changes in provider versions, prompts or schemas should trigger a regression run before automatic migration of an existing archive.

## Current verification boundary

The rebuild can be validated locally for file import, media inspection, persistence, search/filter behavior, review edits, API state transitions and export structures. Mocked provider tests can verify schema/range validation and failure handling. They cannot establish how well the real models recognize footage.

Gemini 3.8 Flash passed live tests of both presets on a synthetic six-second clip containing two colored segments with exact text labels. Both passes recovered the two labels and the three-second boundary without inventing speech on a silent source. This establishes API compatibility on a controlled fixture; a representative footage accuracy benchmark remains outstanding. NLE exports have structural tests, but no installed-editor round trip has been performed. Those remain explicit release gates.

## Sources

1. Google. [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). Official model documentation, updated September 2026. Stable model identifier, inputs, structured output and supported capabilities.
2. Twelve Labs. Exact model, API and pricing pages are listed in [Model landscape — sources](model-landscape.md), alongside release dates and API distinctions.
3. Google. [Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding). Official API guide, accessed September 2026. Native video inputs, sampling, temporal customization and limitations.
