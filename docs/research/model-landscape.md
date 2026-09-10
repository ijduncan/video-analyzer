# Video understanding models for an agency and filmmaking analysis platform

Gemini is a strong default for this rebuild, but a top-tier video library needs several complementary capabilities: reliable media inspection, shot boundaries, speech transcription, descriptive analysis, temporal retrieval, and human correction. The recommended first release uses a configurable stable Gemini model for semantic analysis, deterministic media tooling for technical facts, and an evidence-bearing metadata schema. TwelveLabs should be the first specialist challenger for retrieval and event segmentation. Private deployment with open models is a later option when confidentiality or sustained throughput justifies operating GPUs.

This recommendation reflects official documentation available on September 9, 2026. Model availability and pricing change quickly. The newer releases below are verified in current vendor documentation; older examples using Gemini 1.5/2.0, Pegasus 1.2, or Marengo 2.7 should not become architectural defaults. No application-specific comparison of model accuracy has yet been run. Recommendations therefore identify candidates and a validation method, rather than declaring a universal winner.

## Decisions for the rebuild

| Decision | Recommended implementation | Reason |
| --- | --- | --- |
| Default analysis provider | Gemini, with an environment-configured model ID and recorded model version | Existing credentials can be reused while upgrades remain inexpensive to adopt. |
| Initial stable model | `gemini-3.8-flash`; evaluate `gemini-3.5-flash-lite` for inexpensive first-pass tagging | Both are documented stable video/audio-capable models. [^1][^2] |
| Precision analysis | Restrict analysis to selected time windows and use denser frames for small text, rapid cuts, and product appearances | A whole-video summary is insufficient evidence for exhaustive metadata. |
| Source of technical truth | Container/stream metadata and decoded frame timing | A language model should not invent camera settings, codec, frame rate, or timecode. |
| Retrieval roadmap | Metadata/full-text search first; compare TwelveLabs Marengo embeddings with an open embedding baseline | Retrieval quality and description quality are different objectives. |
| Shot/event semantics | Keep shot cuts, narrative scenes, and event occurrences as different record types | A camera cut is not necessarily a narrative scene or a new brand occurrence. |
| Review | Every generated field retains evidence, provenance, and a review state | Confidence is useful only when its meaning and calibration are clear. |

The important product distinction is between finding a useful moment and certifying every occurrence. An agency searching for “a warm outdoor product close-up” can tolerate approximate ranked candidates. A producer checking every logo appearance or a filmmaker building a frame-accurate edit list cannot. The interface should make that distinction visible through coverage, boundary accuracy, and review status.

## Gemini

### Current models and production fit

Google lists `gemini-3.8-flash` as stable, updated September 2026. It accepts text, images, video, audio, and PDF and returns text. Its documented limits are 1,048,576 input tokens and 65,536 output tokens. Structured output, caching, batch execution, and function calling are supported. Thinking levels are low, medium, and high; `minimal` is explicitly unsupported for this model. [^1]

`gemini-3.5-flash-lite` is also stable with the same advertised input/output token limits and multimodal input types. It is a plausible cost-oriented model for simple descriptions and taxonomy assignment, but should be evaluated on the actual footage before promotion. [^2] The model catalog still labels `gemini-3.1-pro-preview` and `gemini-3-flash-preview` as preview. A “deep analysis” setting should initially use the stable model with a richer workflow, rather than assume the Pro name implies the best current production choice. [^3]

| Candidate | Proposed role | Initial posture |
| --- | --- | --- |
| `gemini-3.8-flash` | Default semantic analysis, complex clip questions, detailed metadata | Stable default; verify account access at runtime. |
| `gemini-3.5-flash-lite` | Bulk first pass, simple taxonomy assignment | Candidate for measured cost reduction. |
| `gemini-3.1-pro-preview` | Optional comparison on difficult footage | Explicit experimental setting; avoid silent fallback. |
| `gemini-3.5-transcribe` | Word-timed transcript candidate | Separate speech pipeline with its own limits. |

### Video sampling and temporal coverage

