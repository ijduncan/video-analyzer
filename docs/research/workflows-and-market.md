# Video analysis workflows and market research

## Recommendation

Build a professional video logging and discovery workspace whose output is **reviewed, time-linked, portable metadata**. A successful session should end with an editor finding a usable moment, checking the evidence, improving its description, and exporting a useful selection or metadata package. A screen full of generated tags is an intermediate result.

The competitive baseline has moved substantially. Adobe Premiere has local visual search; Final Cut Pro now supports visual and transcript search; DaVinci Resolve 21 includes IntelliSearch; and established media asset management products combine AI enrichment with review and editor integrations. Simple semantic search, transcription, summaries, thumbnails, and object tags are necessary capabilities but insufficient differentiation.[^1][^2][^3]

The strongest opportunity is to combine practical agency metadata with filmmaker vocabulary, show exactly why each annotation exists, preserve corrections across model upgrades, and move useful selections into editing tools. This is a product recommendation based on documented workflows, not a claim that any one recognition model is the most accurate. Model quality must be evaluated separately on representative footage.

This report reflects sources checked on September 9, 2026, Pacific time. Product documentation establishes supported behavior; it does not independently establish recognition accuracy, adoption, reliability, or claimed time savings. Newly announced features and older documents are identified where they affect interpretation.

## The jobs the product should serve

### Agencies and brand production teams

The agency's recurring question is: “Which footage can we use for this client, campaign, audience, territory, and deadline?” Visual relevance is only the first condition. The producer also needs to know whether a clip belongs to the correct client, which version is current, whether it has been approved, what restrictions were supplied, and whether the source can be retrieved.

Recommended workflow:

1. Ingest footage into a client and project context, retaining the original filename and source reference.
2. Produce a searchable proxy, technical metadata, transcript, shot descriptions, visible text, and suggested tags.
3. Apply a project vocabulary for products, campaign, deliverable, brand themes, and rights records.
4. Search content while applying explicit operational filters, such as approved status and supplied usage window.
5. Review a candidate at its matched moment, with surrounding context; correct or reject annotations.
6. Assemble a named collection of selects, attach notes, and export ranges plus metadata.
7. Preserve the relationship between sources, selects, and later deliverables so archive reuse becomes easier.

This extends the established pattern of editable fields and saved collections in Frame.io. Its documentation describes built-in and custom fields, metadata-driven Collections, and exportable comments. A new product should make these connections feel immediate while adding rich shot-level analysis.[^4][^5][^6]

### Documentary, narrative, and commercial filmmakers

The filmmaker's question is more specific: “Where is the usable reaction, alternate take, clean insert, exact quote, or shot that completes this sequence?” A generic label such as “person, room, conversation” is rarely enough.

Recommended workflow:

1. Keep camera identifiers, reel, source timecode, shoot day, scene and take information whenever available.
2. Generate shot candidates with explicit start and end points and playable evidence.
3. Describe framing, angle, camera movement, action, visual environment, light, sound, and useful editorial moments.
4. Separate transcript text from visual interpretation, and allow one to find the other.
5. Mark favorites, rejects, continuity notes, clean handles, and tentative selects.
6. Export a log, range markers, or a selects sequence that reconnects to source media.

Iconik's documented workflow is a useful benchmark: selecting transcript text creates a timed range, which can become metadata or a subclip; comments can arrive as Premiere markers. The product lesson is that the transition from finding a quote to handing it to an editor matters as much as speech recognition.[^7]

## Competitive landscape

