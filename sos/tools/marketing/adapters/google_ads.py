"""
Google Ads Adapter

Fetches and manages Google Ads campaigns.

Requires:
- OAuth credentials or MCC access
- Customer ID

Docs: https://developers.google.com/google-ads/api/docs/start
"""

import os
from datetime import date
from typing import Optional, Dict, Any, List

import httpx

from .base import BaseMarketingAdapter
from ..schemas import (
    MarketingAccount,
    AdsData,
    AdsCampaign,
    AdStatus,
    Platform,
    AccountType,
)


class GoogleAdsAdapter(BaseMarketingAdapter):
    """
    Google Ads adapter.

    Uses Google Ads API for campaign management and reporting.
    """

    PLATFORM = Platform.GOOGLE_ADS
    REQUIRES_OAUTH = True
    SCOPES = [
        "https://www.googleapis.com/auth/adwords",
    ]

    # API version and endpoint
    API_VERSION = "v15"
    BASE_URL = "https://googleads.googleapis.com"

    def __init__(self, account: MarketingAccount):
        super().__init__(account)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def customer_id(self) -> Optional[str]:
        """Google Ads customer ID (without dashes)."""
        cid = self._get_credential("customer_id")
        return cid.replace("-", "") if cid else None

    @property
    def access_token(self) -> Optional[str]:
        return self._get_credential("access_token")

    @property
    def developer_token(self) -> Optional[str]:
        """Google Ads API developer token."""
        return self._get_credential("developer_token") or os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")

    # =========================================================================
    # CONNECTION
    # =========================================================================

    async def connect(self) -> bool:
        if not self.access_token or not self.customer_id:
            self._set_error("Missing access token or customer ID")
            return False

        if not self.developer_token:
            self._set_error("Missing developer token")
            return False

        try:
            self._http_client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "developer-token": self.developer_token,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            self._connected = True
            self._clear_error()
            return True

        except Exception as e:
            self._set_error(f"Connection failed: {str(e)}")
            return False

    async def disconnect(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    async def refresh_credentials(self) -> bool:
        """Refresh OAuth token."""
        refresh_token = self._get_credential("refresh_token")
        client_id = self._get_credential("client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = self._get_credential("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")

        if not all([refresh_token, client_id, client_secret]):
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self.account.credentials["access_token"] = data["access_token"]
                    return True

        except Exception as e:
            self._set_error(f"Token refresh error: {str(e)}")

        return False

    async def test_connection(self) -> bool:
        return self._connected

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    async def fetch_data(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch campaign data via GAQL query."""
        if not self._connected:
            await self.connect()

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign_budget.amount_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            WHERE segments.date BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
        """

        response = await self._http_client.post(
            f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/googleAds:searchStream",
            json={"query": query},
        )

        if response.status_code != 200:
            raise Exception(f"Google Ads API error: {response.status_code}")

        return response.json()

    async def get_ads_data(
        self,
        start_date: date,
        end_date: date,
    ) -> AdsData:
        """Get formatted ads data."""
        try:
            raw_data = await self.fetch_data(start_date, end_date)
            campaigns = self._parse_campaigns(raw_data)
        except Exception:
            # Return empty data on error
            campaigns = []

        # Calculate totals
        total_spend = sum(c.spend for c in campaigns)
        total_impressions = sum(c.impressions for c in campaigns)
        total_clicks = sum(c.clicks for c in campaigns)
        total_conversions = sum(c.conversions for c in campaigns)

        self._update_last_sync()

        return AdsData(
            business_id=self.business_id,
            platform=Platform.GOOGLE_ADS,
            date_range=(start_date, end_date),
            campaigns=campaigns,
            active_campaigns=len([c for c in campaigns if c.status == AdStatus.ACTIVE]),
            paused_campaigns=len([c for c in campaigns if c.status == AdStatus.PAUSED]),
            total_spend=total_spend,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            avg_ctr=(total_clicks / total_impressions * 100) if total_impressions else 0,
            avg_cpc=(total_spend / total_clicks) if total_clicks else 0,
            avg_cpa=(total_spend / total_conversions) if total_conversions else 0,
        )

    def _parse_campaigns(self, raw_data: Dict[str, Any]) -> List[AdsCampaign]:
        """Parse Google Ads response into campaigns."""
        campaigns = []

        for batch in raw_data.get("results", []):
            for row in batch.get("results", []):
                campaign = row.get("campaign", {})
                metrics = row.get("metrics", {})
                budget = row.get("campaignBudget", {})

                status_map = {
                    "ENABLED": AdStatus.ACTIVE,
                    "PAUSED": AdStatus.PAUSED,
                    "REMOVED": AdStatus.REMOVED,
                }

                campaigns.append(AdsCampaign(
                    id=str(campaign.get("id", "")),
                    name=campaign.get("name", "Unknown"),
                    status=status_map.get(campaign.get("status", ""), AdStatus.ACTIVE),
                    platform=Platform.GOOGLE_ADS,
                    daily_budget=budget.get("amountMicros", 0) / 1_000_000,
                    impressions=int(metrics.get("impressions", 0)),
                    clicks=int(metrics.get("clicks", 0)),
                    ctr=float(metrics.get("ctr", 0)),
                    conversions=int(float(metrics.get("conversions", 0))),
                    spend=metrics.get("costMicros", 0) / 1_000_000,
                    cpc=metrics.get("averageCpc", 0) / 1_000_000,
                ))

        return campaigns

    # =========================================================================
    # ACTIONS
    # =========================================================================

    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign."""
        return await self._update_campaign_status(campaign_id, "PAUSED")

    async def resume_campaign(self, campaign_id: str) -> bool:
        """Resume a paused campaign."""
        return await self._update_campaign_status(campaign_id, "ENABLED")

    async def _update_campaign_status(self, campaign_id: str, status: str) -> bool:
        """Update campaign status."""
        if not self._connected:
            return False

        try:
            mutation = {
                "operations": [{
                    "update": {
                        "resourceName": f"customers/{self.customer_id}/campaigns/{campaign_id}",
                        "status": status,
                    },
                    "updateMask": "status",
                }],
            }

            response = await self._http_client.post(
                f"{self.BASE_URL}/{self.API_VERSION}/customers/{self.customer_id}/campaigns:mutate",
                json=mutation,
            )

            return response.status_code == 200

        except Exception:
            return False

    async def set_budget(self, campaign_id: str, daily_budget: float) -> bool:
        """Set campaign daily budget."""
        # Budget updates require knowing the budget resource name
        # This is a simplified implementation
        return False


# =============================================================================
# FACTORY
# =============================================================================

def create_google_ads_account(
    business_id: str,
    customer_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    developer_token: Optional[str] = None,
) -> MarketingAccount:
    """Create a Google Ads account configuration."""
    return MarketingAccount(
        id=f"{business_id}_google_ads",
        business_id=business_id,
        platform=Platform.GOOGLE_ADS,
        account_type=AccountType.OAUTH,
        platform_account_id=customer_id,
        platform_name=f"Google Ads {customer_id}",
        credentials={
            "customer_id": customer_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "developer_token": developer_token,
        },
    )