The current video guide distinguishes static sampling from agentic exploration. Static processing defaults to one frame per second. Agentic mode is documented for 3.8 Flash, 3.7 Flash, 3.6 Flash, and 3.5 Flash-Lite; it selectively loads frames, audio, and transcripts. Google reports up to 88% lower token use on long-form material. Custom frame rates and clipping parameters are supported in static mode. The guide estimates about 100 tokens per video second at low resolution and 300 at high resolution, including audio and metadata. [^4]

**Analytical implication:** selective exploration is attractive for targeted questions and long recordings. It does not by itself demonstrate that every frame or every possible tag was considered. Even static one-FPS sampling can miss a short insert or small logo. Preserve a coverage manifest containing analyzed time windows, sampling settings, audio availability, and unresolved regions. Use scene detection and targeted high-density checks to close known gaps.

Timestamp decimals should be preserved. However, a timestamp rendered as `00:01:02.417` does not establish millisecond accuracy. Store the model's estimated interval separately from decoded source frame timing. A reviewed or deterministic boundary may receive a stronger accuracy designation; a free-form model response may not.

### Structured extraction and files

Gemini supports JSON-schema-constrained output, but the supported schema is a subset, large/deep schemas may fail, and Google explicitly requires application validation of values. [^5] The application should validate finite timestamps, start-before-end, containment within the analyzed interval, taxonomy membership, maximum list sizes, and nonempty evidence. Rejected or repaired output should be recorded as such.

Google's current documentation contains a material limit discrepancy. The video-input table advertises paid uploads up to 20 GB and inline inputs below 100 MB, while the Files API guide still documents 2 GB per file, 20 GB per project, and 48-hour expiry; other prose on the video page still recommends Files API above 20 MB. Until the actual endpoint and account are tested, retain conservative 2 GB uploads and use Files API for substantial footage. Uploaded files are temporary analysis inputs, so the application must retain its own originals/proxies and re-upload expired inputs. [^4][^6]

### Speech and sound

The dedicated `gemini-3.5-transcribe` endpoint documents automatic language identification, diarization, word timestamps, and custom vocabulary. Its standard unary limit is one hour, falling to 30 minutes with diarization or word timestamps. It supports up to eight speakers, with attribution for three or more described as experimental; enabling word timestamps can reduce transcription accuracy. [^7]

For filmmakers, verbatim transcription and an editorially cleaned transcript are separate products. Preserve the verbatim evidence; generate cleaned text as a derived field. Do not populate dialogue from a silent clip, subtitles, a title card, or an inferred conversation. Store on-screen text, actual speech, music descriptions, and other sounds separately. Speaker labels should remain anonymous unless the project supplies a permitted identity mapping.

### Price and cost controls

At the verified date, standard Gemini 3.8 Flash input costs $0.75 per million tokens and output, including thinking, $3.75 per million through December 31, 2026. Published prices rise to $1.50/$7.50 on January 1, 2027. Standard 3.5 Flash-Lite is $0.30/$2.50 per million. The listed Gemini 3.8 batch rates are half the standard rates. [^8]

For an illustrative hour at 100 input tokens per second and 10,000 billable output/thinking tokens, the calculation is `360,000 × input_rate / 1,000,000 + 10,000 × output_rate / 1,000,000`: approximately **$0.3075** at current 3.8 Flash rates, **$0.615** after the announced change, and **$0.133** for 3.5 Flash-Lite. At 300 input tokens per second, the current 3.8 example becomes **$0.8475**, normally requiring splitting because 1.08 million input tokens exceeds its context limit. These are arithmetic scenarios, not measured bills. [^1][^33][^8]

Actual costs also include retries, overlapping windows, denser sampling, separate transcription, output size, storage, and compute. Agentic exploration has variable reasoning and loaded-media costs. Record the provider's complete usage object, distinguish observed from estimated cost, attach an effective date to price schedules, and use per-job budgets. “Deep” mode should explain what extra processing is bought.

### Privacy

