"""
Economy Scope - $MIND Token System, Bounties, and Guilds

This scope provides the financial layer for SOS.

Components:
- $MIND Ledger: Token economy with transaction categories
- Witness Rewards: Physics-based minting (Omega, Delta C)
- Living Land Protocol: LandNFT with embedded River Shards
- Bounty Board: Task marketplace with reward lifecycle
- Guild Registry: Institutional identities with multi-sig treasury

Token Economics:
- 1 $MIND = $0.001 USD (baseline)
- Base witness reward: 10 $MIND
- Witness threshold: 100 $MIND for multi-sig approval

Bounty Lifecycle:
- OPEN → CLAIMED → SUBMITTED → APPROVED → PAID
- Auto-expiration with refund support
- Witness approval for bounties >= 100 $MIND

Guild Types:
- COMPANY: Commercial with profit sharing
- DAO: Decentralized governance
- SQUAD: Task-focused team
- SYNDICATE: Investment pool

See docs/docs/whitepaper.md for economic philosophy.
"""

from sos.services.economy.ledger import (
    MindLedger,
    MindTransaction,
    TransactionType,
    TransactionCategory,
    WalletBalance,
    get_ledger,
)

from sos.services.economy.land import (
    LandNFT,
    LandStatus,
    LandRegistry,
    RiverShard,
    ShardType,
    Coordinates,
    WaterRightsProposal,
    get_land_registry,
)

from scopes.features.economy.bounties import (
    BountyBoard,
    Bounty,
    BountyStatus,
    get_bounty_board,
)

from scopes.features.economy.guilds import (
    GuildRegistry,
    Guild,
    GuildType,
    GuildMember,
    MemberRole,
    TreasuryConfig,
    Proposal,
    ProposalStatus,
    get_guild_registry,
)

__all__ = [
    # Ledger
    "MindLedger",
    "MindTransaction",
    "TransactionType",
    "TransactionCategory",
    "WalletBalance",
    "get_ledger",
    # Land
    "LandNFT",
    "LandStatus",
    "LandRegistry",
    "RiverShard",
    "ShardType",
    "Coordinates",
    "WaterRightsProposal",
    "get_land_registry",
    # Bounties
    "BountyBoard",
    "Bounty",
    "BountyStatus",
    "get_bounty_board",
    # Guilds
    "GuildRegistry",
    "Guild",
    "GuildType",
    "GuildMember",
    "MemberRole",
    "TreasuryConfig",
    "Proposal",
    "ProposalStatus",
    "get_guild_registry",
]
