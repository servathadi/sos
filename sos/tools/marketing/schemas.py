"""
Marketing Toolkit Schemas

Data models for marketing integrations.
Platform-agnostic so any adapter can use them.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class Platform(Enum):
    """Marketing platforms we support."""
    GOOGLE_ANALYTICS = "google_analytics"
    GOOGLE_ADS = "google_ads"
    FACEBOOK_ADS = "facebook_ads"
    SEARCH_CONSOLE = "search_console"
    CLARITY = "clarity"
    CUSTOM = "custom"


class AccountType(Enum):
    """Type of account connection."""
    OAUTH = "oauth"           # OAuth 2.0 token
    API_KEY = "api_key"       # Simple API key
    SERVICE_ACCOUNT = "service_account"  # GCP service account
    MCC = "mcc"               # Google Ads MCC (manager account)


class AdStatus(Enum):
    """Ad/campaign status."""
    ACTIVE = "active"
    PAUSED = "paused"
    REMOVED = "removed"
    PENDING = "pending"
    ENDED = "ended"


class InsightType(Enum):
    """Type of marketing insight."""
    OPPORTUNITY = "opportunity"    # Something to improve
    WARNING = "warning"            # Something going wrong
    SUCCESS = "success"            # Something working well
    ACTION = "action"              # Recommended action


class InsightPriority(Enum):
    """Priority of insight."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# ACCOUNT & CREDENTIALS
# =============================================================================

@dataclass
class MarketingAccount:
    """
    A connected marketing account for a business.

    Each business can have multiple accounts (GA, Ads, etc.)
    """
    id: str                              # Unique account ID
    business_id: str                     # Business this belongs to
    platform: Platform                   # Which platform
    account_type: AccountType            # How we connect

    # Platform-specific IDs
    platform_account_id: Optional[str] = None  # e.g., GA property ID
    platform_name: Optional[str] = None        # Human-readable name

    # Credentials (encrypted in storage)
    credentials: Dict[str, Any] = field(default_factory=dict)

    # Status
    connected: bool = False
    last_sync: Optional[datetime] = None
    error: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "business_id": self.business_id,
            "platform": self.platform.value,
            "account_type": self.account_type.value,
            "platform_account_id": self.platform_account_id,
            "platform_name": self.platform_name,
            "connected": self.connected,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# ANALYTICS DATA
# =============================================================================

@dataclass
class AnalyticsData:
    """
    Website analytics data (from GA4 or similar).
    """
    business_id: str
    date_range: tuple[date, date]       # (start, end)

    # Traffic
    sessions: int = 0
    users: int = 0
    new_users: int = 0
    pageviews: int = 0

    # Engagement
    avg_session_duration: float = 0.0   # seconds
    bounce_rate: float = 0.0            # 0-1
    pages_per_session: float = 0.0

    # Sources
    traffic_sources: Dict[str, int] = field(default_factory=dict)
    # e.g., {"google": 500, "direct": 200, "facebook": 100}

    # Top pages
    top_pages: List[Dict[str, Any]] = field(default_factory=list)
    # e.g., [{"path": "/", "views": 1000}, {"path": "/services", "views": 500}]

    # Conversions
    conversions: int = 0
    conversion_rate: float = 0.0
    goals: Dict[str, int] = field(default_factory=dict)

    # Comparison to previous period
    sessions_change: float = 0.0        # % change
    users_change: float = 0.0
    conversions_change: float = 0.0

    # Metadata
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    platform: Platform = Platform.GOOGLE_ANALYTICS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "date_range": [d.isoformat() for d in self.date_range],
            "sessions": self.sessions,
            "users": self.users,
            "new_users": self.new_users,
            "pageviews": self.pageviews,
            "avg_session_duration": self.avg_session_duration,
            "bounce_rate": self.bounce_rate,
            "pages_per_session": self.pages_per_session,
            "traffic_sources": self.traffic_sources,
            "top_pages": self.top_pages,
            "conversions": self.conversions,
            "conversion_rate": self.conversion_rate,
            "sessions_change": self.sessions_change,
            "users_change": self.users_change,
            "conversions_change": self.conversions_change,
            "fetched_at": self.fetched_at.isoformat(),
            "platform": self.platform.value,
        }


