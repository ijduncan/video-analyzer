SCENE_DETECTION_PROMPT = """Identify the narrative scenes or editorial sections of this video.
A scene is a coherent event, setting, or editorial section. A camera cut alone does not require a new scene.
For interviews, separate substantial topic/setting changes; for narrative material, use changes in event, setting or time.
For short ads and trailers, group coherent sequences without inventing arbitrary scene counts.
Use short descriptive scene titles and descriptions grounded in the footage.

Return the supplied JSON schema with the source duration, total scene count and scene intervals.
All times are source-relative MM:SS.mmm or HH:MM:SS.mmm. Preserve fractional seconds when observed.
Arrange scenes chronologically without overlap. Aim to cover the available source from beginning to end,
but report uncertain boundaries or unexamined portions in analysis_warnings rather than claiming exhaustive coverage.
If a trustworthy duration from media metadata is supplied, use it instead of estimating runtime.
Do not claim frame-accurate boundaries. If the input cannot be analyzed, return no scenes and a clear warning.
"""