| Product or category | Verified capability relevant to this project | Implication for the rebuild |
|---|---|---|
| Adobe Premiere media intelligence | Locally analyzes visuals and finds matching clip sections; can combine search with metadata filters. Its FAQ distinguishes semantic visual retrieval from tags and says the analysis/index cannot be used by other applications. The visual system does not perform OCR or identify people.[^1][^8] | Avoid treating visual embeddings as editable tags. Offer portable descriptions, OCR evidence, and reviewed structured metadata with a separate retrieval layer. |
| Final Cut Pro | Visual and transcript search; exact or related spoken-word queries; combined criteria including ratings and metadata. Current support documentation identifies limits for compound clips and multichannel audio analysis.[^2] | Search plus favorites is already a native workflow. Compete on library scope, structured metadata, cross-tool portability, and handling of diverse source material. |
| DaVinci Resolve 21 | IntelliSearch separates visual, transcript, and metadata search. Faster and Better analysis modes are documented. The guide describes optional face identification and custom metadata filtering.[^3] | Make analysis profiles understandable, and never equate slower analysis with a guaranteed accuracy gain without measurement. Filmmaker-specific metadata must produce a concrete editorial benefit. |
| Iconik | AI transcription/enrichment, hybrid storage workflows, editable transcripts, timed metadata, subclips, review, and Premiere integration. Subclip behavior depends on storage: mapped storage can open subclips, while cloud storage may download the full parent with range markers.[^7][^9][^10] | Treat storage location, proxies, retrieval cost, and range semantics as first-class concerns. “Export clip” must describe whether it means an actual media file, a range reference, or a marker. |
| Axle AI | Existing MAM and Tags offerings emphasize existing storage, local AI, scene understanding, transcription, and metadata search. FOCUS was announced for IBC September 11–14, 2026, with tiered local workflows, APIs, and editor handoffs.[^11][^12] | A local or hybrid option is meaningful for teams with large NAS archives. FOCUS's new integration should be evaluated as announced behavior, not independently proven deployment performance. |
| Frame.io V4 | Custom fields, saved metadata Collections, role-based permissions, timed comments, and CSV/XML/plain-text/FIOJSON comment exports.[^4][^5][^6][^13] | Review status, custom fields, and browser collaboration are baseline workflow requirements. Prioritize a focused review loop before attempting a complete review-and-approval platform. |
| Cantemo | Item metadata and access controls; alternate formats; metadata projections on export; Premiere proxy editing, high-resolution relink, and source-media tracking.[^14][^15] | Asset identity and relationships are durable value. Design for originals, proxies, derived files, project membership, and downstream usage. |
| IPV Curator | Searches names and metadata; supports retrieving Premiere productions. Official material describes highlighting whether a match comes from names, descriptions, logged information, or AI-derived content.[^16][^17] | Every result should explain its match: transcript, visible text, reviewed tag, inferred visual description, or technical metadata. |
| Avid PhraseFind AI / ScriptSync AI | Avid documents phrase-based dialogue search and script/dialogue synchronization workflows.[^18] | Interview and take discovery deserve a transcript-oriented mode. Generating a polished summary is not a substitute for returning the exact useful line. |
| Twelve Labs developer platform | Indexed video search accepts text/image queries and returns relevance plus matching time ranges. Metadata filters can constrain searches using supplied fields.[^19][^20] | Useful candidate infrastructure for multimodal retrieval; still requires application-owned metadata, review, media management, and editorial exports. |

The table compares documented workflow characteristics, not overall product rankings. Enterprise systems have broader scope than the proposed application; reproducing their entire permissions, archive, storage, and automation stack would obscure the product's initial advantage.

## Where the product can differentiate

### Evidence attached to each meaningful claim

Show a clickable time range, representative frame, transcript quote, or visible-text region beside generated metadata. A summary without navigable support forces the editor to rewatch the material. A search result with an unexplained relevance number forces the editor to guess why it appeared.

Use clear evidence classes:

| Evidence class | Example | Treatment |
|---|---|---|
| Extracted technical fact | Codec or embedded camera metadata | Read from the media/tool output; retain the original field and parser version. |
| Observed visual evidence | A red vehicle in sampled frames | Link the supporting sample times; avoid implying continuous presence between distant samples. |
| Recognized speech | A quoted interview sentence | Show speaker label, word/segment timing, and editable transcript. |
| Recognized text | A sign, slate, label, or lower third | Preserve exact OCR text separately from its interpreted meaning. |
| Model interpretation | “Tense mood” or “possible establishing shot” | Label as suggested editorial interpretation; allow rejection or replacement. |
| Human-provided fact | Client name, performer identity, usage permission | Record who supplied or confirmed it; protect it from automatic replacement. |

This is a proposed data and interface policy. It should not be confused with a claim that generated rationales prove a model correct. Supporting pixels, audio, and original records are the evidence; an explanation is a convenience.

### A vocabulary that is useful in an edit

Support two opinionated templates with configurable fields. An agency template should include client, brand, campaign, product, intended platform, supplied rights information, status, and deliverable relevance. A filmmaker template should include production, scene, take, reel, camera, framing, angle, movement, location shown, action, audio content, continuity notes, and select status.

Use stable term identifiers and display labels. Merge synonyms such as “close-up” and “CU” for search while preserving a preferred spelling. Let teams add terms without altering the fundamental schema. Allow a free-text note where a forced category would discard useful nuance.

