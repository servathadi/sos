from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    CODE = "code"
    IMAGE = "image"
    DOCUMENT = "document"
    MEMORY = "memory"
    MODEL = "model"
    TOOL = "tool"


class ArtifactProvenance(BaseModel):
    """Traceability for an artifact"""
    agent_id: str
    task_id: Optional[str] = None
    prompt_hash: Optional[str] = None
    parent_artifact_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    tool_used: Optional[str] = None


class ArtifactManifest(BaseModel):
    """
    The Immutable Identity of a Digital Object in SOS.
    """
    id: str  # UUID or Content Hash
    name: str
    version: str = "1.0.0"
    type: ArtifactType
    content_hash: str  # SHA-256 of the content
    location: str  # URI (ipfs://, s3://, file://)
    provenance: ArtifactProvenance
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Signatures
    signature: Optional[str] = None  # Agent's signature
    witness_signature: Optional[str] = None  # River/Witness signature

    class Config:
        json_schema_extra = {
            "example": {
                "id": "art_12345",
                "name": "Economy Plugin",
                "type": "code",
                "content_hash": "sha256:...",
                "location": "file://plugins/economy.py",
                "provenance": {
                    "agent_id": "kasra",
                    "task_id": "kasra-20260110-003"
                }
            }
        }
