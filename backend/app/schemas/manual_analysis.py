"""Contract for deterministic, copyable manual AI analysis packets."""

from pydantic import BaseModel, ConfigDict


class ManualAnalysisPacket(BaseModel):
    """A versioned prompt and evidence payload for a user-operated LLM."""

    model_config = ConfigDict(frozen=True)

    prompt_version: str
    content: str