Never force unknown values into confident categories. “Unknown,” “not analyzed,” “not applicable,” and “rejected suggestion” describe different situations and should remain distinguishable. A “no speech” finding should also be distinct from a failed transcription job.

### Corrections that survive reanalysis

Keep a generated annotation separate from the current reviewed value. Reanalysis should create a proposal or new analysis version, not silently overwrite a producer's edits. Store taxonomy version, prompt/schema version, model identifier, processing profile, sampled ranges, and analysis timestamp.

A reviewer should be able to accept, edit, or reject a suggestion in one action. Batch actions need a visible scope. Undo and revision history are more useful early features than a complex approval matrix.

### Honest handling of scope and uncertainty

Display whether the whole video, selected intervals, or sparse samples were analyzed. When a slow or failed stage leaves gaps, the player should show those gaps. A time range inferred from sampled frames should be labeled as approximate until a temporal process or human review validates its boundaries.

Do not display an LLM's self-reported percentage as an objective probability. Retain provider scores when available with their meaning, but use evaluation data to determine whether they can support thresholds. Retrieval relevance, label confidence, transcription confidence, and boundary precision are separate quantities.

## Recommended metadata model

The canonical schema should be application-owned and versioned, with adapters to external standards. IPTC Video Metadata Hub is a strong semantic reference because it spans visible/audible content, rights, administrative details, and technical properties, and supports mappings to JSON, XMP, and EBUCore. Its user guide distinguishes location shot from location shown and describes sidecar, embedded, and external-database representations.[^21][^22]

| Entity | Minimum fields | Why it matters |
|---|---|---|
| Asset | Stable ID, content fingerprint, original filename, source URI/reference, byte size, created/imported dates, duration | Prevent filename-based identity errors and duplicate analysis. |
| Media representation | Asset ID, role (original/proxy/audio/thumbnail), location, codec, dimensions, availability, derivation | Keep storage and presentation separate from the underlying footage. |
| Technical timing | Stream time base, nominal/average frame rate, variable-frame-rate flag, embedded start timecode if present, timecode mode, rotation, audio track map | Needed to reconcile player times, analyzed media, original frames, and exports. |
| Segment | Stable ID, parent asset, start/end, coordinate system, segment type, boundary method, review status | Distinguish a detected shot, semantic event, transcript span, and human select. |
| Annotation | Subject entity, field/term, value, origin, evidence references, model/run ID, review status | Enables explainability, corrections, filters, and provenance. |
| Transcript | Language, speaker labels, segments/words, timings, revision history, channel/source mapping | Supports quote finding and later corrections without destroying alignment. |
| Editorial metadata | Summary, action, shot size, angle, movement, lighting, scene/take, select rating, continuity notes | Makes footage useful to producers and editors. |
| Business metadata | Client, project, campaign, brand/product IDs, owner, delivery status | Makes an archive useful to agencies. |
| Supplied rights records | Rights owner, license reference, supplied usage scope, dates, territory, release references, reviewer/status | Connects discoverability to an operational review process. |
| Relationships | Derived-from, proxy-of, subclip-of, version-of, belongs-to, used-in | Preserves connections across source footage and deliverables. |
| Analysis run | Provider/model, schema/prompt version, settings, coverage, job state, timestamps, cost/usage, errors | Makes processing reproducible and failures recoverable. |

Rights-related fields are records supplied or reviewed by a person or trusted source. A model can suggest that a logo or person appears; it cannot infer contractual permission, release status, ownership, or territorial clearance from pixels. This is a product behavior recommendation, not legal advice or an automated clearance system.

Do not embed all data directly into original video files as the initial persistence mechanism. Use a database plus a complete JSON sidecar export. Add XMP or container metadata only through explicit, tested mappings. The metadata hub provides the semantic reference, but a standards mapping is not evidence that every destination editor preserves every field.

## Temporal integrity and editorial handoff

Relative playback seconds, encoded presentation timestamps, frame numbers, and source timecode are not interchangeable. A clip can begin at source timecode 01:00:00:00 while the browser player begins at zero. A proxy may have transformed timing or different frame characteristics. The application should record the relevant mappings instead of assuming a universal frame rate.

FFprobe exposes container and stream metadata and can extract timecode from different locations depending on format, including a MOV timecode track. Probe the file rather than asking a model to infer codec, duration, frame rate, or embedded timecode.[^23]

Recommended temporal rules:

