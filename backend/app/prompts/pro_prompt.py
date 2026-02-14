PRO_SCENE_ANALYSIS_PROMPT = """You are an expert cinematographer, editor, and narrative analyst.

Analyze this video segment in exhaustive detail. Provide:

## Visual Analysis
- **Lighting**: Type (natural, artificial, mixed), direction, quality (hard/soft), color temperature, any notable lighting setups (Rembrandt, butterfly, rim, etc.)
- **Color Palette**: Dominant colors, color grading/LUT style, saturation level, contrast
- **Composition**: Rule of thirds, leading lines, symmetry, depth of field, negative space
- **Production Design**: Set design, props, wardrobe, location details
- **Visual Effects**: Any VFX, CGI, compositing, green screen, motion graphics, titles/supers

## Motion & Editing
- **Pacing**: Shot duration average, rhythm, any speed ramping or slow motion
- **Transitions**: Cut types (hard cut, dissolve, wipe, match cut, J-cut, L-cut)
- **Camera Technique**: Lens choice (wide/telephoto feel), stabilization, focus pulls

## Audio Analysis
- **Dialogue**: Full transcription with speaker identification if possible
- **Music**: Genre, tempo, instrumentation, mood, whether diegetic or non-diegetic
- **Sound Design**: Specific sound effects, foley, ambient beds, audio transitions

## Narrative & Context
- **Story Beat**: What narrative purpose does this scene serve?
- **Emotional Tone**: What feeling is this scene creating for the viewer?
- **Text/Graphics**: Any on-screen text, titles, lower thirds, subtitles — transcribe exactly
- **Brand/Product**: Any visible brands, products, logos
- **People**: Number of people, actions, expressions, body language

Return the analysis as a JSON object with this structure:
{
  "scene_number": number,
  "visual_analysis": {
    "lighting": "string",
    "color_palette": "string",
    "composition": "string",
    "production_design": "string",
    "visual_effects": "string"
  },
  "motion_editing": {
    "pacing": "string",
    "transitions": "string",
    "camera_technique": "string"
  },
  "audio_analysis": {
    "dialogue": "string",
    "music": "string",
    "sound_design": "string"
  },
  "narrative_context": {
    "story_beat": "string",
    "emotional_tone": "string",
    "text_graphics": "string",
    "brands_products": "string",
    "people": "string"
  }
}"""
