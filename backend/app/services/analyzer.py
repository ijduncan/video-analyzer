"""Durable, evidence-bearing analysis stages; execution is owned by the job runner."""
import asyncio
import json
import logging
import math
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.config import settings
from app.models.analysis import FlashAnalysis, Scene
from app.services.analysis_support import validate_scenes, validate_shots, time_to_seconds
from app.services.cost_estimator import estimate_cost
from app.services.custom_pass import run_custom_pass
from app.services.flash_pass import run_scene_detection, run_shot_detection
from app.services.job_store import Job, get_job, update_job
from app.services.pro_pass import run_pro_scene
from app.services.shot_matching import run_shot_matching
from app.services.summary_pass import run_summary_pass
from app.services.thumbnail_service import extract_thumbnails

logger = logging.getLogger(__name__)


def _event(event_name: str, **data) -> dict:
    return {"event": event_name, "data": json.dumps(data)}


def _failure(stage: str, error: Exception) -> str:
    """Provider messages can contain credential-bearing URLs or private input."""
    logger.warning("%s failed (%s)", stage, type(error).__name__)
    if isinstance(error, (ValueError, TypeError)):
        return f"{stage} did not return valid analysis. Retry this asset or use another configured model."
    if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
        return f"{stage} timed out. Retry this asset."
    return f"{stage} could not complete. Check provider access, model availability and quota, then retry."


def _shot_spans(result: dict | None) -> dict:
    spans = {}
    for scene in (result or {}).get("scenes", []):
        for shot in scene.get("shots", []):
            try:
                spans[str(shot["shot_number"])] = (time_to_seconds(shot["start_time"]),
                                                   time_to_seconds(shot["end_time"]))
            except (KeyError, ValueError):
                continue
    return spans


