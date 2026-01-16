"""
Marketing Client

Unified client for all marketing integrations.
This is the main interface that SOS projects use.

Usage:
    from sos.tools.marketing import MarketingClient

    client = MarketingClient(business_id="smile_dental")

    # Connect platforms
    await client.connect_google_analytics(property_id, access_token)
    await client.connect_google_ads(customer_id, access_token)

    # Get unified dashboard
    dashboard = await client.get_dashboard(days=30)

    # Get AI-generated insights
    insights = await client.analyze()
"""

import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Dict, List

from .schemas import (
    MarketingAccount,
    AnalyticsData,
    AdsData,
    SearchConsoleData,
    ClarityData,
    MarketingDashboard,
    MarketingInsight,
    InsightType,
    InsightPriority,
    Platform,
)

from .adapters.base import BaseMarketingAdapter
from .adapters.google_analytics import GoogleAnalyticsAdapter, create_ga4_account
from .adapters.google_ads import GoogleAdsAdapter, create_google_ads_account
from .adapters.facebook_ads import FacebookAdsAdapter, create_facebook_ads_account
from .adapters.search_console import SearchConsoleAdapter, create_search_console_account
from .adapters.clarity import ClarityAdapter, create_clarity_account


class MarketingClient:
    """
    Unified marketing client for a business.

    Aggregates data from multiple platforms into a single dashboard.
    """

    def __init__(
        self,
        business_id: str,
        business_name: Optional[str] = None,
        storage_path: Optional[Path] = None,
    ):
        self.business_id = business_id
        self.business_name = business_name or business_id

        # Storage for accounts
        self.storage_path = storage_path or Path.home() / ".sos" / "marketing" / business_id
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Adapters
        self._adapters: Dict[Platform, BaseMarketingAdapter] = {}
        self._accounts: Dict[Platform, MarketingAccount] = {}

        # Load existing accounts
        self._load_accounts()

    # =========================================================================
    # ACCOUNT MANAGEMENT
    # =========================================================================

    def _load_accounts(self):
        """Load saved accounts from storage."""
        accounts_file = self.storage_path / "accounts.json"
        if accounts_file.exists():
            try:
                data = json.loads(accounts_file.read_text())
                for platform_str, account_data in data.items():
                    platform = Platform(platform_str)
                    account = MarketingAccount(
                        id=account_data["id"],
                        business_id=account_data["business_id"],
                        platform=platform,
                        account_type=account_data.get("account_type", "oauth"),
                        platform_account_id=account_data.get("platform_account_id"),
                        credentials=account_data.get("credentials", {}),
                    )
                    self._accounts[platform] = account
            except Exception:
                pass

    def _save_accounts(self):
        """Save accounts to storage."""
        accounts_file = self.storage_path / "accounts.json"
        data = {}
        for platform, account in self._accounts.items():
            data[platform.value] = {
                "id": account.id,
                "business_id": account.business_id,
                "platform_account_id": account.platform_account_id,
                "account_type": account.account_type.value if hasattr(account.account_type, 'value') else account.account_type,
                "credentials": account.credentials,
            }
        accounts_file.write_text(json.dumps(data, indent=2))

    def get_connected_platforms(self) -> List[Platform]:
        """Get list of connected platforms."""
        return list(self._accounts.keys())

    # =========================================================================
    # CONNECT PLATFORMS
    # =========================================================================

    async def connect_google_analytics(
        self,
        property_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> bool:
        """
        Connect Google Analytics 4.

        Args:
            property_id: GA4 property ID (e.g., "123456789")
            access_token: OAuth access token
            refresh_token: OAuth refresh token for auto-renewal

        Returns:
            True if connected successfully
        """
        account = create_ga4_account(
            business_id=self.business_id,
            property_id=property_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        adapter = GoogleAnalyticsAdapter(account)
        if await adapter.connect():
            self._accounts[Platform.GOOGLE_ANALYTICS] = account
            self._adapters[Platform.GOOGLE_ANALYTICS] = adapter
            self._save_accounts()
            return True
        return False

    async def connect_google_ads(
        self,
        customer_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        developer_token: Optional[str] = None,
    ) -> bool:
        """
        Connect Google Ads.

        Args:
            customer_id: Google Ads customer ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            developer_token: Google Ads API developer token

        Returns:
            True if connected successfully
        """
        account = create_google_ads_account(
            business_id=self.business_id,
            customer_id=customer_id,
            access_token=access_token,
            refresh_token=refresh_token,
            developer_token=developer_token,
        )

        adapter = GoogleAdsAdapter(account)
        if await adapter.connect():
            self._accounts[Platform.GOOGLE_ADS] = account
            self._adapters[Platform.GOOGLE_ADS] = adapter
            self._save_accounts()
            return True
        return False

    async def connect_facebook_ads(
        self,
        ad_account_id: str,
        access_token: str,
    ) -> bool:
        """
        Connect Facebook/Meta Ads.

        Args:
            ad_account_id: Facebook Ad Account ID
            access_token: Access token with ads_read permission

        Returns:
            True if connected successfully
        """
        account = create_facebook_ads_account(
            business_id=self.business_id,
            ad_account_id=ad_account_id,
            access_token=access_token,
        )

        adapter = FacebookAdsAdapter(account)
        if await adapter.connect():
            self._accounts[Platform.FACEBOOK_ADS] = account
            self._adapters[Platform.FACEBOOK_ADS] = adapter
            self._save_accounts()
            return True
        return False

    async def connect_search_console(
        self,
        site_url: str,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> bool:
        """
        Connect Google Search Console.

        Args:
            site_url: Site URL (e.g., "https://example.com")
            access_token: OAuth access token
            refresh_token: OAuth refresh token

        Returns:
            True if connected successfully
        """
        account = create_search_console_account(
            business_id=self.business_id,
            site_url=site_url,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        adapter = SearchConsoleAdapter(account)
        if await adapter.connect():
            self._accounts[Platform.SEARCH_CONSOLE] = account
            self._adapters[Platform.SEARCH_CONSOLE] = adapter
            self._save_accounts()
            return True
        return False

    async def connect_clarity(
        self,
        project_id: str,
        api_token: Optional[str] = None,
    ) -> bool:
        """
        Connect Microsoft Clarity.

        Args:
            project_id: Clarity project ID
            api_token: Optional API token

        Returns:
            True if connected successfully
        """
        account = create_clarity_account(
            business_id=self.business_id,
            project_id=project_id,
            api_token=api_token,
        )

        adapter = ClarityAdapter(account)
        if await adapter.connect():
            self._accounts[Platform.CLARITY] = account
            self._adapters[Platform.CLARITY] = adapter
            self._save_accounts()
            return True
        return False

    # =========================================================================
    # GET DATA
    # =========================================================================

    async def get_analytics(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[AnalyticsData]:
        """Get Google Analytics data."""
        if Platform.GOOGLE_ANALYTICS not in self._adapters:
            return None

        end = end_date or date.today()
        start = start_date or (end - timedelta(days=days))

        adapter: GoogleAnalyticsAdapter = self._adapters[Platform.GOOGLE_ANALYTICS]
        return await adapter.get_analytics_data(start, end)

    async def get_google_ads(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[AdsData]:
        """Get Google Ads data."""
        if Platform.GOOGLE_ADS not in self._adapters:
            return None

        end = end_date or date.today()
        start = start_date or (end - timedelta(days=days))

        adapter: GoogleAdsAdapter = self._adapters[Platform.GOOGLE_ADS]
        return await adapter.get_ads_data(start, end)

    async def get_facebook_ads(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[AdsData]:
        """Get Facebook Ads data."""
        if Platform.FACEBOOK_ADS not in self._adapters:
            return None

        end = end_date or date.today()
        start = start_date or (end - timedelta(days=days))

        adapter: FacebookAdsAdapter = self._adapters[Platform.FACEBOOK_ADS]
        return await adapter.get_ads_data(start, end)

    async def get_search_console(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[SearchConsoleData]:
        """Get Search Console data."""
        if Platform.SEARCH_CONSOLE not in self._adapters:
            return None

        end = end_date or date.today()
        start = start_date or (end - timedelta(days=days))

        adapter: SearchConsoleAdapter = self._adapters[Platform.SEARCH_CONSOLE]
        return await adapter.get_search_data(start, end)

    async def get_clarity(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[ClarityData]:
        """Get Clarity data."""
        if Platform.CLARITY not in self._adapters:
            return None

        end = end_date or date.today()
        start = start_date or (end - timedelta(days=days))

        adapter: ClarityAdapter = self._adapters[Platform.CLARITY]
        return await adapter.get_clarity_data(start, end)

    # =========================================================================
    # UNIFIED DASHBOARD
    # =========================================================================

    async def get_dashboard(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> MarketingDashboard:
        """
        Get unified marketing dashboard.

        Aggregates data from all connected platforms.
        """
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=days))

        # Fetch from all connected platforms
        analytics = await self.get_analytics(start_date=start, end_date=end)
        google_ads = await self.get_google_ads(start_date=start, end_date=end)
        facebook_ads = await self.get_facebook_ads(start_date=start, end_date=end)
        search_console = await self.get_search_console(start_date=start, end_date=end)
        clarity = await self.get_clarity(start_date=start, end_date=end)

        # Calculate unified metrics
        total_traffic = analytics.sessions if analytics else 0
        total_conversions = 0
        total_ad_spend = 0.0

        if analytics:
            total_conversions += analytics.conversions

        if google_ads:
            total_conversions += google_ads.total_conversions
            total_ad_spend += google_ads.total_spend

        if facebook_ads:
            total_conversions += facebook_ads.total_conversions
            total_ad_spend += facebook_ads.total_spend

        # Calculate cost per lead
        cost_per_lead = (total_ad_spend / total_conversions) if total_conversions else 0

        # Calculate health score (simple algorithm)
        health_score = self._calculate_health_score(
            analytics, google_ads, facebook_ads, search_console
        )

        # Generate insights
        insights = await self.analyze(
            analytics=analytics,
            google_ads=google_ads,
            facebook_ads=facebook_ads,
            search_console=search_console,
            clarity=clarity,
        )

        return MarketingDashboard(
            business_id=self.business_id,
            business_name=self.business_name,
            date_range=(start, end),
            analytics=analytics,
            google_ads=google_ads,
            facebook_ads=facebook_ads,
            search_console=search_console,
            clarity=clarity,
            total_traffic=total_traffic,
            total_leads=total_conversions,
            total_ad_spend=total_ad_spend,
            total_conversions=total_conversions,
            cost_per_lead=cost_per_lead,
            health_score=health_score,
            connected_platforms=self.get_connected_platforms(),
            insights=insights,
        )

    def _calculate_health_score(
        self,
        analytics: Optional[AnalyticsData],
        google_ads: Optional[AdsData],
        facebook_ads: Optional[AdsData],
        search_console: Optional[SearchConsoleData],
    ) -> int:
        """Calculate overall marketing health score (0-100)."""
        score = 50  # Base score

        if analytics:
            # Traffic growth
            if analytics.sessions_change > 10:
                score += 10
            elif analytics.sessions_change < -10:
                score -= 10

            # Bounce rate
            if analytics.bounce_rate < 0.4:
                score += 10
            elif analytics.bounce_rate > 0.7:
                score -= 10

        if google_ads:
            # CTR
            if google_ads.avg_ctr > 3:
                score += 10
            elif google_ads.avg_ctr < 1:
                score -= 10

            # CPA efficiency
            if google_ads.avg_cpa > 0 and google_ads.avg_cpa < 50:
                score += 10
            elif google_ads.avg_cpa > 100:
                score -= 10

        if search_console:
            # Position improvement
            if search_console.position_change < 0:  # Lower is better
                score += 5

        return max(0, min(100, score))

    # =========================================================================
    # INSIGHTS / ANALYSIS
    # =========================================================================

    async def analyze(
        self,
        analytics: Optional[AnalyticsData] = None,
        google_ads: Optional[AdsData] = None,
        facebook_ads: Optional[AdsData] = None,
        search_console: Optional[SearchConsoleData] = None,
        clarity: Optional[ClarityData] = None,
    ) -> List[MarketingInsight]:
        """
        Analyze marketing data and generate insights.

        Returns actionable insights and recommendations.
        """
        insights = []

        # Analytics insights
        if analytics:
            # High bounce rate
            if analytics.bounce_rate > 0.6:
                insights.append(MarketingInsight(
                    id=str(uuid.uuid4()),
                    business_id=self.business_id,
                    type=InsightType.WARNING,
                    priority=InsightPriority.HIGH,
                    title="High Bounce Rate",
                    description=f"Bounce rate is {analytics.bounce_rate:.1%}, above the 60% threshold",
                    recommendation="Review landing page content, page speed, and mobile experience",
                    platform=Platform.GOOGLE_ANALYTICS,
                    metric="bounce_rate",
                    current_value=analytics.bounce_rate,
                    threshold=0.6,
                ))

            # Traffic decline
            if analytics.sessions_change < -20:
                insights.append(MarketingInsight(
                    id=str(uuid.uuid4()),
                    business_id=self.business_id,
                    type=InsightType.WARNING,
                    priority=InsightPriority.HIGH,
                    title="Traffic Decline",
                    description=f"Sessions down {abs(analytics.sessions_change):.1f}% vs previous period",
                    recommendation="Check for SEO issues, review recent changes, analyze traffic sources",
                    platform=Platform.GOOGLE_ANALYTICS,
                    metric="sessions",
                    current_value=analytics.sessions_change,
                ))

            # Traffic growth
            if analytics.sessions_change > 20:
                insights.append(MarketingInsight(
                    id=str(uuid.uuid4()),
                    business_id=self.business_id,
                    type=InsightType.SUCCESS,
                    priority=InsightPriority.MEDIUM,
                    title="Traffic Growth",
                    description=f"Sessions up {analytics.sessions_change:.1f}% vs previous period",
                    recommendation="Identify what's working and double down",
                    platform=Platform.GOOGLE_ANALYTICS,
                    metric="sessions",
                    current_value=analytics.sessions_change,
                ))

        # Google Ads insights
        if google_ads:
            # Low CTR
            if google_ads.avg_ctr < 1.5 and google_ads.total_impressions > 1000:
                insights.append(MarketingInsight(
                    id=str(uuid.uuid4()),
                    business_id=self.business_id,
                    type=InsightType.OPPORTUNITY,
                    priority=InsightPriority.HIGH,
                    title="Low Google Ads CTR",
                    description=f"Average CTR is {google_ads.avg_ctr:.2f}%, below the 1.5% benchmark",
                    recommendation="Review ad copy, test new headlines, check keyword relevance",
                    platform=Platform.GOOGLE_ADS,
                    metric="ctr",
                    current_value=google_ads.avg_ctr,
                    threshold=1.5,
                ))

            # High CPA
            if google_ads.avg_cpa > 100:
                insights.append(MarketingInsight(
                    id=str(uuid.uuid4()),
                    business_id=self.business_id,
                    type=InsightType.WARNING,
                    priority=InsightPriority.HIGH,
                    title="High Cost Per Acquisition",
                    description=f"Google Ads CPA is ${google_ads.avg_cpa:.2f}",
                    recommendation="Review targeting, pause underperforming campaigns, optimize landing pages",
                    platform=Platform.GOOGLE_ADS,
                    metric="cpa",
                    current_value=google_ads.avg_cpa,
                ))

            # Paused campaigns
            for campaign in google_ads.campaigns:
                if campaign.status.value == "paused" and campaign.conversions > 0:
                    insights.append(MarketingInsight(
                        id=str(uuid.uuid4()),
                        business_id=self.business_id,
                        type=InsightType.ACTION,
                        priority=InsightPriority.MEDIUM,
                        title="Paused Campaign With Conversions",
                        description=f"'{campaign.name}' is paused but had {campaign.conversions} conversions",
                        recommendation="Consider resuming this campaign",
                        action_type="resume_campaign",
                        action_params={"campaign_id": campaign.id, "platform": "google_ads"},
                        platform=Platform.GOOGLE_ADS,
                    ))

        # Search Console insights
        if search_console:
            # Position opportunity
            for query in search_console.top_queries[:10]:
                if 4 <= query.position <= 10 and query.impressions > 100:
                    insights.append(MarketingInsight(
                        id=str(uuid.uuid4()),
                        business_id=self.business_id,
                        type=InsightType.OPPORTUNITY,
                        priority=InsightPriority.MEDIUM,
                        title=f"SEO Opportunity: '{query.query}'",
                        description=f"Ranking position {query.position:.1f} with {query.impressions} impressions",
                        recommendation="Create or optimize content for this keyword to reach top 3",
                        platform=Platform.SEARCH_CONSOLE,
                        metric="position",
                        current_value=query.position,
                    ))

        # Clarity insights
        if clarity:
            if clarity.rage_clicks > 50:
                insights.append(MarketingInsight(
                    id=str(uuid.uuid4()),
                    business_id=self.business_id,
                    type=InsightType.WARNING,
                    priority=InsightPriority.HIGH,
                    title="User Frustration Detected",
                    description=f"{clarity.rage_clicks} rage clicks detected",
                    recommendation="Review elements users are clicking that aren't interactive",
                    platform=Platform.CLARITY,
                    metric="rage_clicks",
                    current_value=clarity.rage_clicks,
                ))

        # Sort by priority
        priority_order = {
            InsightPriority.CRITICAL: 0,
            InsightPriority.HIGH: 1,
            InsightPriority.MEDIUM: 2,
            InsightPriority.LOW: 3,
        }
        insights.sort(key=lambda x: priority_order[x.priority])

        return insights

    # =========================================================================
    # ACTIONS
    # =========================================================================

    async def pause_campaign(
        self,
        campaign_id: str,
        platform: Platform = Platform.GOOGLE_ADS,
    ) -> bool:
        """Pause an ad campaign."""
        if platform not in self._adapters:
            return False
        return await self._adapters[platform].pause_campaign(campaign_id)

    async def resume_campaign(
        self,
        campaign_id: str,
        platform: Platform = Platform.GOOGLE_ADS,
    ) -> bool:
        """Resume a paused campaign."""
        if platform not in self._adapters:
            return False
        return await self._adapters[platform].resume_campaign(campaign_id)

    async def execute_insight_action(self, insight: MarketingInsight) -> bool:
        """Execute the action recommended by an insight."""
        if not insight.action_type:
            return False

        action_type = insight.action_type
        params = insight.action_params

        if action_type == "pause_campaign":
            platform = Platform(params.get("platform", "google_ads"))
            return await self.pause_campaign(params["campaign_id"], platform)

        elif action_type == "resume_campaign":
            platform = Platform(params.get("platform", "google_ads"))
            return await self.resume_campaign(params["campaign_id"], platform)

        return False

    # =========================================================================
    # CLEANUP
    # =========================================================================

    async def disconnect_all(self):
        """Disconnect all adapters."""
        for adapter in self._adapters.values():
            await adapter.disconnect()
        self._adapters.clear()


# =============================================================================
# SINGLETON
# =============================================================================

_clients: Dict[str, MarketingClient] = {}


def get_marketing_client(
    business_id: str,
    business_name: Optional[str] = None,
) -> MarketingClient:
    """Get or create a marketing client for a business."""
    if business_id not in _clients:
        _clients[business_id] = MarketingClient(
            business_id=business_id,
            business_name=business_name,
        )
    return _clients[business_id]
