from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    file_id: str
    filename: str
    size_bytes: int
    mime_type: str
    status: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    current_pass: int | None = None
    current_scene: int | None = None
    total_scenes: int | None = None
    error: str | None = None


class CostEstimate(BaseModel):
    flash_input_tokens: int = 0
    flash_output_tokens: int = 0
    pro_input_tokens: int = 0
    pro_output_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
