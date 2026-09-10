"""Dated, approximate Gemini estimates based on reported usage.

Source: https://ai.google.dev/gemini-api/docs/pricing (verified 2026-09-09).
Unknown models are deliberately not assigned invented prices.
"""
from datetime import date

from app.config import settings


def model_rates(model: str, as_of: date | None = None) -> tuple[float, float] | None:
    as_of = as_of or date.today()
    if model in {"gemini-3.8-flash", "gemini-3.7-flash"}:
        return (0.75, 3.75) if as_of < date(2027, 1, 1) else (1.50, 7.50)
    if model == "gemini-3.5-flash-lite":
        return 0.30, 2.50
    return None


def estimate_cost(
    flash_input: int = 0, flash_output: int = 0,
    pro_input: int = 0, pro_output: int = 0,
    usage_records: list[dict] | None = None, as_of: date | None = None,
) -> dict:
    as_of = as_of or date.today()
    records = usage_records if usage_records is not None else [
        {"model": settings.gemini_analysis_model, "stage": "analysis", "input_tokens": flash_input,
         "output_tokens": flash_output, "usage_available": True},
        {"model": settings.gemini_deep_model, "stage": "deep_analysis", "input_tokens": pro_input,
         "output_tokens": pro_output, "usage_available": True},
    ]
    known_cost = 0.0
    unpriced = set()
    input_tokens = output_tokens = thinking_tokens = 0
    analysis_input = analysis_output = deep_input = deep_output = 0
    unknown_usage = False
    cache_warning = False
    for record in records:
        model = record.get("model", "unknown")
        inp, out = record.get("input_tokens", 0), record.get("output_tokens", 0)
        input_tokens += inp
        output_tokens += out  # candidate + thinking, from extract_usage
        thinking_tokens += record.get("thinking_tokens", 0)
        if record.get("stage") in {"deep_analysis", "summary", "custom"}:
            deep_input += inp
            deep_output += out
        else:
            analysis_input += inp
            analysis_output += out
        rates = model_rates(model, as_of)
        if rates is None:
            unpriced.add(model)
        elif not record.get("usage_available", True):
            unknown_usage = True
        else:
            known_cost += (inp * rates[0] + out * rates[1]) / 1_000_000
        cache_warning |= bool(record.get("cached_input_tokens", 0))
    warnings = ["Estimate uses standard list prices; excludes media storage, transfer, compute, and unreported failed requests."]
    if unpriced:
        warnings.append("No verified price schedule for: " + ", ".join(sorted(unpriced)))
    if unknown_usage:
        warnings.append("Provider token usage was unavailable for one or more requests.")
    if cache_warning:
        warnings.append("Cached tokens are estimated at uncached rates; cache storage and discounts are not reconciled.")
    return {
        "flash_input_tokens": analysis_input, "flash_output_tokens": analysis_output,
        "pro_input_tokens": deep_input, "pro_output_tokens": deep_output,
        "total_input_tokens": input_tokens, "total_output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "estimated_cost_usd": None if unpriced or unknown_usage else round(known_cost, 6),
        "priced_subtotal_usd": round(known_cost, 6),
        "pricing_status": "unpriced" if unpriced or unknown_usage else "estimated",
        "pricing_as_of": as_of.isoformat(), "pricing_verified_on": "2026-09-09",
        "pricing_source": "https://ai.google.dev/gemini-api/docs/pricing",
        "unpriced_models": sorted(unpriced), "warnings": warnings, "usage_records": records,
    }


def estimate_pre_analysis(video_duration_seconds: float, mode: str = "flash_pro") -> dict:
    """Planning scenario: two low-resolution analysis passes, plus deep work."""
    seconds = max(0.0, video_duration_seconds)
    video_tokens = int(seconds * 100)
    scenes = max(1, int(seconds / 60))
    cost = estimate_cost(
        flash_input=video_tokens * 2 + scenes * 1200,
        flash_output=max(2000, scenes * 1500),
        pro_input=0 if mode == "flash_only" else video_tokens * 2 + scenes * 1800,
        pro_output=0 if mode == "flash_only" else scenes * 2500 + 2000,
    )
    cost["basis"] = "planning_scenario_not_quote"
    cost["warnings"].append("Sampling rate, high-resolution frames, thinking, scene count, optional passes and retries can substantially change cost.")
    return cost
