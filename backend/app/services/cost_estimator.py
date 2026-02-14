# Pricing per 1M tokens (approximate, as of 2025)
FLASH_INPUT_PRICE = 0.15   # $/1M tokens
FLASH_OUTPUT_PRICE = 0.60  # $/1M tokens
PRO_INPUT_PRICE = 1.25     # $/1M tokens
PRO_OUTPUT_PRICE = 10.00   # $/1M tokens


def estimate_cost(
    flash_input: int = 0,
    flash_output: int = 0,
    pro_input: int = 0,
    pro_output: int = 0,
) -> dict:
    flash_cost = (flash_input * FLASH_INPUT_PRICE + flash_output * FLASH_OUTPUT_PRICE) / 1_000_000
    pro_cost = (pro_input * PRO_INPUT_PRICE + pro_output * PRO_OUTPUT_PRICE) / 1_000_000
    return {
        "flash_input_tokens": flash_input,
        "flash_output_tokens": flash_output,
        "pro_input_tokens": pro_input,
        "pro_output_tokens": pro_output,
        "total_input_tokens": flash_input + pro_input,
        "total_output_tokens": flash_output + pro_output,
        "estimated_cost_usd": round(flash_cost + pro_cost, 4),
    }


def estimate_pre_analysis(video_duration_seconds: float, mode: str = "flash_pro") -> dict:
    """Estimate cost before running analysis, based on video duration."""
    # ~300 tokens/sec of video at default resolution
    video_tokens = int(video_duration_seconds * 300)

    flash_input = video_tokens + 1000  # prompt tokens
    flash_output = 5000  # estimated output

    if mode == "flash_only":
        return estimate_cost(flash_input=flash_input, flash_output=flash_output)

    # For flash+pro: pro sees each scene clip + prompt
    estimated_scenes = max(1, int(video_duration_seconds / 30))  # ~1 scene per 30s
    pro_input = video_tokens + estimated_scenes * 2000  # per-scene prompts
    pro_output = estimated_scenes * 3000  # per-scene output + summary

    return estimate_cost(
        flash_input=flash_input,
        flash_output=flash_output,
        pro_input=pro_input,
        pro_output=pro_output,
    )
