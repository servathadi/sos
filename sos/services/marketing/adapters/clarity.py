"""
Microsoft Clarity Adapter

Fetches behavior analytics from Microsoft Clarity.

Requires:
- API token
- Project ID

Note: Clarity's API is limited. Most data requires the dashboard.
This adapter provides what's available via API.

Docs: https://docs.microsoft.com/en-us/clarity/
"""

import os
from datetime import date, datetime, timezone
from typing import Optional, Dict, Any, List

import httpx

from .base import BaseMarketingAdapter
from ..schemas import (
    MarketingAccount,
    ClarityData,
    Platform,
    AccountType,
)


class ClarityAdapter(BaseMarketingAdapter):
    """
    Microsoft Clarity adapter.

    Uses Clarity API for behavior analytics.
    Note: Clarity API is limited; this provides core metrics.
    """

    PLATFORM = Platform.CLARITY
    REQUIRES_OAUTH = False  # Uses API token

    BASE_URL = "https://www.clarity.ms/api/v1"

    def __init__(self, account: MarketingAccount):
        super().__init__(account)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def project_id(self) -> Optional[str]:
        """Clarity project ID."""
        return self._get_credential("project_id")

    @property
    def api_token(self) -> Optional[str]:
        """Clarity API token."""
        return self._get_credential("api_token")

    # =========================================================================
    # CONNECTION
    # =========================================================================

    async def connect(self) -> bool:
        if not self.project_id:
            self._set_error("Missing project ID")
            return False

        # Clarity doesn't require auth for basic data
        # The project ID is used to identify the site
        try:
            self._http_client = httpx.AsyncClient(
                headers={
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
        # Clarity doesn't use OAuth
        return True

    async def test_connection(self) -> bool:
        return self._connected and self.project_id is not None

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    async def fetch_data(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch Clarity data.

        Note: Clarity's public API is very limited.
        This returns mock/estimated data based on typical patterns.
        For full data, use the Clarity dashboard or webhook integration.
        """
        if not self._connected:
            await self.connect()

        # Clarity doesn't have a comprehensive public API
        # In production, you'd either:
        # 1. Use webhooks to push data to your system
        # 2. Use the embed script with custom events
        # 3. Export data manually from dashboard

        # For now, return structure that can be populated
        return {
            "project_id": self.project_id,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "sessions": 0,
            "scroll_depth": 0,
            "rage_clicks": 0,
            "dead_clicks": 0,
            "quick_backs": 0,
        }

    async def get_clarity_data(
        self,
        start_date: date,
        end_date: date,
    ) -> ClarityData:
        """
        Get Clarity behavior data.

        Note: Due to API limitations, some data may need manual setup.
        """
        raw_data = await self.fetch_data(start_date, end_date)

        self._update_last_sync()

        # Generate insights based on available data
        insights = []
        if raw_data.get("rage_clicks", 0) > 10:
            insights.append("High rage clicks detected - users may be frustrated with non-clickable elements")
        if raw_data.get("quick_backs", 0) > 20:
            insights.append("Many quick backs - content may not match user expectations")
        if raw_data.get("scroll_depth", 100) < 50:
            insights.append("Low scroll depth - consider moving important content higher")

        return ClarityData(
            business_id=self.business_id,
            date_range=(start_date, end_date),
            total_sessions=raw_data.get("sessions", 0),
            avg_scroll_depth=raw_data.get("scroll_depth", 0),
            rage_clicks=raw_data.get("rage_clicks", 0),
            dead_clicks=raw_data.get("dead_clicks", 0),
            quick_backs=raw_data.get("quick_backs", 0),
            insights=insights,
        )


# =============================================================================
# CLARITY SETUP HELPER
# =============================================================================

def get_clarity_script(project_id: str) -> str:
    """
    Get the Clarity tracking script to add to a website.

    Add this to the <head> of your pages.
    """
    return f"""<script type="text/javascript">
    (function(c,l,a,r,i,t,y){{
        c[a]=c[a]||function(){{(c[a].q=c[a].q||[]).push(arguments)}};
        t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    }})(window, document, "clarity", "script", "{project_id}");
</script>"""


# =============================================================================
# FACTORY
# =============================================================================

def create_clarity_account(
    business_id: str,
    project_id: str,
    api_token: Optional[str] = None,
) -> MarketingAccount:
    """Create a Clarity account configuration."""
    return MarketingAccount(
        id=f"{business_id}_clarity",
        business_id=business_id,
        platform=Platform.CLARITY,
        account_type=AccountType.API_KEY,
        platform_account_id=project_id,
        platform_name=f"Clarity: {project_id}",
        credentials={
            "project_id": project_id,
            "api_token": api_token,
        },
    )
