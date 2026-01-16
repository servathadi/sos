"""
Facebook/Meta Ads Adapter

Fetches and manages Facebook Ads campaigns.

Requires:
- Access token with ads_read permission
- Ad Account ID

Docs: https://developers.facebook.com/docs/marketing-api
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


class FacebookAdsAdapter(BaseMarketingAdapter):
    """
    Facebook/Meta Ads adapter.

    Uses the Marketing API for campaign management and reporting.
    """

    PLATFORM = Platform.FACEBOOK_ADS
    REQUIRES_OAUTH = True
    SCOPES = [
        "ads_read",
        "ads_management",  # For actions
    ]

    API_VERSION = "v18.0"
    BASE_URL = "https://graph.facebook.com"

    def __init__(self, account: MarketingAccount):
        super().__init__(account)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def ad_account_id(self) -> Optional[str]:
        """Facebook Ad Account ID (with 'act_' prefix)."""
        account_id = self._get_credential("ad_account_id")
        if account_id and not account_id.startswith("act_"):
            return f"act_{account_id}"
        return account_id

    @property
    def access_token(self) -> Optional[str]:
        return self._get_credential("access_token")

    # =========================================================================
    # CONNECTION
    # =========================================================================

    async def connect(self) -> bool:
        if not self.access_token or not self.ad_account_id:
            self._set_error("Missing access token or ad account ID")
            return False

        try:
            self._http_client = httpx.AsyncClient(
                base_url=f"{self.BASE_URL}/{self.API_VERSION}",
                params={"access_token": self.access_token},
                timeout=30.0,
            )

            if await self.test_connection():
                self._connected = True
                self._clear_error()
                return True
            return False

        except Exception as e:
            self._set_error(f"Connection failed: {str(e)}")
            return False

    async def disconnect(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    async def refresh_credentials(self) -> bool:
        """
        Refresh long-lived token.

        Facebook tokens need to be exchanged for long-lived tokens.
        """
        app_id = self._get_credential("app_id") or os.getenv("FACEBOOK_APP_ID")
        app_secret = self._get_credential("app_secret") or os.getenv("FACEBOOK_APP_SECRET")

        if not all([app_id, app_secret, self.access_token]):
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": app_id,
                        "client_secret": app_secret,
                        "fb_exchange_token": self.access_token,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self.account.credentials["access_token"] = data["access_token"]
                    return True

        except Exception:
            pass

        return False

    async def test_connection(self) -> bool:
        if not self._http_client:
            return False

        try:
            response = await self._http_client.get(
                f"/{self.ad_account_id}",
                params={"fields": "name,account_status"},
            )
            return response.status_code == 200

        except Exception:
            return False

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    async def fetch_data(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch campaign insights."""
        if not self._connected:
            await self.connect()

        response = await self._http_client.get(
            f"/{self.ad_account_id}/insights",
            params={
                "fields": "campaign_id,campaign_name,impressions,clicks,spend,conversions,ctr,cpc,actions",
                "level": "campaign",
                "time_range": f'{{"since":"{start_date.isoformat()}","until":"{end_date.isoformat()}"}}',
            },
        )

        if response.status_code != 200:
            raise Exception(f"Facebook API error: {response.status_code}")

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
            campaigns = []

        # Calculate totals
        total_spend = sum(c.spend for c in campaigns)
        total_impressions = sum(c.impressions for c in campaigns)
        total_clicks = sum(c.clicks for c in campaigns)
        total_conversions = sum(c.conversions for c in campaigns)

        self._update_last_sync()

        return AdsData(
            business_id=self.business_id,
            platform=Platform.FACEBOOK_ADS,
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
            currency="USD",  # Facebook uses USD by default
        )

    def _parse_campaigns(self, raw_data: Dict[str, Any]) -> List[AdsCampaign]:
        """Parse Facebook response into campaigns."""
        campaigns = []

        for row in raw_data.get("data", []):
            # Extract conversions from actions
            conversions = 0
            for action in row.get("actions", []):
                if action.get("action_type") in ["lead", "purchase", "complete_registration"]:
                    conversions += int(action.get("value", 0))

            campaigns.append(AdsCampaign(
                id=row.get("campaign_id", ""),
                name=row.get("campaign_name", "Unknown"),
                status=AdStatus.ACTIVE,  # Would need separate call to get status
                platform=Platform.FACEBOOK_ADS,
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                ctr=float(row.get("ctr", 0)),
                conversions=conversions,
                spend=float(row.get("spend", 0)),
                cpc=float(row.get("cpc", 0)) if row.get("cpc") else 0,
            ))

        return campaigns

    # =========================================================================
    # ACTIONS
    # =========================================================================

    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign."""
        return await self._update_campaign_status(campaign_id, "PAUSED")

    async def resume_campaign(self, campaign_id: str) -> bool:
        """Resume a campaign."""
        return await self._update_campaign_status(campaign_id, "ACTIVE")

    async def _update_campaign_status(self, campaign_id: str, status: str) -> bool:
        """Update campaign status."""
        if not self._connected:
            return False

        try:
            response = await self._http_client.post(
                f"/{campaign_id}",
                data={"status": status},
            )
            return response.status_code == 200

        except Exception:
            return False


# =============================================================================
# FACTORY
# =============================================================================

def create_facebook_ads_account(
    business_id: str,
    ad_account_id: str,
    access_token: str,
) -> MarketingAccount:
    """Create a Facebook Ads account configuration."""
    return MarketingAccount(
        id=f"{business_id}_facebook_ads",
        business_id=business_id,
        platform=Platform.FACEBOOK_ADS,
        account_type=AccountType.OAUTH,
        platform_account_id=ad_account_id,
        platform_name=f"Facebook Ads {ad_account_id}",
        credentials={
            "ad_account_id": ad_account_id,
            "access_token": access_token,
        },
    )
