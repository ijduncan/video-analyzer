import asyncio
import json
import logging
from typing import AsyncGenerator

from app.config import settings
from app.models.analysis import FlashAnalysis
from app.services.cost_estimator import estimate_cost
from app.services.custom_pass import run_custom_pass
from app.services.flash_pass import run_flash_pass
from app.services.job_store import Job, update_job
from app.services.pro_pass import run_pro_scene
from app.services.shot_matching import run_shot_matching
from app.services.summary_pass import run_summary_pass
from app.services.thumbnail_service import extract_thumbnails

logger = logging.getLogger(__name__)


async def run_analysis(
    job: Job, fps: float = 1.0, mode: str = "flash_pro", custom_prompt: str | None = None,
    api_key: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Run the full analysis pipeline, yielding SSE events."""

    flash_usage = {}
    pro_usage_total = {"input_tokens": 0, "output_tokens": 0}
    summary_usage = {}

    try:
        # --- Pass 1: Scene Detection (Flash) ---
        update_job(job.job_id, status="analyzing", current_pass=1)
        yield {"event": "pass_start", "data": json.dumps({"pass": 1, "name": "Scene Detection (Flash)"})}

        flash_result, flash_usage = await run_flash_pass(job.file_uri, job.mime_type, fps, api_key=api_key)
        flash_dict = flash_result.model_dump()

        update_job(
            job.job_id,
            flash_result=flash_dict,
            total_scenes=flash_result.total_scenes,
        )
        yield {
            "event": "pass_complete",
            "data": json.dumps({"pass": 1, "result": flash_dict}),
        }

        # Kick off thumbnail extraction in background (skip if no local file)
        thumb_task = None
        if job.local_path:
            thumb_task = asyncio.create_task(
                extract_thumbnails(job.local_path, job.job_id, flash_dict["scenes"], settings.upload_dir)
            )

        if mode == "flash_only":
            if thumb_task:
                try:
                    await thumb_task
                    yield {"event": "thumbnails_ready", "data": json.dumps({"job_id": job.job_id})}
                except Exception as e:
                    logger.warning(f"Thumbnail extraction failed: {e}")
            cost = estimate_cost(
                flash_input=flash_usage.get("input_tokens", 0),
                flash_output=flash_usage.get("output_tokens", 0),
            )
            update_job(job.job_id, status="complete", cost_estimate=cost)
            yield {
                "event": "analysis_complete",
                "data": json.dumps({
                    "flash": flash_dict,
                    "deep": [],
                    "summary": None,
                    "cost_estimate": cost,
                }),
            }
            return

        # --- Pass 2: Deep Analysis (Pro) per scene ---
        update_job(job.job_id, current_pass=2)
        yield {"event": "pass_start", "data": json.dumps({"pass": 2, "name": "Deep Analysis (Pro)"})}

        deep_results = []
        total_scenes = len(flash_result.scenes)

        for i, scene in enumerate(flash_result.scenes):
            scene_num = i + 1
            update_job(job.job_id, current_scene=scene_num)
            yield {
                "event": "scene_start",
                "data": json.dumps({"scene": scene_num, "total": total_scenes}),
            }

            try:
                deep, usage = await run_pro_scene(job.file_uri, job.mime_type, scene, api_key=api_key)
                deep_dict = deep.model_dump()
                deep_results.append(deep_dict)
                pro_usage_total["input_tokens"] += usage.get("input_tokens", 0)
                pro_usage_total["output_tokens"] += usage.get("output_tokens", 0)

                yield {
                    "event": "scene_complete",
                    "data": json.dumps({"scene": scene_num, "result": deep_dict}),
                }
            except Exception as e:
                logger.error(f"Pro pass failed for scene {scene_num}: {e}")
                yield {
                    "event": "error_event",
                    "data": json.dumps({
                        "message": f"Deep analysis failed for scene {scene_num}: {str(e)}",
                        "recoverable": True,
                    }),
                }

        update_job(job.job_id, deep_results=deep_results)
        yield {"event": "pass_complete", "data": json.dumps({"pass": 2})}

        # --- Pass 3: Full Summary (Pro) ---
        update_job(job.job_id, current_pass=3)
        yield {"event": "pass_start", "data": json.dumps({"pass": 3, "name": "Full Summary (Pro)"})}

        try:
            summary, summary_usage = await run_summary_pass(
                job.file_uri, job.mime_type, flash_result, api_key=api_key,
            )
            summary_dict = summary.model_dump()
            update_job(job.job_id, summary=summary_dict)
            yield {
                "event": "pass_complete",
                "data": json.dumps({"pass": 3, "result": summary_dict}),
            }
        except Exception as e:
            logger.error(f"Summary pass failed: {e}")
            summary_dict = None
            yield {
                "event": "error_event",
                "data": json.dumps({
                    "message": f"Summary generation failed: {str(e)}",
                    "recoverable": True,
                }),
            }

        # --- Shot Matching (Flash) ---
        match_usage = {}
        matches_list = []
        try:
            yield {"event": "pass_start", "data": json.dumps({"pass": 0, "name": "Shot Matching"})}
            matches_list, match_usage = await run_shot_matching(
                job.file_uri, job.mime_type, flash_dict, api_key=api_key,
            )
            yield {
                "event": "matches_complete",
                "data": json.dumps({"matches": matches_list}),
            }
        except Exception as e:
            logger.warning(f"Shot matching failed: {e}")
            yield {
                "event": "error_event",
                "data": json.dumps({
                    "message": f"Shot matching failed: {str(e)}",
                    "recoverable": True,
                }),
            }

        # --- Pass 4: Custom Prompt (optional) ---
        custom_usage = {}
        custom_result_dict = None
        if custom_prompt:
            update_job(job.job_id, current_pass=4, custom_prompt=custom_prompt)
            yield {"event": "pass_start", "data": json.dumps({"pass": 4, "name": "Custom Analysis"})}

            try:
                custom_result, custom_usage = await run_custom_pass(
                    job.file_uri, job.mime_type, custom_prompt, api_key=api_key,
                )
                custom_result_dict = custom_result
                update_job(job.job_id, custom_result=custom_result_dict)
                yield {
                    "event": "custom_complete",
                    "data": json.dumps({"result": custom_result_dict}),
                }
            except Exception as e:
                logger.error(f"Custom pass failed: {e}")
                yield {
                    "event": "error_event",
                    "data": json.dumps({
                        "message": f"Custom analysis failed: {str(e)}",
                        "recoverable": True,
                    }),
                }

        # --- Wait for thumbnails ---
        if thumb_task:
            try:
                await thumb_task
                yield {"event": "thumbnails_ready", "data": json.dumps({"job_id": job.job_id})}
            except Exception as e:
                logger.warning(f"Thumbnail extraction failed: {e}")

        # --- Complete ---
        cost = estimate_cost(
            flash_input=flash_usage.get("input_tokens", 0) + match_usage.get("input_tokens", 0),
            flash_output=flash_usage.get("output_tokens", 0) + match_usage.get("output_tokens", 0),
            pro_input=pro_usage_total["input_tokens"] + summary_usage.get("input_tokens", 0) + custom_usage.get("input_tokens", 0),
            pro_output=pro_usage_total["output_tokens"] + summary_usage.get("output_tokens", 0) + custom_usage.get("output_tokens", 0),
        )
        update_job(job.job_id, status="complete", cost_estimate=cost)

        yield {
            "event": "analysis_complete",
            "data": json.dumps({
                "flash": flash_dict,
                "deep": deep_results,
                "summary": summary_dict,
                "custom": custom_result_dict,
                "cost_estimate": cost,
            }),
        }

    except Exception as e:
        logger.error(f"Analysis pipeline failed: {e}")
        update_job(job.job_id, status="error", error=str(e))
        yield {
            "event": "error_event",
            "data": json.dumps({
                "message": f"Analysis failed: {str(e)}",
                "recoverable": False,
            }),
        }