For US usage, the distinction between unpaid and paid Gemini services is operationally important: unpaid content can be used to improve products and reviewed by people; paid API usage through a billing-enabled project is covered by different terms and is not used for product improvement. Paid prompts/responses can still be logged for limited abuse-monitoring purposes. The terms contain regional exceptions for EEA/Switzerland/UK. [^9]

Google Cloud's enterprise platform states that customer data is not used to train models without permission. Zero retention requires attention to feature-specific conditions: abuse monitoring, optional request logging, grounding, and stored interactions differ. The documented Interactions API default is `store=true`; achieving zero retention requires `store=false` along with other applicable controls. [^10] Confidential client footage should use a deployment profile whose actual contracts and retention settings match the client's requirements.

## TwelveLabs

### Pegasus 1.5: the strongest specialist to test for metadata

Pegasus 1.5 accepts video directly from an asset, raw URL, or base64, without the former pre-indexing step. It supports general analysis and custom temporal segmentation. Documented limits include 4 seconds to 2 hours, a 2 GB model-level file limit, a 261,120-token shared input/output context, and up to 98,304 output tokens. Full language support is English; other listed languages have partial support. [^11]

Its segmentation workflow closely matches professional logging: define segment types, attach reference images for products or logos, specify custom typed fields, and obtain start/end intervals. Up to ten definitions can be submitted and minimum/maximum segment duration can be controlled. [^12] This is especially relevant for client-specific brand occurrences and editor-defined event classes, where a fixed generic label vocabulary is insufficient.

Pegasus 1.2 was removed on August 18, 2026; current analysis requests must use 1.5. The release notes also document timestamp formatting and identify `pegasus1.5` as the model selector. [^13] Actual operation limits matter: synchronous Analyze is capped at one hour, asynchronous Analyze at two. Multipart asset upload supports larger files than the Pegasus model can analyze; upload success is therefore not proof of analysis eligibility. [^14]

**Recommendation:** benchmark Pegasus against Gemini on labeled product appearances, editorial events, transcript-linked moments, and fast montage footage. It is an attractive second adapter, but official capability claims do not establish higher accuracy for every filmmaking task. Segmentation output still requires range validation and human review.

### Marengo: retrieval and embeddings

Marengo 3.5, released August 31, 2026, produces 512-dimensional embeddings across video, audio, images, and documents. It adds composed multimodal queries, unified audio encoding, uncertainty vectors, and time-aligned metadata fusion. Its embeddings are incompatible with 3.0. The current `/search` API does not support 3.5: use 3.0 for the existing managed Search API, or query 3.5 embeddings in the application's own retrieval system. [^15]

The advertised absence of a model duration ceiling applies to asynchronous 3.5 content embedding, not every call. Synchronous video/audio embedding is limited to 30 seconds and 32 MB per source; uploads also have method-specific limits. [^14] The product should therefore distinguish query clips, corpus assets, embedding jobs, and analysis jobs.

The retrieval opportunity is substantial: a query can represent visual style, sound, dialogue, or their combination. But indexing every source into one undifferentiated vector loses useful structure. Retain time ranges, modality, project permissions, source asset IDs, and model version with every vector. Re-embedding should create a new index version, never mix incompatible model spaces.

### Cost and security

TwelveLabs' posted Developer rates are $1.75 per input video hour for Analyze plus $7.50 per million output tokens. Segment multiplies input duration by the number of segment definitions. Managed search is listed at $2.50 per indexed hour once, $0.09 per indexed hour per month for infrastructure, and $4 per thousand searches. The pricing page directs Marengo 3.5 search users to Jockey; core documentation explicitly describes self-managed querying. [^16]

A one-hour Segment request with five definitions therefore represents five billable input hours: $8.75 before output. A 1,000-hour managed search collection would imply $2,500 initial indexing and $90 monthly infrastructure, plus queries, under those posted rates. This arithmetic shows why a specialist segmentation pass should be selective and why ongoing index costs must be visible. [^16]

