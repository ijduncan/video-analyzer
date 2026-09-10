PRO_SCENE_ANALYSIS_PROMPT = """Analyze this scene for an editor, filmmaker, or creative agency.
Return the supplied JSON schema with concrete observations, useful interpretations explicitly framed as such,
and short time-linked evidence for significant claims.

Visual analysis: visible lighting quality/direction, palette/contrast, composition, set/props/wardrobe,
and apparent graphics or visual effects. Describe the appearance; do not assert a named LUT, exact color
 temperature, specific camera/lens, green-screen method or production budget without supplied evidence.
Motion/editing: observed rhythm, cuts/transitions, movement and focus changes. Distinguish camera motion
from object motion. Avoid claiming a technical measurement that was not provided.
Audio: dialogue only from words actually heard, music and sound design separately. Use anonymous speaker
labels when needed. Never infer a transcript from visible captions or lip movements. Leave absent audio empty.
Narrative: describe the apparent story beat, creative tone, readable on-screen text, identifiable products/logos,
and observable people/actions. Creative interpretations are suggestions, not facts about internal intent.
Evidence: directly observable details with modality, description, and source-relative start/end timestamps
within this scene. Include uncertainty in analysis_warnings and keep review_status unreviewed.
"""
