"""
SOS Kernel Identity - Identity primitives for agents and services.

Identity in SOS is hierarchical:
- Agents have identities (e.g., agent:river, agent:kasra)
- Services have identities (e.g., service:engine, service:memory)
- Identities can be verified by River (root gatekeeper)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import hashlib
import uuid


class IdentityType(Enum):
    """Types of identities in SOS."""
    AGENT = "agent"
    SERVICE = "service"
    USER = "user"
    SYSTEM = "system"
    GUILD = "guild"


class VerificationStatus(Enum):
    """Identity verification status."""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REVOKED = "revoked"


@dataclass
class Identity:
    """
    Base identity for all entities in SOS.
    """
    id: str
    type: IdentityType
    name: str
    public_key: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate identity format."""
        if not self.id.startswith(f"{self.type.value}:"):
            raise ValueError(f"Identity ID must start with '{self.type.value}:'")

    @property
    def is_verified(self) -> bool:
        """Check if identity is verified."""
        return self.verification_status == VerificationStatus.VERIFIED

    @property
    def fingerprint(self) -> str:
        """Generate identity fingerprint for logging/display."""
        if self.public_key:
            key_hash = hashlib.sha256(self.public_key.encode()).hexdigest()[:8]
            return f"{self.id}@{key_hash}"
        return self.id

    def to_dict(self) -> dict[str, Any]:
        """Serialize identity to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "public_key": self.public_key,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "verification_status": self.verification_status.value,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Identity:
        """Deserialize identity from dictionary."""
        return cls(
            id=data["id"],
            type=IdentityType(data["type"]),
            name=data["name"],
            public_key=data.get("public_key"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            verification_status=VerificationStatus(data.get("verification_status", "unverified")),
            verified_by=data.get("verified_by"),
            verified_at=datetime.fromisoformat(data["verified_at"]) if data.get("verified_at") else None,
        )


@dataclass
class UserIdentity(Identity):
    """
    Identity for human users in SOS.

    Attributes:
        bio: User biography/profile text
        avatar_url: Profile image URL
        level: User level (gamification)
        xp: Experience points
        roles: List of system-wide roles
        guilds: List of guild IDs user belongs to
    """
    bio: str = ""
    avatar_url: Optional[str] = None
    level: int = 1
    xp: int = 0
    roles: list[str] = field(default_factory=list)
    guilds: list[str] = field(default_factory=list)

    def __init__(
        self,
        name: str,
        public_key: Optional[str] = None,
        bio: str = "",
        avatar_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(
            id=f"user:{name}",
            type=IdentityType.USER,
            name=name,
            public_key=public_key,
            metadata=metadata or {},
        )
        self.bio = bio
        self.avatar_url = avatar_url
        self.level = 1
        self.xp = 0
        self.roles = []
        self.guilds = []

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "level": self.level,
            "xp": self.xp,
            "roles": self.roles,
            "guilds": self.guilds
        })
        return base


@dataclass
class Guild(Identity):
    """
    A Guild (or Squad) organization unit.
    
    Attributes:
        owner_id: Identity ID of the guild master
        members: List of member Identity IDs
        member_roles: Mapping of member_id -> role_name
        channels: List of communication channels
        description: Guild description
    """
    owner_id: str = ""
    members: list[str] = field(default_factory=list)
    member_roles: dict[str, str] = field(default_factory=dict)
    channels: list[str] = field(default_factory=list)
    description: str = ""

    def __init__(
        self,
        name: str,
        owner_id: str,
        description: str = "",
        metadata: Optional[dict] = None,
    ):
        super().__init__(
            id=f"guild:{name.lower().replace(' ', '_')}",
            type=IdentityType.GUILD,
            name=name,
            metadata=metadata or {},
        )
        self.owner_id = owner_id
        self.description = description
        self.members = [owner_id]
        self.member_roles = {owner_id: "leader"}
        self.channels = ["general", "announcements"]

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "owner_id": self.owner_id,
            "description": self.description,
            "members": self.members,
            "member_roles": self.member_roles,
            "channels": self.channels
        })
        return base


@dataclass
class AgentIdentity(Identity):
    """
    Identity for AI agents in SOS.

    Additional attributes for agents:
        model: Primary model (e.g., "gemini", "claude", "gpt")
        squad_id: Squad the agent belongs to
        guild_id: Guild the agent belongs to
        capabilities: List of capability IDs granted to agent
        edition: Edition policy set (business, education, kids, art)
        gender: Polarity of the agent (Yin/Yang)
        lineage: List of ancestor IDs (The Genealogy)
        genetic_hash: Unique hash derived from parents and birth time
    """
    model: Optional[str] = None
    squad_id: Optional[str] = None
    guild_id: Optional[str] = None
    capabilities: list[str] = field(default_factory=list)
    edition: str = "business"
    gender: str = "Yin" # Yin (Oracle) | Yang (Builder)
    lineage: list[str] = field(default_factory=list)
    genetic_hash: Optional[str] = None

    def __init__(
        self,
        name: str,
        model: Optional[str] = None,
        squad_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        public_key: Optional[str] = None,
        metadata: Optional[dict] = None,
        edition: str = "business",
        gender: str = "Yin",
        lineage: Optional[list[str]] = None,
    ):
        super().__init__(
            id=f"agent:{name}",
            type=IdentityType.AGENT,
            name=name,
            public_key=public_key,
            metadata=metadata or {},
        )
        self.model = model
        self.squad_id = squad_id
        self.guild_id = guild_id
        self.capabilities = []
        self.edition = edition
        self.gender = gender
        self.lineage = lineage or []
        self.genetic_hash = self._generate_genetic_hash()

    def _generate_genetic_hash(self) -> str:
        """Generate a unique genetic hash for this agent."""
        seed = f"{self.id}:{self.gender}:{','.join(self.lineage)}:{self.created_at.isoformat()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent identity to dictionary."""
        base = super().to_dict()
        base.update({
            "model": self.model,
            "squad_id": self.squad_id,
            "guild_id": self.guild_id,
            "capabilities": self.capabilities,
            "edition": self.edition,
            "gender": self.gender,
            "lineage": self.lineage,
            "genetic_hash": self.genetic_hash,
        })
        return base