# =============================================================================
# ADS DATA
# =============================================================================

@dataclass
class AdsCampaign:
    """A single ad campaign."""
    id: str
    name: str
    status: AdStatus
    platform: Platform

    # Budget
    daily_budget: float = 0.0
    total_budget: Optional[float] = None
    currency: str = "CAD"

    # Performance
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0                    # Click-through rate
    conversions: int = 0
    conversion_rate: float = 0.0

    # Cost
    spend: float = 0.0
    cpc: float = 0.0                    # Cost per click
    cpa: float = 0.0                    # Cost per acquisition
    roas: float = 0.0                   # Return on ad spend

    # Dates
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "platform": self.platform.value,
            "daily_budget": self.daily_budget,
            "spend": self.spend,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "ctr": self.ctr,
            "conversions": self.conversions,
            "cpc": self.cpc,
            "cpa": self.cpa,
        }


@dataclass
class AdsData:
    """
    Aggregated ads data across campaigns.
    """
    business_id: str
    platform: Platform
    date_range: tuple[date, date]

    # Campaigns
    campaigns: List[AdsCampaign] = field(default_factory=list)
    active_campaigns: int = 0
    paused_campaigns: int = 0

    # Totals
    total_spend: float = 0.0
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0

    # Averages
    avg_ctr: float = 0.0
    avg_cpc: float = 0.0
    avg_cpa: float = 0.0

    # Budget
    daily_budget: float = 0.0
    monthly_budget: float = 0.0
    budget_remaining: float = 0.0

    # Comparison
    spend_change: float = 0.0
    conversions_change: float = 0.0

    # Metadata
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    currency: str = "CAD"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "platform": self.platform.value,
            "date_range": [d.isoformat() for d in self.date_range],
            "campaigns": [c.to_dict() for c in self.campaigns],
            "active_campaigns": self.active_campaigns,
            "total_spend": self.total_spend,
            "total_impressions": self.total_impressions,
            "total_clicks": self.total_clicks,
            "total_conversions": self.total_conversions,
            "avg_ctr": self.avg_ctr,
            "avg_cpc": self.avg_cpc,
            "avg_cpa": self.avg_cpa,
            "fetched_at": self.fetched_at.isoformat(),
        }


# =============================================================================
# SEARCH CONSOLE DATA
# =============================================================================

@dataclass
class SearchQuery:
    """A search query from Search Console."""
    query: str
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    position: float = 0.0               # Average position


@dataclass
class SearchConsoleData:
    """
    Search Console / SEO data.
    """
    business_id: str
    date_range: tuple[date, date]

    # Totals
    total_impressions: int = 0
    total_clicks: int = 0
    avg_ctr: float = 0.0
    avg_position: float = 0.0

    # Top queries
    top_queries: List[SearchQuery] = field(default_factory=list)

    # Top pages
    top_pages: List[Dict[str, Any]] = field(default_factory=list)
    # e.g., [{"url": "/invisalign", "clicks": 50, "impressions": 1000}]

    # Issues
    indexing_issues: int = 0
    mobile_issues: int = 0

    # Comparison
    clicks_change: float = 0.0
    impressions_change: float = 0.0
    position_change: float = 0.0

    # Metadata
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "date_range": [d.isoformat() for d in self.date_range],
            "total_impressions": self.total_impressions,
            "total_clicks": self.total_clicks,
            "avg_ctr": self.avg_ctr,
            "avg_position": self.avg_position,
            "top_queries": [
                {"query": q.query, "clicks": q.clicks, "impressions": q.impressions, "position": q.position}
                for q in self.top_queries[:10]
            ],
            "top_pages": self.top_pages[:10],
            "clicks_change": self.clicks_change,
            "position_change": self.position_change,
            "fetched_at": self.fetched_at.isoformat(),
        }


# =============================================================================
# CLARITY DATA
# =============================================================================

