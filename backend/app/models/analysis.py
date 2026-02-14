from __future__ import annotations

from pydantic import BaseModel


# --- Pass 1: Flash Scene Detection ---

class Shot(BaseModel):
    shot_number: int
    start_time: str  # MM:SS
    end_time: str  # MM:SS
    shot_type: str
    camera_movement: str
    visual_description: str
    audio_notes: str
    subjects: list[str] = []
    dominant_colors: list[str] = []
    mood: str = ""


class Scene(BaseModel):
    scene_number: int
    scene_title: str
    scene_description: str
    start_time: str  # MM:SS
    end_time: str  # MM:SS
    shots: list[Shot] = []


class FlashAnalysis(BaseModel):
    total_duration: str  # MM:SS
    total_shots: int
    total_scenes: int
    scenes: list[Scene]


# --- Pass 2: Pro Deep Analysis ---

class CinematographyDetail(BaseModel):
    lighting: str = ""
    color_palette: str = ""
    composition: str = ""
    production_design: str = ""
    visual_effects: str = ""


class MotionEditingDetail(BaseModel):
    pacing: str = ""
    transitions: str = ""
    camera_technique: str = ""


class AudioDetail(BaseModel):
    dialogue: str = ""
    music: str = ""
    sound_design: str = ""


class NarrativeDetail(BaseModel):
    story_beat: str = ""
    emotional_tone: str = ""
    text_graphics: str = ""
    brands_products: str = ""
    people: str = ""


class SceneDeepAnalysis(BaseModel):
    scene_number: int
    visual_analysis: CinematographyDetail = CinematographyDetail()
    motion_editing: MotionEditingDetail = MotionEditingDetail()
    audio_analysis: AudioDetail = AudioDetail()
    narrative_context: NarrativeDetail = NarrativeDetail()


# --- Pass 3: Full Summary ---

class VideoSummary(BaseModel):
    executive_summary: str = ""
    genre_category: str = ""
    production_value: str = ""
    target_audience: str = ""
    visual_style: str = ""
    key_themes: list[str] = []
    total_runtime: str = ""
    total_scenes: int = 0
    total_shots: int = 0
    notable_observations: str = ""