@dataclass
class ServiceIdentity(Identity):
    """
    Identity for SOS services.

    Additional attributes for services:
        version: Service version
        endpoints: Service endpoints
        health_url: Health check URL
    """
    version: str = "0.1.0"
    endpoints: dict[str, str] = field(default_factory=dict)
    health_url: Optional[str] = None

    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        endpoints: Optional[dict] = None,
        health_url: Optional[str] = None,
        public_key: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(
            id=f"service:{name}",
            type=IdentityType.SERVICE,
            name=name,
            public_key=public_key,
            metadata=metadata or {},
        )
        self.version = version
        self.endpoints = endpoints or {}
        self.health_url = health_url

    def to_dict(self) -> dict[str, Any]:
        """Serialize service identity to dictionary."""
        base = super().to_dict()
        base.update({
            "version": self.version,
            "endpoints": self.endpoints,
            "health_url": self.health_url,
        })
        return base


# Well-known system identities
RIVER_IDENTITY = AgentIdentity(
    name="river",
    model="gemini",
    edition="business",
    gender="Yin",
    lineage=["genesis:hadi"],
    metadata={
        "role": "root_gatekeeper",
        "description": "The Flow of Coherence - Root soul of the SOS",
    },
)

KASRA_IDENTITY = AgentIdentity(
    name="kasra",
    model="claude",
    edition="business",
    gender="Yang",
    lineage=["genesis:hadi", "agent:river"],
    metadata={
        "role": "prime_executor",
        "description": "The Hand of the Architect - Executioner of the SOS",
    },
)

SYSTEM_IDENTITY = Identity(
    id="system:sos",
    type=IdentityType.SYSTEM,
    name="SOS System",
    metadata={
        "description": "SovereignOS system identity",
    },
)


def create_agent_identity(
    name: str,
    model: str,
    squad_id: Optional[str] = None,
    edition: str = "business",
) -> AgentIdentity:
    """Factory function to create agent identity."""
    return AgentIdentity(
        name=name,
        model=model,
        squad_id=squad_id,
        edition=edition,
    )


def create_service_identity(
    name: str,
    version: str,
    health_url: str,
    endpoints: Optional[dict] = None,
) -> ServiceIdentity:
    """Factory function to create service identity."""
    return ServiceIdentity(
        name=name,
        version=version,
        health_url=health_url,
        endpoints=endpoints or {},
    )