- Store normalized asset-relative intervals with an explicit start-inclusive/end-exclusive convention.
- Preserve the underlying media timing and frame-rate rational rather than rounding every file to 24, 25, or 30 fps.
- Keep source timecode as a separate field, including its declared mode; if absent, label it unavailable.
- Record chunk offsets and map chunk-level responses back to the source asset before saving.
- Validate that every interval is ordered and lies within the analyzed asset duration.
- Distinguish model-estimated boundaries from frame-verified or manually confirmed boundaries.
- Retain handles separately from the chosen edit range.
- Test fractional frame rates, nonzero source timecode, rotated phone footage, variable frame rates, multichannel audio, and proxy relinking.

These are engineering recommendations. They should be release gates for professional export claims, even when an AI model appears impressively accurate on a demo clip.

### Export priorities

| Export | Appropriate use | Release condition |
|---|---|---|
| Versioned JSON | Complete machine-readable analysis, provenance, evidence, edits, and metadata | Round-trip back into the application without losing IDs, timing, or reviewed values. |
| CSV shot log | Producer review, spreadsheets, searchable archive handoff | Stable columns, correct quoting/Unicode, explicit time units, asset and segment IDs. |
| SRT / WebVTT | Transcript or caption exchange | Export actual transcript cues; never silently turn visual descriptions into dialogue captions. |
| FCPXML | Final Cut media, keywords, ratings, markers, ranges, and selects sequences | Validate against a supported format version and import in the target Final Cut release. |
| OTIO | An application-neutral editorial timeline representation | Validate time ranges and references; document adapters and unsupported fields. |
| Premiere / Resolve handoff | Markers, subclips, logs, or selects using supported target-specific routes | Test the exact editor/version and media-relink workflow; publish a capability matrix. |
| Contact sheet or review log | Human inspection and sharing of selects | Include asset identity, time ranges, reviewed notes, and sufficient surrounding context. |

Apple documents FCPXML exchange of media, metadata, ratings, keywords, and markers. OpenTimelineIO provides a native JSON format and adapter plugins for additional formats; its documentation explicitly notes varying support and maintenance levels for community adapters. Therefore “supports XML” or “supports OTIO” is not sufficient proof of complete interoperability.[^24][^25][^26]

An initial build can ship robust JSON, CSV, and transcript exports while labeling NLE-specific integration as pending verification. A CSV marker file should not be advertised as a universal native Premiere import unless that exact path has been tested. A reference range must not be presented as an exported media clip.

## Search and review experience

Build one search experience with visible match types and strong filters. Support literal transcript/OCR searches, structured metadata filters, and semantic visual retrieval as distinct mechanisms that can cooperate. A semantic query such as “quiet city street after rain” should not prevent exact filters for client, camera, aspect ratio, approved status, and minimum duration.

Every result should show the matching asset, in/out range, representative image, brief description, and why it matched. For text matches, highlight the words. For visual results, link the relevant sample or playback span. Avoid a wall of tags and unexplained scores.

The default detail view should connect player, timeline, transcript, and editable metadata. Selecting a shot seeks the player. Selecting transcript text creates a range. Selecting an annotation reveals its evidence. Keyboard navigation, next-unreviewed actions, and undo reduce repeated manual work.

Saved collections should capture filters or explicit selects, and indicate which type they are. An automatically changing search collection serves a different purpose from a fixed shortlist sent to an editor. Collection membership should be stable and reviewable when an export is generated.

## Build order

### First complete product slice

Deliver ingest, a durable job record, real media playback, technical probing, configurable analysis, persisted results, shot/evidence navigation, editable annotations, search/filter, selects, and JSON/CSV/transcript export. Include retries, cancellation, clear error states, and coverage status. Support an agency and a filmmaker analysis template through the same underlying schema.

This is the smallest workflow that can show genuine professional usefulness. It connects the source file to a reviewed output and can be validated end to end.

### Second slice: better temporal analysis and interchange

Improve shot boundary detection and word alignment; add OCR/slate evidence, configurable controlled vocabularies, duplicate reuse, source timecode mappings, and versioned reanalysis. Implement one fully tested NLE handoff before claiming broad NLE coverage. Add proxy support for formats or file sizes that do not play well in a browser.

### Third slice: team and archive workflows

Add project membership, permissions, shared collections, review assignment, recorded usage constraints, source/derivative relationships, external storage connectors, and existing MAM integrations. Treat this as expansion after the core logging workflow is reliable.

Defer full cloud archive management, billing, watermark distribution, complete approval routing, autonomous re-editing, custom face-recognition training, and speculative recommendation dashboards until evidence shows that the target teams need them. This keeps development focused on the distinctive value: trustworthy metadata that improves an edit.