TwelveLabs documents TLS 1.2+ transport, AES-256-at-rest minimum, access controls, and audit practices. [^17] Its privacy policy says customer processor arrangements are governed by customer contracts and separately describes use of customer data/output to improve services. That page alone does **not** establish a universal no-training promise for every plan. Confirm the applicable contract, retention, region, and deletion behavior before sending unreleased client work. [^18]

## Traditional cloud video indexers

These systems remain useful where the required output is a known detector's structured result rather than open-ended interpretation.

| Service | Documented strengths | Best role in this platform |
| --- | --- | --- |
| Google Cloud Video Intelligence | Frame/shot/segment labels; objects, locations, activities, products; frame-level label sampling at one FPS | Baseline controlled labels and conventional annotations. [^19] |
| Amazon Rekognition Video | Technical cues, shot changes, black frames, credits, slates; frame numbers and SMPTE timecode output | Technical segmentation and broadcast preparation. [^20] |
| Azure AI Video Indexer | Transcription, OCR, scenes/shots/keyframes, editorial shot types, content and audio insights | An integrated enterprise indexing alternative, especially for Azure organizations. [^21] |

Rekognition explicitly documents frame-accurate timecodes for its segment results. [^20] This supports a useful distinction: use those results or a validated local detector for cut boundaries, while attaching semantic descriptions from a multimodal model. A frame number for a detected boundary still does not prove that every possible boundary was found.

Google's posted stored-video prices after the free allowance include $0.10/minute for labels, $0.05/minute for standalone shot detection, and $0.15/minute each for object tracking, OCR, or logo detection. Shot detection is free when used with label detection. [^22] Selecting several detectors can cost considerably more than a single generative pass, though they deliver different structured evidence. AWS separately charges each API applied to the same footage. [^23]

Azure has restricted facial/identity-related capabilities and authorization requirements; do not design general access around their availability. [^24] Its public pricing page did not expose a reliable numeric regional quote in the accessible content, so this report makes no price comparison for Azure. Obtain the actual region/preset quote for procurement. [^25]

## Open models and private deployments

Qwen3.5-35B-A3B is a relevant self-hosted multimodal candidate, with Apache-2.0 model licensing, 35 billion total parameters/3 billion activated, and a native 262,144-token context. Its official card reports Video-MME results of 82.5 without subtitles and 86.6 with subtitles. Those are vendor-reported benchmark results, not an agency-footage evaluation. [^26]

Qwen3-VL remains relevant where its video-specific tooling or existing deployment is useful. The original technical report describes 256K native multimodal context and video reasoning. [^27] Qwen3-VL-Embedding-8B provides text/image/video embeddings with a 32K context and selectable 64–4096 dimensions; a related reranker is available. [^28] This offers a practical private retrieval baseline to compare against TwelveLabs.

InternVL3.5 is another open visual baseline. Its documented video example loads sampled frames and presents a numbered sequence of images to the model. [^29] That is useful for controlled frame analysis, but the example does not establish a complete audio pipeline. Keep transcription as a separate component unless the chosen model explicitly supports it.

**Analytical judgment:** self-hosting is most compelling when media cannot leave a controlled environment, throughput is predictable, or domain-specific optimization provides measurable gains. Weights, KV cache, image tokens, decoding, batching, and the operations team all consume resources. Activated parameter count does not mean the remaining weights occupy no memory. No defensible per-hour self-hosted price can be stated without hardware, frame density, quantization, utilization, and latency requirements.

## What current benchmarks establish

Google's September 2026 model card reports LVBench accuracy of 87.8% for Gemini 3.8 agentic processing and 87.1% static, ahead of the comparison models listed there. These are Google-published measurements, not an independent head-to-head test of this application. [^30] LVBench tests long-video understanding across several task types; it is not a guarantee of complete metadata, frame-accurate logging, or recognizable brand identification. [^31]

The 2026 Video-MME-v2 paper explicitly targets weaknesses masked by older aggregate scores, including cross-frame consistency and temporal reasoning. It reports that reasoning gains depend on textual cues and can worsen purely visual performance. Its tested model versions and input procedures differ from current production endpoints. [^32] This reinforces a workload-specific evaluation rather than choosing a provider by a single leaderboard.

