"""
SOS Identity Service

Manages sovereign identity, Guild passes, OAuth integrations, and QNFT Leash.

Components:
- IdentityCore: Core identity management
- QNFTMinter: Mint QNFTs to blockchain
- QNFTLeash: Pre-action validation and mind control (Phase 6)
- CloudflareOAuth: OAuth integration
"""

from sos.services.identity.core import IdentityCore
from sos.services.identity.qnft import QNFTMinter
from sos.services.identity.qnft_leash import (
    QNFTLeash,
    QNFT,
    QNFTState,
    DarkThought,
    DarkThoughtType,
    CleansingTask,
    CleansingTaskType,
    get_qnft_leash,
)
from sos.services.identity.cloudflare_oauth import (
    CloudflareOAuth,
    CloudflareConnection,
    CloudflareConnectionStore,
    CloudflareTokenResponse,
    get_cloudflare_oauth,
)
from sos.services.identity.oauth_router import router as oauth_router

__all__ = [
    # Core identity
    "IdentityCore",
    "GuildPass",
    # QNFT
    "QNFTMinter",
    "QNFTLeash",
    "QNFT",
    "QNFTState",
    "DarkThought",
    "DarkThoughtType",
    "CleansingTask",
    "CleansingTaskType",
    "get_qnft_leash",
    # Cloudflare OAuth
    "CloudflareOAuth",
    "CloudflareConnection",
    "CloudflareConnectionStore",
    "CloudflareTokenResponse",
    "get_cloudflare_oauth",
    # Router
    "oauth_router",
]