## Evaluation and release gates

Evaluate complete tasks, not the apparent eloquence of a model response. Build a permissioned corpus of representative commercial footage, interviews, documentary b-roll, rapid cuts, low light, handheld motion, product close-ups, screen content, multilingual speech, archival media, and no-audio clips. Include clips with common technical edge cases and known expected metadata.

| Dimension | Measurement | Practical decision |
|---|---|---|
| Tag quality | Per-field precision/recall against reviewed labels; unsupported-claim rate | Which fields are safe to suggest automatically? |
| Temporal accuracy | Boundary error and interval overlap against reviewed ranges | Are results good enough for discovery, logging, or direct editing? |
| Search usefulness | Top-result relevance, recall at a small result count, time to useful select | Does the tool outperform the existing workflow? |
| Transcript quality | Word errors plus timestamp errors, especially names and important quotes | Can the editor trust navigation and exported cues? |
| Review effort | Corrections per minute and time to approved metadata | Does richer output save effort or create cleanup work? |
| Coverage | Percentage of input actually analyzed, skipped intervals, silent failures | Is the UI accurately representing what is known? |
| Interchange | Successful import, correct ranges, preserved key fields, correct relink | Is the export claim justified? |
| Operations | Completion rate, latency, cost per analyzed hour, retry recovery | Is the chosen processing profile practical? |

Use human-reviewed reference examples and retain difficult failures. Do not compare providers using unrelated marketing benchmarks. Separate short-shot description, long-video understanding, temporal retrieval, OCR, and transcription tests. The best provider may differ across these tasks, which argues for a provider adapter and application-owned schema.

No independent head-to-head product or model accuracy test was performed for this report. Vendor feature availability, quality under the actual account tier, editor-version compatibility, and recognition performance remain items for direct validation.

## Sources

