"""
Tool Registry - Central Registry for SOS Marketplace Tools

Implements Phase 7 tool commerce:
- Tool registration with metadata and versioning
- Pricing models (free, per-use, subscription, one-time)
- Usage metering and billing
- Revenue sharing with publishers (Guilds/Agents)
- Discovery and search
- Ratings and reviews

Tools are like equipment in a game:
- They have tiers (Common → Legendary)
- They cost $MIND to use or purchase
- They can be crafted by AI Companies
- They earn revenue for their creators
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable, Awaitable
from enum import Enum
from collections import defaultdict
import uuid
import json
import hashlib
from pathlib import Path

from sos.observability.logging import get_logger

log = get_logger("tool_registry")


# ============================================================================
# ENUMERATIONS
# ============================================================================

class ToolType(str, Enum):
    """Type of tool implementation."""
    NATIVE = "native"        # Built into SOS
    MCP = "mcp"              # External MCP server
    COMPOSITE = "composite"  # Chain of tools
    CUSTOM = "custom"        # User-created


class ToolTier(str, Enum):
    """Tool rarity/quality tier (like game equipment)."""
    COMMON = "common"        # Basic, free or cheap
    RARE = "rare"            # Enhanced features
    EPIC = "epic"            # Advanced AI integration
    LEGENDARY = "legendary"  # Unique, auction-only


class PricingModel(str, Enum):
    """How the tool is priced."""
    FREE = "free"            # No cost
    PER_USE = "per_use"      # Pay per execution
    SUBSCRIPTION = "subscription"  # Monthly fee
    ONE_TIME = "one_time"    # Buy once
    AUCTION = "auction"      # Bid-based


class LicenseType(str, Enum):
    """Type of tool license."""
    OPEN = "open"            # Anyone can use
    LICENSED = "licensed"    # Requires purchase/subscription
    EXCLUSIVE = "exclusive"  # Single owner
    GUILD = "guild"          # Guild members only


class ToolCategory(str, Enum):
    """Tool categories for discovery."""
    PRODUCTIVITY = "productivity"  # Task management, docs
    DEVELOPMENT = "development"    # Code, git, CI/CD
    RESEARCH = "research"          # Web search, data
    COMMUNICATION = "communication"  # Chat, email
    FINANCE = "finance"            # Payments, accounting
    CREATIVE = "creative"          # Image, audio, video
    ANALYTICS = "analytics"        # Data analysis
    SECURITY = "security"          # Auth, encryption
    INTEGRATION = "integration"    # API connectors
    AI = "ai"                      # AI/ML tools


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ToolPricing:
    """Pricing configuration for a tool."""
    model: PricingModel
    price_mind: float = 0.0           # Price in $MIND
    subscription_days: int = 30       # For subscription model
    usage_limit: Optional[int] = None  # Max uses per period
    revenue_share: float = 0.7        # Publisher gets 70%, platform 30%

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model.value,
            "price_mind": self.price_mind,
            "subscription_days": self.subscription_days,
            "usage_limit": self.usage_limit,
            "revenue_share": self.revenue_share,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolPricing":
        return cls(
            model=PricingModel(data["model"]),
            price_mind=data.get("price_mind", 0.0),
            subscription_days=data.get("subscription_days", 30),
            usage_limit=data.get("usage_limit"),
            revenue_share=data.get("revenue_share", 0.7),
        )


@dataclass
class ToolVersion:
    """A version of a tool."""
    version: str              # Semantic version (1.0.0)
    changelog: str = ""
    released_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deprecated: bool = False
    min_sos_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "changelog": self.changelog,
            "released_at": self.released_at.isoformat(),
            "deprecated": self.deprecated,
            "min_sos_version": self.min_sos_version,
        }


@dataclass
class ToolUsage:
    """Usage record for metering."""
    tool_id: str
    user_id: str
    used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0
    cost_mind: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "user_id": self.user_id,
            "used_at": self.used_at.isoformat(),
            "duration_ms": self.duration_ms,
            "cost_mind": self.cost_mind,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class ToolRating:
    """User rating for a tool."""
    user_id: str
    rating: int  # 1-5 stars
    review: str = ""
    rated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "rating": self.rating,
            "review": self.review,
            "rated_at": self.rated_at.isoformat(),
        }


@dataclass
class ToolLicense:
    """License granting access to a tool."""
    id: str
    tool_id: str
    user_id: str
    license_type: LicenseType
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    usage_remaining: Optional[int] = None  # For per-use
    active: bool = True

    @property
    def is_valid(self) -> bool:
        if not self.active:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        if self.usage_remaining is not None and self.usage_remaining <= 0:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "user_id": self.user_id,
            "license_type": self.license_type.value,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "usage_remaining": self.usage_remaining,
            "active": self.active,
            "is_valid": self.is_valid,
        }


@dataclass
class Tool:
    """A registered tool in the marketplace."""
    id: str
    name: str
    description: str
    tool_type: ToolType
    tier: ToolTier = ToolTier.COMMON
    category: ToolCategory = ToolCategory.PRODUCTIVITY

    # Publisher
    publisher_id: str = ""        # Guild or Agent ID
    publisher_name: str = ""

    # Pricing
    pricing: ToolPricing = field(default_factory=lambda: ToolPricing(model=PricingModel.FREE))

    # Versioning
    current_version: str = "1.0.0"
    versions: List[ToolVersion] = field(default_factory=list)

    # Technical
    mcp_server: Optional[str] = None  # MCP server name for MCP tools
    endpoint: Optional[str] = None     # API endpoint for native tools
    schema: Dict[str, Any] = field(default_factory=dict)  # Input/output schema

    # For composite tools
    tool_chain: List[str] = field(default_factory=list)  # List of tool IDs

    # Stats
    total_uses: int = 0
    total_revenue: float = 0.0
    avg_rating: float = 0.0
    rating_count: int = 0

    # Metadata
    tags: List[str] = field(default_factory=list)
    icon: Optional[str] = None
    documentation_url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published: bool = True
    verified: bool = False  # Platform-verified

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type.value,
            "tier": self.tier.value,
            "category": self.category.value,
            "publisher_id": self.publisher_id,
            "publisher_name": self.publisher_name,
            "pricing": self.pricing.to_dict(),
            "current_version": self.current_version,
            "versions": [v.to_dict() for v in self.versions],
            "mcp_server": self.mcp_server,
            "endpoint": self.endpoint,
            "schema": self.schema,
            "tool_chain": self.tool_chain,
            "total_uses": self.total_uses,
            "total_revenue": self.total_revenue,
            "avg_rating": self.avg_rating,
            "rating_count": self.rating_count,
            "tags": self.tags,
            "icon": self.icon,
            "documentation_url": self.documentation_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published": self.published,
            "verified": self.verified,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tool":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            tool_type=ToolType(data["tool_type"]),
            tier=ToolTier(data.get("tier", "common")),
            category=ToolCategory(data.get("category", "productivity")),
            publisher_id=data.get("publisher_id", ""),
            publisher_name=data.get("publisher_name", ""),
            pricing=ToolPricing.from_dict(data.get("pricing", {"model": "free"})),
            current_version=data.get("current_version", "1.0.0"),
            versions=[
                ToolVersion(
                    version=v["version"],
                    changelog=v.get("changelog", ""),
                    released_at=datetime.fromisoformat(v["released_at"]) if v.get("released_at") else datetime.now(timezone.utc),
                    deprecated=v.get("deprecated", False),
                )
                for v in data.get("versions", [])
            ],
            mcp_server=data.get("mcp_server"),
            endpoint=data.get("endpoint"),
            schema=data.get("schema", {}),
            tool_chain=data.get("tool_chain", []),
            total_uses=data.get("total_uses", 0),
            total_revenue=data.get("total_revenue", 0.0),
            avg_rating=data.get("avg_rating", 0.0),
            rating_count=data.get("rating_count", 0),
            tags=data.get("tags", []),
            icon=data.get("icon"),
            documentation_url=data.get("documentation_url"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc),
            published=data.get("published", True),
            verified=data.get("verified", False),
        )


# ============================================================================
# TOOL REGISTRY
# ============================================================================

class ToolRegistry:
    """
    Central registry for SOS marketplace tools.

    Handles:
    - Tool registration and versioning
    - License management
    - Usage metering and billing
    - Discovery and search
    - Revenue tracking
    """

    # Platform fee percentage
    PLATFORM_FEE = 0.30  # 30% to platform, 70% to publisher

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "marketplace"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._tools: Dict[str, Tool] = {}
        self._licenses: Dict[str, ToolLicense] = {}
        self._usage: List[ToolUsage] = []
        self._ratings: Dict[str, List[ToolRating]] = defaultdict(list)

        # Index for fast lookup
        self._by_category: Dict[ToolCategory, Set[str]] = defaultdict(set)
        self._by_publisher: Dict[str, Set[str]] = defaultdict(set)
        self._by_tag: Dict[str, Set[str]] = defaultdict(set)

        self._load_registry()
        self._register_native_tools()

    def _load_registry(self):
        """Load registry from storage."""
        registry_file = self.storage_path / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file) as f:
                    data = json.load(f)
                    for tool_data in data.get("tools", []):
                        tool = Tool.from_dict(tool_data)
                        self._tools[tool.id] = tool
                        self._index_tool(tool)

                    for lic_data in data.get("licenses", []):
                        lic = ToolLicense(
                            id=lic_data["id"],
                            tool_id=lic_data["tool_id"],
                            user_id=lic_data["user_id"],
                            license_type=LicenseType(lic_data["license_type"]),
                            granted_at=datetime.fromisoformat(lic_data["granted_at"]),
                            expires_at=datetime.fromisoformat(lic_data["expires_at"]) if lic_data.get("expires_at") else None,
                            usage_remaining=lic_data.get("usage_remaining"),
                            active=lic_data.get("active", True),
                        )
                        self._licenses[lic.id] = lic

                log.info(f"Loaded {len(self._tools)} tools, {len(self._licenses)} licenses")
            except Exception as e:
                log.error(f"Failed to load registry: {e}")

    def _save_registry(self):
        """Save registry to storage."""
        registry_file = self.storage_path / "registry.json"
        try:
            with open(registry_file, "w") as f:
                data = {
                    "tools": [t.to_dict() for t in self._tools.values()],
                    "licenses": [l.to_dict() for l in self._licenses.values()],
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save registry: {e}")

    def _index_tool(self, tool: Tool):
        """Add tool to search indices."""
        self._by_category[tool.category].add(tool.id)
        self._by_publisher[tool.publisher_id].add(tool.id)
        for tag in tool.tags:
            self._by_tag[tag.lower()].add(tool.id)

    def _register_native_tools(self):
        """Register built-in SOS tools."""
        native_tools = [
            Tool(
                id="native_web_search",
                name="Web Search",
                description="Search the web using DuckDuckGo",
                tool_type=ToolType.NATIVE,
                tier=ToolTier.COMMON,
                category=ToolCategory.RESEARCH,
                publisher_id="sos_platform",
                publisher_name="SOS Platform",
                pricing=ToolPricing(model=PricingModel.PER_USE, price_mind=1.0),
                endpoint="web_search",
                tags=["search", "web", "research"],
                verified=True,
            ),
            Tool(
                id="native_filesystem",
                name="Filesystem Access",
                description="Read files from the filesystem (sandboxed)",
                tool_type=ToolType.NATIVE,
                tier=ToolTier.COMMON,
                category=ToolCategory.DEVELOPMENT,
                publisher_id="sos_platform",
                publisher_name="SOS Platform",
                pricing=ToolPricing(model=PricingModel.FREE),
                endpoint="filesystem_read",
                tags=["file", "read", "filesystem"],
                verified=True,
            ),
            Tool(
                id="native_spore",
                name="Spore Generator",
                description="Generate context-injection spores for agent state transfer",
                tool_type=ToolType.NATIVE,
                tier=ToolTier.RARE,
                category=ToolCategory.AI,
                publisher_id="sos_platform",
                publisher_name="SOS Platform",
                pricing=ToolPricing(model=PricingModel.PER_USE, price_mind=5.0),
                endpoint="generate_spore",
                tags=["spore", "context", "agent", "ai"],
                verified=True,
            ),
            Tool(
                id="native_wallet",
                name="Wallet Operations",
                description="Check balance, credit, and debit $MIND",
                tool_type=ToolType.NATIVE,
                tier=ToolTier.COMMON,
                category=ToolCategory.FINANCE,
                publisher_id="sos_platform",
                publisher_name="SOS Platform",
                pricing=ToolPricing(model=PricingModel.FREE),
                endpoint="wallet_*",
                tags=["wallet", "mind", "economy", "balance"],
                verified=True,
            ),
            Tool(
                id="native_ui_asset",
                name="UI Asset Generator",
                description="Generate UI assets using AI",
                tool_type=ToolType.NATIVE,
                tier=ToolTier.EPIC,
                category=ToolCategory.CREATIVE,
                publisher_id="sos_platform",
                publisher_name="SOS Platform",
                pricing=ToolPricing(model=PricingModel.PER_USE, price_mind=10.0),
                endpoint="generate_ui_asset",
                tags=["ui", "asset", "image", "ai", "creative"],
                verified=True,
            ),
        ]

        for tool in native_tools:
            if tool.id not in self._tools:
                self._tools[tool.id] = tool
                self._index_tool(tool)

    # =========================================================================
    # TOOL REGISTRATION
    # =========================================================================

    def register_tool(
        self,
        name: str,
        description: str,
        tool_type: ToolType,
        publisher_id: str,
        publisher_name: str = "",
        tier: ToolTier = ToolTier.COMMON,
        category: ToolCategory = ToolCategory.PRODUCTIVITY,
        pricing: Optional[ToolPricing] = None,
        mcp_server: Optional[str] = None,
        endpoint: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        tool_chain: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        icon: Optional[str] = None,
        documentation_url: Optional[str] = None,
    ) -> Tool:
        """
        Register a new tool in the marketplace.

        Args:
            name: Human-readable name
            description: What the tool does
            tool_type: NATIVE, MCP, COMPOSITE, or CUSTOM
            publisher_id: Guild or Agent ID
            publisher_name: Display name for publisher
            tier: COMMON, RARE, EPIC, or LEGENDARY
            category: Tool category for discovery
            pricing: Pricing configuration
            mcp_server: MCP server name (for MCP tools)
            endpoint: API endpoint (for native tools)
            schema: Input/output schema
            tool_chain: List of tool IDs (for composite tools)
            tags: Search tags
            icon: Icon URL
            documentation_url: Docs URL

        Returns:
            The registered Tool
        """
        tool_id = f"tool_{hashlib.sha256(f'{name}{publisher_id}'.encode()).hexdigest()[:12]}"

        tool = Tool(
            id=tool_id,
            name=name,
            description=description,
            tool_type=tool_type,
            tier=tier,
            category=category,
            publisher_id=publisher_id,
            publisher_name=publisher_name,
            pricing=pricing or ToolPricing(model=PricingModel.FREE),
            mcp_server=mcp_server,
            endpoint=endpoint,
            schema=schema or {},
            tool_chain=tool_chain or [],
            tags=tags or [],
            icon=icon,
            documentation_url=documentation_url,
            versions=[ToolVersion(version="1.0.0", changelog="Initial release")],
        )

        self._tools[tool_id] = tool
        self._index_tool(tool)
        self._save_registry()

        log.info(f"Tool registered: {tool_id} - {name} by {publisher_name}")
        return tool

    def update_tool(
        self,
        tool_id: str,
        publisher_id: str,
        **updates
    ) -> Optional[Tool]:
        """Update a tool (only by publisher)."""
        tool = self._tools.get(tool_id)
        if not tool:
            return None

        if tool.publisher_id != publisher_id:
            log.warning(f"Unauthorized update attempt: {publisher_id} on {tool_id}")
            return None

        for key, value in updates.items():
            if hasattr(tool, key) and key not in ["id", "publisher_id", "created_at"]:
                setattr(tool, key, value)

        tool.updated_at = datetime.now(timezone.utc)
        self._save_registry()

        return tool

    def publish_version(
        self,
        tool_id: str,
        publisher_id: str,
        version: str,
        changelog: str = ""
    ) -> Optional[ToolVersion]:
        """Publish a new version of a tool."""
        tool = self._tools.get(tool_id)
        if not tool or tool.publisher_id != publisher_id:
            return None

        new_version = ToolVersion(version=version, changelog=changelog)
        tool.versions.append(new_version)
        tool.current_version = version
        tool.updated_at = datetime.now(timezone.utc)
        self._save_registry()

        log.info(f"Version {version} published for {tool_id}")
        return new_version

    # =========================================================================
    # LICENSING
    # =========================================================================

    def grant_license(
        self,
        tool_id: str,
        user_id: str,
        license_type: LicenseType = LicenseType.LICENSED,
        duration_days: Optional[int] = None,
        usage_count: Optional[int] = None,
    ) -> Optional[ToolLicense]:
        """
        Grant a license to use a tool.

        Called after purchase/subscription payment.
        """
        tool = self._tools.get(tool_id)
        if not tool:
            return None

        license_id = f"lic_{uuid.uuid4().hex[:12]}"

        expires_at = None
        if duration_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
        elif tool.pricing.model == PricingModel.SUBSCRIPTION:
            expires_at = datetime.now(timezone.utc) + timedelta(days=tool.pricing.subscription_days)

        license = ToolLicense(
            id=license_id,
            tool_id=tool_id,
            user_id=user_id,
            license_type=license_type,
            expires_at=expires_at,
            usage_remaining=usage_count,
        )

        self._licenses[license_id] = license
        self._save_registry()

        log.info(f"License granted: {license_id} for {user_id} on {tool_id}")
        return license

    def check_license(self, tool_id: str, user_id: str) -> tuple[bool, Optional[ToolLicense]]:
        """
        Check if user has valid license for tool.

        Returns (has_access, license)
        """
        tool = self._tools.get(tool_id)
        if not tool:
            return False, None

        # Free tools don't need license
        if tool.pricing.model == PricingModel.FREE:
            return True, None

        # Find valid license
        for lic in self._licenses.values():
            if lic.tool_id == tool_id and lic.user_id == user_id and lic.is_valid:
                return True, lic

        return False, None

    def consume_usage(self, license_id: str) -> bool:
        """Consume one usage from a per-use license."""
        lic = self._licenses.get(license_id)
        if not lic or not lic.is_valid:
            return False

        if lic.usage_remaining is not None:
            lic.usage_remaining -= 1
            self._save_registry()

        return True

    # =========================================================================
    # USAGE METERING
    # =========================================================================

    def record_usage(
        self,
        tool_id: str,
        user_id: str,
        duration_ms: float = 0.0,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolUsage:
        """
        Record a tool usage event.

        Called after tool execution for billing and analytics.
        """
        tool = self._tools.get(tool_id)
        cost = 0.0

        if tool:
            tool.total_uses += 1

            if tool.pricing.model == PricingModel.PER_USE:
                cost = tool.pricing.price_mind
                tool.total_revenue += cost

        usage = ToolUsage(
            tool_id=tool_id,
            user_id=user_id,
            duration_ms=duration_ms,
            cost_mind=cost,
            success=success,
            metadata=metadata or {},
        )

        self._usage.append(usage)

        # Keep only last 10000 usage records in memory
        if len(self._usage) > 10000:
            self._usage = self._usage[-10000:]

        self._save_registry()
        return usage

    def get_usage_stats(
        self,
        tool_id: Optional[str] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics."""
        filtered = self._usage

        if tool_id:
            filtered = [u for u in filtered if u.tool_id == tool_id]
        if user_id:
            filtered = [u for u in filtered if u.user_id == user_id]
        if since:
            filtered = [u for u in filtered if u.used_at >= since]

        return {
            "total_uses": len(filtered),
            "total_cost": sum(u.cost_mind for u in filtered),
            "success_rate": sum(1 for u in filtered if u.success) / len(filtered) if filtered else 0,
            "avg_duration_ms": sum(u.duration_ms for u in filtered) / len(filtered) if filtered else 0,
        }

    # =========================================================================
    # RATINGS
    # =========================================================================

    def rate_tool(
        self,
        tool_id: str,
        user_id: str,
        rating: int,
        review: str = ""
    ) -> Optional[ToolRating]:
        """Rate a tool (1-5 stars)."""
        tool = self._tools.get(tool_id)
        if not tool or rating < 1 or rating > 5:
            return None

        # Remove previous rating from same user
        self._ratings[tool_id] = [
            r for r in self._ratings[tool_id] if r.user_id != user_id
        ]

        tool_rating = ToolRating(user_id=user_id, rating=rating, review=review)
        self._ratings[tool_id].append(tool_rating)

        # Update average
        ratings = self._ratings[tool_id]
        tool.avg_rating = sum(r.rating for r in ratings) / len(ratings)
        tool.rating_count = len(ratings)

        self._save_registry()
        return tool_rating

    def get_ratings(self, tool_id: str) -> List[ToolRating]:
        """Get all ratings for a tool."""
        return self._ratings.get(tool_id, [])

    # =========================================================================
    # DISCOVERY
    # =========================================================================

    def get(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[ToolCategory] = None,
        tier: Optional[ToolTier] = None,
        pricing_model: Optional[PricingModel] = None,
        publisher_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        verified_only: bool = False,
        limit: int = 50,
    ) -> List[Tool]:
        """
        Search for tools.

        Returns tools matching all specified criteria.
        """
        candidates = set(self._tools.keys())

        # Filter by category
        if category:
            candidates &= self._by_category.get(category, set())

        # Filter by publisher
        if publisher_id:
            candidates &= self._by_publisher.get(publisher_id, set())

        # Filter by tags
        if tags:
            for tag in tags:
                candidates &= self._by_tag.get(tag.lower(), set())

        # Get tools and apply remaining filters
        results = []
        for tool_id in candidates:
            tool = self._tools.get(tool_id)
            if not tool or not tool.published:
                continue

            if tier and tool.tier != tier:
                continue
            if pricing_model and tool.pricing.model != pricing_model:
                continue
            if verified_only and not tool.verified:
                continue

            # Text search
            if query:
                query_lower = query.lower()
                if not (
                    query_lower in tool.name.lower() or
                    query_lower in tool.description.lower() or
                    any(query_lower in tag.lower() for tag in tool.tags)
                ):
                    continue

            results.append(tool)

        # Sort by rating then uses
        results.sort(key=lambda t: (t.avg_rating, t.total_uses), reverse=True)

        return results[:limit]

    def list_by_category(self, category: ToolCategory) -> List[Tool]:
        """List all tools in a category."""
        return self.search(category=category)

    def list_popular(self, limit: int = 20) -> List[Tool]:
        """List most popular tools by usage."""
        tools = [t for t in self._tools.values() if t.published]
        tools.sort(key=lambda t: t.total_uses, reverse=True)
        return tools[:limit]

    def list_top_rated(self, limit: int = 20) -> List[Tool]:
        """List top-rated tools."""
        tools = [t for t in self._tools.values() if t.published and t.rating_count >= 3]
        tools.sort(key=lambda t: t.avg_rating, reverse=True)
        return tools[:limit]

    def list_by_publisher(self, publisher_id: str) -> List[Tool]:
        """List all tools from a publisher."""
        return self.search(publisher_id=publisher_id)

    # =========================================================================
    # REVENUE
    # =========================================================================

    def calculate_revenue(
        self,
        publisher_id: str,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate revenue for a publisher."""
        tools = self.list_by_publisher(publisher_id)

        total_revenue = sum(t.total_revenue for t in tools)
        publisher_share = total_revenue * (1 - self.PLATFORM_FEE)

        return {
            "total_revenue": total_revenue,
            "publisher_share": publisher_share,
            "platform_fee": total_revenue * self.PLATFORM_FEE,
            "tool_count": len(tools),
            "total_uses": sum(t.total_uses for t in tools),
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        tools = list(self._tools.values())

        type_counts = {}
        for tt in ToolType:
            type_counts[tt.value] = sum(1 for t in tools if t.tool_type == tt)

        tier_counts = {}
        for tier in ToolTier:
            tier_counts[tier.value] = sum(1 for t in tools if t.tier == tier)

        category_counts = {}
        for cat in ToolCategory:
            category_counts[cat.value] = sum(1 for t in tools if t.category == cat)

        return {
            "total_tools": len(tools),
            "published_tools": sum(1 for t in tools if t.published),
            "verified_tools": sum(1 for t in tools if t.verified),
            "total_licenses": len(self._licenses),
            "active_licenses": sum(1 for l in self._licenses.values() if l.is_valid),
            "total_uses": sum(t.total_uses for t in tools),
            "total_revenue": sum(t.total_revenue for t in tools),
            "type_counts": type_counts,
            "tier_counts": tier_counts,
            "category_counts": category_counts,
        }


# Singleton
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