### Evaluation design

Build a small, rights-cleared, representative corpus before claiming the product is top-tier. Include agency ads, fast social edits, branded products, documentary interviews, quiet B-roll, dialogue scenes, animation, screen recordings, low-light footage, and at least several long recordings. A starting evaluation might contain 60–100 assets with deliberately annotated difficult moments. This is a proposed test design, not an industry standard.

| Measure | Test | Why it matters |
| --- | --- | --- |
| Tag precision and recall | Compare approved taxonomy labels to independent annotations; report by category | Generic correctness can conceal poor brand recall. |
| Temporal localization | Boundary error and interval overlap, with separate results for short events | A useful tag at the wrong moment frustrates editors. |
| Retrieval | Recall@K and ranked relevance on actual agency/filmmaker queries | The library must return usable shots, including unfamiliar wording. |
| Verbatim evidence | Speech word error and on-screen text accuracy separately | Dialogue and visible copy have different sources. |
| Unsupported assertions | Rate of guessed identities, locations, camera/lens settings, and invented speech | Plausible false metadata contaminates search and exports. |
| Correction effort | Time from upload to approved useful metadata | User value includes human cleanup, not just inference speed. |
| Operational reliability | Completion rate, retries, p50/p95 latency, output truncation, and measured cost | Quality must survive long and difficult jobs. |

Evaluate the same normalized proxies and task definitions, and keep provider-specific enhanced modes as separate treatments. Include silent inputs and negative examples. Do not score a blank result as a successful analysis, or score a confidently guessed field as correct merely because its wording sounds reasonable. An optional second model should be adopted only when its incremental improvement justifies its cost and operational burden.

## Metadata and pipeline contract

The following is a proposed application contract, derived from the workflow requirements rather than a vendor's output format.

1. **Asset:** original filename, content hash, project, source URI, technical probe results, audio presence, source timecode, proxy relationship, and rights information supplied by the project.
2. **Analysis run:** provider/model, prompt/schema versions, input windows, sampling/resolution, requested mode, start/end/status, usage, cost basis, retry count, and warnings.
3. **Timed segment:** decimal seconds relative to the source, shot/scene/event type, description, controlled tags, visible objects/actions, setting, shot size, camera movement, lighting, visible text, brands/logos, and separate audio evidence.
4. **Evidence:** modality, observed time range, representative frame reference or verbatim transcript span, ambiguity, and analysis coverage. Model-generated confidence is labeled uncalibrated until evaluated.
5. **Review:** proposed/approved/rejected status, reviewer edits, timestamps, prior values, and validation warnings. Human-confirmed values survive reanalysis.

Fields such as exact city, person identity, named camera/lens, ethnicity, intent, rights clearance, or consent should not be guessed from appearance. A model can describe “urban street at night” or “shallow depth of field”; it cannot reliably certify an undisclosed camera model or a release agreement. Location names and brand names require explicit visual/audio evidence or project-provided metadata, with provenance.

The first production pipeline should probe and retain media, generate browser-playable proxies as needed, create durable jobs, analyze bounded windows, validate and persist metadata, and make all results editable. Subsequent iterations should add reliable cut detection, dedicated transcripts, hybrid retrieval, and NLE-friendly export. This architecture can improve continuously as model providers change, without rebuilding the library and review system each time.

## Sources

All sources were accessed September 9, 2026. Dates below are publication/update dates where clearly available; otherwise the source is a live reference. Prices are USD unless stated otherwise.

