FLASH_SCENE_DETECTION_PROMPT = """You are a professional video analyst specializing in post-production and editorial breakdown.

Analyze this video and identify every distinct shot and scene. For each shot, provide:

1. **Timestamp**: Start and end time (MM:SS format)
2. **Shot Type**: e.g., Wide Shot (WS), Medium Shot (MS), Close-Up (CU), Extreme Close-Up (ECU), Over-the-Shoulder (OTS), POV, Aerial/Drone, Establishing Shot, Insert Shot, Two-Shot, etc.
3. **Camera Movement**: Static, Pan (L/R), Tilt (Up/Down), Dolly (In/Out), Tracking, Crane, Handheld, Steadicam, Zoom (In/Out), Whip Pan, etc.
4. **Scene Boundary**: Boolean — does this shot begin a new scene? If yes, provide a scene number and brief scene description.
5. **Brief Visual Description**: One sentence describing what is visually happening in the shot.
6. **Audio Notes**: What is heard — dialogue (paraphrase), music, sound effects, ambient sound, silence.

Group shots into scenes. A new scene starts when there is a significant change in location, time, or narrative context.

Return the results as a JSON object with this structure:
{
  "total_duration": "MM:SS",
  "total_shots": number,
  "total_scenes": number,
  "scenes": [
    {
      "scene_number": 1,
      "scene_title": "string",
      "scene_description": "string",
      "start_time": "MM:SS",
      "end_time": "MM:SS",
      "shots": [
        {
          "shot_number": 1,
          "start_time": "MM:SS",
          "end_time": "MM:SS",
          "shot_type": "string",
          "camera_movement": "string",
          "visual_description": "string",
          "audio_notes": "string",
          "subjects": ["string"],
          "dominant_colors": ["string"],
          "mood": "string"
        }
      ]
    }
  ]
}

Be thorough and precise with timestamps. Every frame of the video should be accounted for within a shot."""