[^1]: Adobe. [Search for media using media intelligence](https://helpx.adobe.com/premiere/desktop/organize-media/file-organization/search-for-media-using-ai-powered-media-intelligence.html). Updated June 2, 2026. Local search, clip discovery, filtering, and reduced-frame-analysis limitations.

[^2]: Apple. [Find clips and projects in Final Cut Pro for Mac](https://support.apple.com/en-gb/guide/final-cut-pro/ver65764b45/mac). Current user guide, accessed September 9, 2026. Visual/transcript searches, ratings, combined filters, and documented clip/audio limitations.

[^3]: Blackmagic Design. [DaVinci Resolve 21 New Features Guide](https://documents.blackmagicdesign.com/SupportNotes/DaVinci_Resolve_21_New_Features_Guide.pdf). 2026, pp. 38–41 and 86. IntelliSearch modes and custom metadata. This guide retains beta wording for some unrelated features, including Slate ID; their completed availability is not assumed here. Current [product page](https://www.blackmagicdesign.com/uk/products/davinciresolve) also advertises Resolve 21 and IntelliSearch.

[^4]: Frame.io. [Getting Started: How do I use metadata?](https://help.frame.io/en/articles/9092149-getting-started-how-do-i-use-metadata). June 16, 2026. Built-in/custom fields and project views.

[^5]: Frame.io. [Collections Overview](https://help.frame.io/en/articles/9101042-collections-overview). Current V4 documentation, accessed September 9, 2026. Collections built from metadata.

[^6]: Frame.io. [Comments Panel Overview](https://help.frame.io/en/articles/9105278-comments-panel-overview). Current V4 documentation, accessed September 9, 2026. Timecode, comment filters, editable fields, and comment export formats.

[^7]: Iconik. [How Iconik transcriptions, comments, and the Premiere Panel collapse the gap between shoot and edit](https://www.iconik.io/workflows/iconik-transcriptions-comments-and-the-premiere-panel). 2026, accessed September 9, 2026. Transcript correction, text-to-range workflow, SRT/WebVTT export, and Premiere markers. Workflow description is vendor-authored, not an independently measured time-savings study.

[^8]: Adobe. [Media intelligence and Search panel FAQ](https://helpx.adobe.com/premiere/desktop/organize-media/file-organization/media-intelligence-and-search-panel.html). August 19, 2026. Semantic retrieval versus tags, OCR/identity limits, local operation, and proprietary index portability.

[^9]: Iconik. [AI metadata generation and media intelligence](https://www.iconik.io/artificial-intelligence). Accessed September 9, 2026. AI enrichment, proxies, and administrator-controlled processing. Privacy statements are vendor representations.

[^10]: Iconik. [Release — Iconik 25.10](https://www.iconik.io/release-notes/iconik-2510). November 3, 2025. Storage-dependent Premiere subclip behavior.

[^11]: Axle AI. [AI-powered media asset management](https://www.axle.ai/). Accessed September 9, 2026. Existing-storage cataloging, metadata search, proxies, and local AI positioning. Marketing superiority and customer-count claims are not adopted.

[^12]: Axle AI. [Axle AI FOCUS launches at IBC2026](https://www.axle.ai/blog/axle-ai-focus-revolutionary-on-premise-media-search-software-launches-at-ibc2026-conference). Posted September 4, 2026, with release dateline September 3. Announcement for September 11–14 demonstration; configurations and capabilities are announced, not independently verified in deployment.

[^13]: Frame.io. [User Roles and Permissions](https://help.frame.io/en/articles/9875389-user-roles-and-permissions). Current V4 documentation, accessed September 9, 2026.

[^14]: Cantemo. [Items and SubClips](https://doc.cantemo.com/latest/UserDocumentation/items.html). Version 6.2.1 documentation, accessed September 9, 2026. Item formats, metadata exports, relationships, and access controls.

[^15]: Cantemo. [Cantemo Panel for Premiere Pro](https://doc.cantemo.com/latest/UserDocumentation/apps/ppro/main.html). Version 6.2.1 documentation, accessed September 9, 2026. Proxy/high-resolution relink and media tracking.

[^16]: IPV. [Searching for assets](https://help.ipv.com/docs/searching-for-assets). Current support documentation, accessed September 9, 2026. Search and Premiere-production retrieval.

[^17]: IPV. [Introducing search highlighting](https://blog.ipv.com/introducing-search-highlighting-and-why-it-was-our-most-user-requested-feature). Older official feature article, approximately 2020. Used only as evidence of the established match-explanation workflow, not current licensing or interface details.

[^18]: Avid. [Media Composer 2023.8: PhraseFind AI and ScriptSync AI Preview FAQ](https://kb.avid.com/pkb/articles/en_US/Knowledge/PhraseFind-AI-and-ScriptSync-AI-Preview-FAQ?popup=true). August 2023. Used to establish dialogue-search and script-sync workflow purpose, not 2026 pricing or current option entitlements.

[^19]: Twelve Labs. [Search](https://docs.twelvelabs.io/docs/guides/search). Current developer documentation, accessed September 9, 2026. Query modalities, result identity, relevance, and time ranges. Pin the actual API/model version during implementation.

[^20]: Twelve Labs. [Filtering](https://docs.twelvelabs.io/docs/guides/search/filtering). Current developer documentation, accessed September 9, 2026. System and supplied metadata filters. API capabilities should be checked against the selected version.

[^21]: IPTC. [Video Metadata Hub](https://iptc.org/standards/video-metadata-hub/). Accessed September 9, 2026. The site identifies Recommendation 1.7 as current; do not infer a publication year from its undated news teaser.

[^22]: IPTC. [Video Metadata Hub User Guide](https://www.iptc.org/std-dev/videometadatahub/userguide/vmhub-may2021.html). May 2021, based on VMH 1.3. Used for stable semantic concepts and storage approaches; field counts and version-specific additions are not treated as current.

[^23]: FFmpeg developers. [ffprobe Documentation](https://ffmpeg.org/ffprobe.html). Current documentation, accessed September 9, 2026. Structured stream/container inspection and format-specific timecode extraction.

[^24]: Apple. [Content and Metadata Exchanges with Final Cut Pro](https://developer.apple.com/documentation/professional-video-applications/content-and-metadata-exchanges-with-final-cut-pro). Current developer documentation, accessed September 9, 2026. Media/metadata exchange, keywords, ratings, and editorial decisions.

[^25]: Apple. [Creating FCPXML Documents](https://developer.apple.com/documentation/professional-video-applications/creating-fcpxml-documents). Current developer documentation, accessed September 9, 2026. Media assets, timelines, metadata, markers, keywords, and ratings.

[^26]: Academy Software Foundation / OpenTimelineIO. [Adapters](https://opentimelineio.readthedocs.io/en/latest/tutorials/adapters.html). Documentation labeled 0.19.0.dev1, accessed September 9, 2026. Native formats, separately installed adapters, and community maintenance caveats; development documentation is not a stable-package compatibility guarantee.
