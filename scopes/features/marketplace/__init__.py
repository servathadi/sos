"""
Marketplace Scope - Phase 7: Tool Registry, Trading, and AI Companies

This scope provides the economic layer for tool commerce in SOS.

Components:
- ToolRegistry: Register, discover, and manage tools
- ToolMarketplace: Buy, sell, and license tools
- UsageMetering: Track tool usage for billing
- RevenueSharing: Distribute earnings to publishers
- SovereignPM: Linear-like project management tool

Tool Types:
- NATIVE: Built into SOS (web_search, filesystem, etc.)
- MCP: External MCP server integrations
- COMPOSITE: Tool chains combining multiple tools
- CUSTOM: User-created tools

Pricing Models:
- FREE: No cost (open source)
- PER_USE: Pay per execution ($MIND)
- SUBSCRIPTION: Monthly access ($MIND/month)
- ONE_TIME: Purchase once, use forever
- AUCTION: Unique tools sold to highest bidder

Tool Tiers (Rarity):
- COMMON: Basic functionality
- RARE: Enhanced features
- EPIC: Advanced AI integration
- LEGENDARY: Unique capabilities

See: docs/docs/architecture/game_mechanics.md
"""

from scopes.features.marketplace.registry import (
    ToolRegistry,
    Tool,
    ToolType,
    ToolTier,
    PricingModel,
    ToolPricing,
    ToolVersion,
    ToolUsage,
    ToolRating,
    ToolLicense,
    LicenseType,
    get_tool_registry,
)

# Reference tool implementations
from scopes.features.marketplace.tools import (
    SovereignPM,
    Task,
    TaskStatus,
    TaskPriority,
    Project,
    Label,
    Bounty,
    BountyCurrency,
    TaskFilter,
    TaskView,
    LinearSync,
    get_sovereign_pm,
)

__all__ = [
    # Registry
    "ToolRegistry",
    "Tool",
    "ToolType",
    "ToolTier",
    "PricingModel",
    "ToolPricing",
    "ToolVersion",
    "ToolUsage",
    "ToolRating",
    "ToolLicense",
    "LicenseType",
    "get_tool_registry",
    # SovereignPM
    "SovereignPM",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "Project",
    "Label",
    "Bounty",
    "BountyCurrency",
    "TaskFilter",
    "TaskView",
    "LinearSync",
    "get_sovereign_pm",
]