async def run_analysis(
    job: Job, fps: float = 1.0, mode: str = "flash_pro", custom_prompt: str | None = None,
    api_key: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Yield compatible progress events while persisting every completed stage.

    The job runner ensures the remote file is active before calling this function.
    Model proposals are stored separately from human annotations and metadata.
    """
    usage_records: list[dict] = []
    warnings = ["AI-generated timestamps are approximate; review metadata before editorial use."]
    thumb_task = None
    flash_dict = None
    deep_results, matches_list = [], []
    summary_dict = custom_result_dict = None
    transcript = []
    previous_config = dict(job.analysis_config)
    archived = False
    previous_annotations, previous_spans = {}, {}

    def persist(**changes):
        # update_job reloads the durable record, so unrelated human edits survive.
        update_job(job.job_id, warnings=list(dict.fromkeys(warnings)),
                   cost_estimate=estimate_cost(usage_records=usage_records), **changes)

    def persist_replacement(result: dict):
        """Archive the prior run once and bind reviews only to identical intervals."""
        nonlocal archived, previous_annotations, previous_spans
        latest = get_job(job.job_id)
        if latest is None:
            raise ValueError("Asset no longer exists")
        changes = {}
        if not archived:
            previous_annotations = dict(latest.shot_annotations)
            previous_spans = _shot_spans(latest.flash_result)
            if latest.flash_result:
                snapshot = {
                    "archived_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_config": previous_config, "flash_result": latest.flash_result,
                    "deep_results": latest.deep_results, "summary": latest.summary,
                    "shot_annotations": latest.shot_annotations, "shot_matches": latest.shot_matches,
                    "transcript": latest.transcript, "custom_result": latest.custom_result,
                    "cost_estimate": job.cost_estimate,
                }
                changes["analysis_history"] = (list(latest.analysis_history) + [snapshot])[-10:]
            changes.update(deep_results=[], summary=None, shot_matches=[], custom_result=None)
            archived = True
        new_spans = _shot_spans(result)
        annotations = {key: value for key, value in previous_annotations.items()
                       if key in new_spans and previous_spans.get(key) == new_spans[key]}
        latest_spans = _shot_spans(latest.flash_result)
        annotations.update({key: value for key, value in latest.shot_annotations.items()
                            if key in new_spans and latest_spans.get(key) == new_spans[key]})
        persist(flash_result=result, transcript=transcript, shot_annotations=annotations, **changes)

    try:
        if mode not in {"flash_only", "flash_pro"}:
            raise ValueError("Unknown analysis mode")
        if not math.isfinite(fps) or not 0.1 <= fps <= 30:
            raise ValueError("Sampling FPS must be between 0.1 and 30")
        duration = job.technical.get("duration_seconds")
        if duration is not None:
            duration = time_to_seconds(duration)
            if duration <= 0:
                raise ValueError("Source duration must be positive")
        config = dict(job.analysis_config)
        config.update({"provider": "gemini", "analysis_model": settings.gemini_analysis_model,
                       "deep_model": settings.gemini_deep_model, "fps": fps, "mode": mode,
                       "schema_version": "2.0", "processing": "static",
                       "timestamp_accuracy": "approximate", "started_at": datetime.now(timezone.utc).isoformat()})
        persist(status="analyzing", error=None, current_pass=1, current_scene=None,
                progress="Finding editorial scenes", analysis_config=config)
        yield _event("pass_start", **{"pass": 1, "name": "Scene analysis"})
        scenes_result, usage = await run_scene_detection(
            job.file_uri, job.mime_type, api_key=api_key, duration_seconds=duration,
        )
        usage_records.append(usage)
        scenes_result = validate_scenes(scenes_result, duration)
        warnings.extend(scenes_result.analysis_warnings)
        yield _event("scenes_detected", total_scenes=scenes_result.total_scenes,
                     total_duration=scenes_result.total_duration)
        yield _event("pass_start", **{"pass": 1, "name": "Shot metadata and evidence"})
        assembled_scenes = []
        shot_counter = 1
        for outline in scenes_result.scenes:
            persist(current_scene=outline.scene_number, total_scenes=scenes_result.total_scenes,
                    progress=f"Logging scene {outline.scene_number} of {scenes_result.total_scenes}")
            yield _event("shot_detection_progress", scene=outline.scene_number,
                         total=scenes_result.total_scenes, scene_title=outline.scene_title)
            try:
                shots, usage = await run_shot_detection(
                    job.file_uri, job.mime_type, outline, shot_counter, fps, api_key=api_key,
                )
                usage_records.append(usage)
                shots = validate_shots(shots, time_to_seconds(outline.start_time),
                                       time_to_seconds(outline.end_time), shot_counter)
                for shot in shots:
                    if job.technical.get("has_audio") is False:
                        if shot.transcript or any(e.modality in {"audio", "both"} for e in shot.evidence):
                            shot.analysis_warnings.append("Audio claims removed: source has no audio stream.")
                        shot.transcript = ""
                        shot.audio_notes = "No audio stream in source."
                        shot.evidence = [e for e in shot.evidence if e.modality == "visual"]
                    if shot.transcript.strip():
                        transcript.append({"shot_number": shot.shot_number,
                                           "start_time": shot.start_time, "end_time": shot.end_time,
                                           "text": shot.transcript, "source": "model_transcription",
                                           "review_status": "unreviewed", "timestamp_accuracy": "approximate"})
                    warnings.extend(f"Shot {shot.shot_number}: {w}" for w in shot.analysis_warnings)
            except Exception as error:
                message = _failure(f"Shot analysis for scene {outline.scene_number}", error)
                warnings.append(message)
                shots = []
                yield _event("error_event", message=message, recoverable=True)
            assembled_scenes.append(Scene(
                scene_number=outline.scene_number, scene_title=outline.scene_title,
                scene_description=outline.scene_description, start_time=outline.start_time,
                end_time=outline.end_time, shots=shots,
            ))
            shot_counter += len(shots)
            flash_result = FlashAnalysis(
                total_duration=scenes_result.total_duration, total_scenes=len(assembled_scenes),
                total_shots=shot_counter - 1, scenes=assembled_scenes,
                analysis_warnings=list(dict.fromkeys(warnings)), model=settings.gemini_analysis_model,
            )
            flash_dict = flash_result.model_dump()
            if shot_counter > 1:
                persist_replacement(flash_dict)
            elif not job.flash_result:
                persist(flash_result=flash_dict, transcript=transcript)
        if shot_counter == 1:
            raise ValueError("No valid shot metadata was generated")
        persist(flash_result=flash_dict, total_scenes=len(assembled_scenes))
        yield _event("pass_complete", **{"pass": 1, "result": flash_dict})

        if job.local_path:
            thumb_task = asyncio.create_task(extract_thumbnails(
                job.local_path, job.job_id, flash_dict["scenes"], settings.upload_dir,
            ))
        if mode == "flash_pro":
            persist(current_pass=2, progress="Building detailed scene notes")
            yield _event("pass_start", **{"pass": 2, "name": "Detailed scene analysis"})
            for scene in flash_result.scenes:
                persist(current_scene=scene.scene_number,
                        progress=f"Detailed notes for scene {scene.scene_number} of {len(assembled_scenes)}")
                yield _event("scene_start", scene=scene.scene_number, total=len(assembled_scenes))
                try:
                    deep, usage = await run_pro_scene(job.file_uri, job.mime_type, scene, api_key=api_key)
                    usage_records.append(usage)
                    if job.technical.get("has_audio") is False:
                        deep.audio_analysis.dialogue = ""
                        deep.audio_analysis.music = ""
                        deep.audio_analysis.sound_design = "No audio stream in source."
                        deep.evidence = [e for e in deep.evidence if e.modality == "visual"]
                    deep_dict = deep.model_dump()
                    deep_results.append(deep_dict)
                    warnings.extend(deep.analysis_warnings)
                    persist(deep_results=deep_results)
                    yield _event("scene_complete", scene=scene.scene_number, result=deep_dict)
                except Exception as error:
                    message = _failure(f"Detailed analysis for scene {scene.scene_number}", error)
                    warnings.append(message)
                    persist()
                    yield _event("error_event", message=message, recoverable=True)
            yield _event("pass_complete", **{"pass": 2})
            persist(current_pass=3, progress="Writing the editorial summary")
            yield _event("pass_start", **{"pass": 3, "name": "Editorial summary"})
            try:
                summary, usage = await run_summary_pass(job.file_uri, job.mime_type, flash_result, api_key=api_key)
                usage_records.append(usage)
                summary_dict = summary.model_dump()
                persist(summary=summary_dict)
                yield _event("pass_complete", **{"pass": 3, "result": summary_dict})
            except Exception as error:
                message = _failure("Summary generation", error)
                warnings.append(message)
                persist()
                yield _event("error_event", message=message, recoverable=True)
            try:
                persist(progress="Finding visually related shots")
                yield _event("pass_start", **{"pass": 0, "name": "Related shots"})
                matches_list, usage = await run_shot_matching(job.file_uri, job.mime_type, flash_dict, api_key=api_key)
                usage_records.append(usage)
                persist(shot_matches=matches_list)
                yield _event("matches_complete", matches=matches_list)
            except Exception as error:
                message = _failure("Related-shot analysis", error)
                warnings.append(message)
                persist()
                yield _event("error_event", message=message, recoverable=True)

        if custom_prompt:
            persist(current_pass=4, custom_prompt=custom_prompt, progress="Running the custom analysis brief")
            yield _event("pass_start", **{"pass": 4, "name": "Custom analysis"})
            try:
                custom_result_dict, usage = await run_custom_pass(
                    job.file_uri, job.mime_type, custom_prompt, api_key=api_key,
                )
                usage_records.append(usage)
                persist(custom_result=custom_result_dict)
                yield _event("custom_complete", result=custom_result_dict)
            except Exception as error:
                message = _failure("Custom analysis", error)
                warnings.append(message)
                persist()
                yield _event("error_event", message=message, recoverable=True)
        if thumb_task:
            try:
                await asyncio.wait_for(thumb_task, timeout=45)
                yield _event("thumbnails_ready", job_id=job.job_id)
            except Exception as error:
                warnings.append(_failure("Thumbnail generation", error))
        persist(status="complete", current_pass=None, current_scene=None,
                deep_results=deep_results, summary=summary_dict, custom_result=custom_result_dict,
                shot_matches=matches_list, progress="Analysis ready for review")
        yield _event("analysis_complete", flash=flash_dict, deep=deep_results, summary=summary_dict,
                     custom=custom_result_dict, matches=matches_list, warnings=list(dict.fromkeys(warnings)),
                     cost_estimate=estimate_cost(usage_records=usage_records))
    except Exception as error:
        message = _failure("Analysis", error)
        warnings.append(message)
        persist(status="error", error=message, progress="Analysis needs attention; completed stages saved")
        yield _event("error_event", message=message, recoverable=False)
    finally:
        if thumb_task and not thumb_task.done():
            thumb_task.cancel()
            try:
                await thumb_task
            except (asyncio.CancelledError, Exception):
                pass