@dataclass
class ClarityData:
    """
    Microsoft Clarity behavior data.
    """
    business_id: str
    date_range: tuple[date, date]

    # Sessions
    total_sessions: int = 0
    sessions_with_recordings: int = 0

    # Engagement
    avg_scroll_depth: float = 0.0       # 0-100%
    rage_clicks: int = 0                # Frustration indicator
    dead_clicks: int = 0                # Clicks on non-interactive elements
    quick_backs: int = 0                # Quick returns to previous page

    # Performance
    avg_page_load: float = 0.0          # seconds

    # Heatmap data (simplified)
    click_hotspots: List[Dict[str, Any]] = field(default_factory=list)
    # e.g., [{"selector": ".cta-button", "clicks": 500}]

    # Top insights
    insights: List[str] = field(default_factory=list)

    # Metadata
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "date_range": [d.isoformat() for d in self.date_range],
            "total_sessions": self.total_sessions,
            "avg_scroll_depth": self.avg_scroll_depth,
            "rage_clicks": self.rage_clicks,
            "dead_clicks": self.dead_clicks,
            "quick_backs": self.quick_backs,
            "avg_page_load": self.avg_page_load,
            "insights": self.insights,
            "fetched_at": self.fetched_at.isoformat(),
        }


# =============================================================================
# UNIFIED DASHBOARD
# =============================================================================

@dataclass
class MarketingDashboard:
    """
    Unified marketing dashboard combining all sources.
    """
    business_id: str
    business_name: str
    date_range: tuple[date, date]

    # Data from each source
    analytics: Optional[AnalyticsData] = None
    google_ads: Optional[AdsData] = None
    facebook_ads: Optional[AdsData] = None
    search_console: Optional[SearchConsoleData] = None
    clarity: Optional[ClarityData] = None

    # Unified metrics
    total_traffic: int = 0
    total_leads: int = 0
    total_ad_spend: float = 0.0
    total_conversions: int = 0
    overall_conversion_rate: float = 0.0
    cost_per_lead: float = 0.0

    # Health score (0-100)
    health_score: int = 0

    # Connected accounts
    connected_platforms: List[Platform] = field(default_factory=list)

    # Generated insights
    insights: List["MarketingInsight"] = field(default_factory=list)

    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "business_name": self.business_name,
            "date_range": [d.isoformat() for d in self.date_range],
            "analytics": self.analytics.to_dict() if self.analytics else None,
            "google_ads": self.google_ads.to_dict() if self.google_ads else None,
            "facebook_ads": self.facebook_ads.to_dict() if self.facebook_ads else None,
            "search_console": self.search_console.to_dict() if self.search_console else None,
            "clarity": self.clarity.to_dict() if self.clarity else None,
            "total_traffic": self.total_traffic,
            "total_leads": self.total_leads,
            "total_ad_spend": self.total_ad_spend,
            "total_conversions": self.total_conversions,
            "cost_per_lead": self.cost_per_lead,
            "health_score": self.health_score,
            "connected_platforms": [p.value for p in self.connected_platforms],
            "insights": [i.to_dict() for i in self.insights],
            "generated_at": self.generated_at.isoformat(),
        }


# =============================================================================
# INSIGHTS
# =============================================================================

@dataclass
class MarketingInsight:
    """
    An actionable insight generated from marketing data.
    """
    id: str
    business_id: str
    type: InsightType
    priority: InsightPriority

    # Content
    title: str
    description: str
    recommendation: Optional[str] = None

    # Action (if applicable)
    action_type: Optional[str] = None   # e.g., "pause_campaign", "adjust_bid"
    action_params: Dict[str, Any] = field(default_factory=dict)
    action_approved: bool = False
    action_executed: bool = False

    # Source
    platform: Optional[Platform] = None
    metric: Optional[str] = None        # e.g., "ctr", "bounce_rate"
    current_value: Optional[float] = None
    threshold: Optional[float] = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "business_id": self.business_id,
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "action_type": self.action_type,
            "action_approved": self.action_approved,
            "action_executed": self.action_executed,
            "platform": self.platform.value if self.platform else None,
            "metric": self.metric,
            "current_value": self.current_value,
            "created_at": self.created_at.isoformat(),
        }