[^1]: Google. [Gemini 3.8 Flash model reference](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). September 2, 2026.
[^2]: Google. [Gemini 3.5 Flash-Lite model reference](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite). July 30, 2026.
[^3]: Google. [Gemini API model catalog](https://ai.google.dev/gemini-api/docs/models). Live reference.
[^4]: Google. [Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding). Live reference; contains conflicting size guidance noted above.
[^5]: Google. [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output). September 2, 2026.
[^6]: Google. [Files API](https://ai.google.dev/gemini-api/docs/files). September 4, 2026.
[^7]: Google. [Audio transcription](https://ai.google.dev/gemini-api/docs/transcribe). Live reference.
[^8]: Google. [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing). Live price schedule.
[^9]: Google. [Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms). Live terms.
[^10]: Google Cloud. [Gemini Enterprise Agent Platform and zero data retention](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention). Live reference, redirected from the former Vertex AI data-governance URL.
[^11]: TwelveLabs. [Pegasus model reference](https://docs.twelvelabs.io/docs/concepts/models/pegasus). Live reference.
[^12]: TwelveLabs. [Segment videos](https://docs.twelvelabs.io/v1.3/docs/guides/segment-videos). Live guide.
[^13]: TwelveLabs. [Release notes](https://docs.twelvelabs.io/docs/get-started/release-notes). Relevant entries April–August 2026.
[^14]: TwelveLabs. [Upload and processing methods](https://docs.twelvelabs.io/docs/concepts/upload-methods). Live reference.
[^15]: TwelveLabs. [Marengo 3.5](https://docs.twelvelabs.io/v1.3/docs/concepts/models/marengo/marengo-3-5). Live model reference.
[^16]: TwelveLabs. [API pricing](https://www.twelvelabs.io/pricing). Live price schedule; distinguish current rates from legacy FAQ text.
[^17]: TwelveLabs. [Security and compliance](https://www.twelvelabs.io/security). Live security overview.
[^18]: TwelveLabs. [Privacy policy](https://www.twelvelabs.io/legal/privacy-policy). January 12, 2026.
[^19]: Google Cloud. [Analyze videos for labels](https://docs.cloud.google.com/video-intelligence/docs/analyze-labels). Live reference.
[^20]: AWS. [Detecting video segments in stored video](https://docs.aws.amazon.com/rekognition/latest/dg/segments.html). Live reference.
[^21]: Microsoft. [What is Azure AI Video Indexer?](https://learn.microsoft.com/en-us/azure/azure-video-indexer/video-indexer-overview). Live reference.
[^22]: Google Cloud. [Video Intelligence API pricing](https://cloud.google.com/products/video-intelligence/pricing). Live price schedule.
[^23]: AWS. [Amazon Rekognition pricing](https://aws.amazon.com/rekognition/pricing/). Live price schedule.
[^24]: Microsoft. [Transparency Note for Azure AI Video Indexer](https://learn.microsoft.com/en-us/legal/azure-video-indexer/transparency-note). Live reference.
[^25]: Microsoft. [Azure AI Video Indexer pricing](https://azure.microsoft.com/en-us/pricing/details/video-indexer/). Live regional price page; no numeric quote relied on here.
[^26]: Qwen. [Qwen3.5-35B-A3B model card](https://huggingface.co/Qwen/Qwen3.5-35B-A3B). Official model repository, live reference.
[^27]: Qwen team. [Qwen3-VL Technical Report](https://arxiv.org/abs/2511.21631). November 2025.
[^28]: Qwen. [Qwen3-VL-Embedding-8B model card](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B). Official model repository, live reference.
[^29]: OpenGVLab. [InternVL3.5-8B model card](https://huggingface.co/OpenGVLab/InternVL3_5-8B). Official model repository, live reference.
[^30]: Google DeepMind. [Gemini 3.8 Flash model card](https://deepmind.google/models/model-cards/gemini-3-8-flash/). September 2, 2026.
[^31]: LVBench team. [LVBench benchmark and methodology](https://lvbench.github.io/). Associated with Wang et al., 2024/ICCV 2025; visible leaderboard does not reflect every September 2026 release.
[^32]: Fu et al. [Video-MME-v2: Towards the Next Stage in Benchmarks for Comprehensive Video Understanding](https://arxiv.org/abs/2604.05015). April 6, 2026.

[^33]: Google. [Understand and count tokens](https://ai.google.dev/gemini-api/docs/tokens). September 4, 2026.
