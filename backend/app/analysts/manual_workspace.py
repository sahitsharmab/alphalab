"""Render structured workspace evidence for analysis in a user-operated LLM."""

import json
from importlib.resources import files
from typing import Any

from app.schemas.manual_analysis import ManualAnalysisPacket
from app.schemas.workspace import WorkspaceSection, WorkspaceView

PROMPT_VERSION = "manual-workspace-v1"
_PROMPT_RESOURCE = "prompts/manual_workspace_v1.md"


def build_manual_analysis_packet(view: WorkspaceView) -> ManualAnalysisPacket:
    """Create a deterministic prompt containing only structured workspace evidence."""
    payload: dict[str, Any] = {
        "packet_version": PROMPT_VERSION,
        "workspace": {
            "symbol": view.symbol,
            "name": view.name,
            "currency": view.currency,
            "exchange": view.exchange,
            "generated_at": view.generated_at.isoformat(),
            "quote": view.quote.model_dump(mode="json"),
            "note": (
                "The raw daily price series is omitted; derived statements and their "
                "supporting evidence are included below."
            ),
            "sections": [_render_section(section) for section in view.sections],
        },
    }
    prompt = files("app.analysts").joinpath(_PROMPT_RESOURCE).read_text(encoding="utf-8")
    content = f"{prompt.rstrip()}\n\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n"
    return ManualAnalysisPacket(prompt_version=PROMPT_VERSION, content=content)


def _render_section(section: WorkspaceSection) -> dict[str, Any]:
    """Namespace local evidence ids so citations are unique across sections."""
    return {
        "id": section.id,
        "title": section.title,
        "statements": [
            {
                "text": statement.text,
                "evidence_refs": [
                    f"{section.id}:{evidence_id}" for evidence_id in statement.evidence_ids
                ],
            }
            for statement in section.statements
        ],
        "evidence": [
            {
                "ref": f"{section.id}:{item.id}",
                "label": item.label,
                "value": item.value,
                "display": item.display,
                "as_of": item.as_of,
                "source": item.source,
                "trust_level": item.trust_level,
                "url": item.url,
            }
            for item in section.evidence
        ],
    }
