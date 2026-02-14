SUMMARY_PROMPT = """Based on the full video, provide a comprehensive summary:

1. A one-paragraph executive summary of the video content
2. Overall genre/category (commercial, narrative film, documentary, music video, corporate, social media, tutorial, etc.)
3. Estimated production value (low/medium/high/premium)
4. Target audience assessment
5. Overall visual style and tone
6. Key themes and messaging
7. Total runtime, number of scenes, number of shots
8. Any notable technical achievements or issues

Return as a JSON object with this structure:
{
  "executive_summary": "string",
  "genre_category": "string",
  "production_value": "string",
  "target_audience": "string",
  "visual_style": "string",
  "key_themes": ["string"],
  "total_runtime": "string",
  "total_scenes": number,
  "total_shots": number,
  "notable_observations": "string"
}"""
