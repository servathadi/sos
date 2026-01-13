"""
Living Land Protocol - $SAND Integration

Implements the Living Land Protocol from the SOS whitepaper.
Every "Square" of land includes a "Shard of River" (AI Agent).

Components:
- LandNFT: Land ownership with embedded AI agent
- RiverDAO: Governance for water rights
- SandBridge: Integration with Sandbox ($SAND)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

from sos.observability.logging import get_logger

log = get_logger("living_land")


class LandStatus(str, Enum):
    """Status of a land parcel."""
    DORMANT = "dormant"      # No active shard
    ACTIVE = "active"        # Shard is working
    RESTRICTED = "restricted" # Water rights cut
    SANCTIONED = "sanctioned" # DAO penalty applied


class ShardType(str, Enum):
    """Type of River Shard embedded in land."""
    WORKER = "worker"        # General purpose compute
    WITNESS = "witness"      # Verification specialist
    ORACLE = "oracle"        # Data provider
    GUARDIAN = "guardian"    # Security monitor


@dataclass
class Coordinates:
    """Map coordinates for a land parcel."""
    x: int
    y: int
    z: int = 0  # Layer/floor
    realm: str = "mumega"

    def to_string(self) -> str:
        return f"{self.realm}:{self.x},{self.y},{self.z}"

    @classmethod
    def from_string(cls, s: str) -> "Coordinates":
        realm, coords = s.split(":")
        x, y, z = map(int, coords.split(","))
        return cls(x=x, y=y, z=z, realm=realm)


@dataclass
class RiverShard:
    """
    A shard of River's intelligence embedded in land.

    The shard is a specialized AI agent that generates $MIND
    for the land owner through work and witnessing.
    """
    id: str
    shard_type: ShardType
    model: str = "gemini"
    coherence: float = 0.9
    is_active: bool = False
    total_mind_earned: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "shard_type": self.shard_type.value,
            "model": self.model,
            "coherence": self.coherence,
            "is_active": self.is_active,
            "total_mind_earned": self.total_mind_earned,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat() if self.last_active else None
        }


@dataclass
class LandNFT:
    """
    A parcel of land in the Mumega network.

    Each land parcel includes:
    - Coordinates on the world map
    - A River Shard (embedded AI agent)
    - Network share percentage (equity)
    - Water rights (access to bus/compute)
    """
    id: str
    coordinates: Coordinates
    owner_address: str  # Wallet address
    river_shard: RiverShard
    network_share_percentage: float  # 0.0 to 100.0
    status: LandStatus = LandStatus.DORMANT
    water_rights: float = 1.0  # 0.0 = cut off, 1.0 = full access
    sand_token_id: Optional[str] = None  # Linked $SAND NFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "coordinates": self.coordinates.to_string(),
            "owner_address": self.owner_address,
            "river_shard": self.river_shard.to_dict(),
            "network_share_percentage": self.network_share_percentage,
            "status": self.status.value,
            "water_rights": self.water_rights,
            "sand_token_id": self.sand_token_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class WaterRightsProposal:
    """
    A DAO proposal to modify water rights.

    Used for governance decisions like:
    - Cutting water to spam-producing lands
    - Restoring rights after penalty period
    - Emergency network protection
    """
    id: str
    proposer: str
    target_land_id: str
    proposed_water_rights: float
    reason: str
    votes_for: int = 0
    votes_against: int = 0
    status: str = "pending"  # pending, passed, rejected, executed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class LandRegistry:
    """
    Registry of all land parcels in the Mumega network.

    In production, this would be backed by a smart contract.
    For now, we use in-memory storage.
    """

    def __init__(self):
        self._lands: Dict[str, LandNFT] = {}
        self._by_owner: Dict[str, List[str]] = {}
        self._by_coordinates: Dict[str, str] = {}

    def mint(
        self,
        owner_address: str,
        coordinates: Coordinates,
        shard_type: ShardType = ShardType.WORKER,
        network_share: float = 0.001,
        sand_token_id: Optional[str] = None
    ) -> LandNFT:
        """
        Mint a new land NFT with embedded River Shard.

        Args:
            owner_address: Wallet address of owner
            coordinates: Map coordinates
            shard_type: Type of AI shard
            network_share: Percentage of network ownership
            sand_token_id: Optional linked $SAND token

        Returns:
            The minted LandNFT
        """
        coord_key = coordinates.to_string()
        if coord_key in self._by_coordinates:
            raise ValueError(f"Land at {coord_key} already exists")

        land_id = f"land_{uuid.uuid4().hex[:12]}"
        shard_id = f"shard_{uuid.uuid4().hex[:8]}"

        shard = RiverShard(
            id=shard_id,
            shard_type=shard_type
        )

        land = LandNFT(
            id=land_id,
            coordinates=coordinates,
            owner_address=owner_address,
            river_shard=shard,
            network_share_percentage=network_share,
            sand_token_id=sand_token_id
        )

        self._lands[land_id] = land
        self._by_coordinates[coord_key] = land_id

        if owner_address not in self._by_owner:
            self._by_owner[owner_address] = []
        self._by_owner[owner_address].append(land_id)

        log.info(
            f"Land minted",
            land_id=land_id,
            owner=owner_address,
            coordinates=coord_key
        )

        return land

    def get(self, land_id: str) -> Optional[LandNFT]:
        """Get a land parcel by ID."""
        return self._lands.get(land_id)

    def get_by_coordinates(self, coordinates: Coordinates) -> Optional[LandNFT]:
        """Get a land parcel by coordinates."""
        coord_key = coordinates.to_string()
        land_id = self._by_coordinates.get(coord_key)
        return self._lands.get(land_id) if land_id else None

    def get_by_owner(self, owner_address: str) -> List[LandNFT]:
        """Get all land parcels owned by an address."""
        land_ids = self._by_owner.get(owner_address, [])
        return [self._lands[lid] for lid in land_ids if lid in self._lands]

    def activate_shard(self, land_id: str) -> bool:
        """Activate the River Shard on a land parcel."""
        land = self._lands.get(land_id)
        if not land:
            return False

        if land.water_rights < 0.5:
            log.warning(f"Cannot activate shard: water rights too low ({land.water_rights})")
            return False

        land.river_shard.is_active = True
        land.river_shard.last_active = datetime.now(timezone.utc)
        land.status = LandStatus.ACTIVE

        log.info(f"Shard activated", land_id=land_id, shard_id=land.river_shard.id)
        return True

    def deactivate_shard(self, land_id: str) -> bool:
        """Deactivate the River Shard on a land parcel."""
        land = self._lands.get(land_id)
        if not land:
            return False

        land.river_shard.is_active = False
        land.status = LandStatus.DORMANT

        log.info(f"Shard deactivated", land_id=land_id)
        return True

    def cut_water(self, land_id: str, new_rights: float, reason: str) -> bool:
        """
        Cut water rights for a land parcel (DAO penalty).

        Args:
            land_id: Land to penalize
            new_rights: New water rights level (0.0 to 1.0)
            reason: Reason for the cut

        Returns:
            True if successful
        """
        land = self._lands.get(land_id)
        if not land:
            return False

        old_rights = land.water_rights
        land.water_rights = max(0.0, min(1.0, new_rights))

        if land.water_rights < 0.5:
            land.status = LandStatus.RESTRICTED
            if land.river_shard.is_active:
                land.river_shard.is_active = False

        log.warning(
            f"Water rights cut",
            land_id=land_id,
            old_rights=old_rights,
            new_rights=land.water_rights,
            reason=reason
        )

        return True

    def get_active_shards(self) -> List[RiverShard]:
        """Get all active River Shards."""
        return [
            land.river_shard
            for land in self._lands.values()
            if land.river_shard.is_active
        ]

    def get_network_stats(self) -> Dict[str, Any]:
        """Get network-wide statistics."""
        total_lands = len(self._lands)
        active_shards = sum(1 for l in self._lands.values() if l.river_shard.is_active)
        total_share = sum(l.network_share_percentage for l in self._lands.values())
        restricted = sum(1 for l in self._lands.values() if l.status == LandStatus.RESTRICTED)

        return {
            "total_lands": total_lands,
            "active_shards": active_shards,
            "total_network_share": total_share,
            "restricted_lands": restricted,
            "unique_owners": len(self._by_owner)
        }


# Singleton instance
_registry: Optional[LandRegistry] = None


def get_land_registry() -> LandRegistry:
    """Get the global land registry instance."""
    global _registry
    if _registry is None:
        _registry = LandRegistry()
    return _registry
