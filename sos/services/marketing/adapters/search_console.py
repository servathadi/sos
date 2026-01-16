"""
Google Search Console Adapter

Fetches SEO data from Google Search Console.

Requires:
- OAuth credentials with webmasters.readonly scope
- Site URL (property)

Docs: https://developers.google.com/webmaster-tools/v1/api_reference_index
"""

import os
from datetime import date, datetime, timezone
from typing import Optional, Dict, Any, List

import httpx

from .base import BaseMarketingAdapter
from ..schemas import (
    MarketingAccount,
    SearchConsoleData,
    SearchQuery,
    Platform,
    AccountType,
)


class SearchConsoleAdapter(BaseMarketingAdapter):
    """
    Google Search Console adapter.

    Uses the Search Console API for SEO data.
    """

    PLATFORM = Platform.SEARCH_CONSOLE
    REQUIRES_OAUTH = True
    SCOPES = [
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]

    BASE_URL = "https://searchconsole.googleapis.com/webmasters/v3"

    def __init__(self, account: MarketingAccount):
        super().__init__(account)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def site_url(self) -> Optional[str]:
        """Site URL (e.g., 'https://example.com' or 'sc-domain:example.com')."""
        return self._get_credential("site_url")

    @property
    def access_token(self) -> Optional[str]:
        return self._get_credential("access_token")

    # =========================================================================
    # CONNECTION
    # =========================================================================

    async def connect(self) -> bool:
        if not self.access_token or not self.site_url:
            self._set_error("Missing access token or site URL")
            return False

        try:
            self._http_client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.access_token}",
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

        except Exception:
            pass

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
        """Fetch search analytics data."""
        if not self._connected:
            await self.connect()

        # URL encode the site URL
        import urllib.parse
        encoded_site = urllib.parse.quote(self.site_url, safe="")

        response = await self._http_client.post(
            f"{self.BASE_URL}/sites/{encoded_site}/searchAnalytics/query",
            json={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": ["query"],
                "rowLimit": 100,
            },
        )

        if response.status_code != 200:
            raise Exception(f"Search Console API error: {response.status_code}")

        return response.json()

    async def get_search_data(
        self,
        start_date: date,
        end_date: date,
        include_comparison: bool = True,
    ) -> SearchConsoleData:
        """Get formatted search console data."""
        try:
            raw_data = await self.fetch_data(start_date, end_date)
        except Exception:
            raw_data = {"rows": []}

        # Parse queries
        top_queries = []
        total_clicks = 0
        total_impressions = 0

        for row in raw_data.get("rows", []):
            query = SearchQuery(
                query=row.get("keys", [""])[0],
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=float(row.get("ctr", 0)) * 100,
                position=float(row.get("position", 0)),
            )
            top_queries.append(query)
            total_clicks += query.clicks
            total_impressions += query.impressions

        # Get top pages
        top_pages = await self._get_top_pages(start_date, end_date)

        # Calculate comparison
        comparison = {}
        if include_comparison:
            prev_start, prev_end = self.get_previous_period(start_date, end_date)
            try:
                prev_data = await self.fetch_data(prev_start, prev_end)
                prev_clicks = sum(r.get("clicks", 0) for r in prev_data.get("rows", []))
                prev_impressions = sum(r.get("impressions", 0) for r in prev_data.get("rows", []))
                comparison = {"clicks": prev_clicks, "impressions": prev_impressions}
            except Exception:
                pass

        self._update_last_sync()

        return SearchConsoleData(
            business_id=self.business_id,
            date_range=(start_date, end_date),
            total_clicks=total_clicks,
            total_impressions=total_impressions,
            avg_ctr=(total_clicks / total_impressions * 100) if total_impressions else 0,
            avg_position=sum(q.position for q in top_queries) / len(top_queries) if top_queries else 0,
            top_queries=top_queries[:20],
            top_pages=top_pages,
            clicks_change=self.calculate_change(
                total_clicks, comparison.get("clicks", 0)
            ) if comparison else 0,
            impressions_change=self.calculate_change(
                total_impressions, comparison.get("impressions", 0)
            ) if comparison else 0,
        )

    async def _get_top_pages(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get top pages by clicks."""
        if not self._http_client:
            return []

        try:
            import urllib.parse
            encoded_site = urllib.parse.quote(self.site_url, safe="")

            response = await self._http_client.post(
                f"{self.BASE_URL}/sites/{encoded_site}/searchAnalytics/query",
                json={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "dimensions": ["page"],
                    "rowLimit": 20,
                },
            )

            if response.status_code != 200:
                return []

            data = response.json()
            pages = []

            for row in data.get("rows", []):
                pages.append({
                    "url": row.get("keys", [""])[0],
                    "clicks": int(row.get("clicks", 0)),
                    "impressions": int(row.get("impressions", 0)),
                    "ctr": float(row.get("ctr", 0)) * 100,
                    "position": float(row.get("position", 0)),
                })

            return pages

        except Exception:
            return []


# =============================================================================
# FACTORY
# =============================================================================

def create_search_console_account(
    business_id: str,
    site_url: str,
    access_token: str,
    refresh_token: Optional[str] = None,
) -> MarketingAccount:
    """Create a Search Console account configuration."""
    return MarketingAccount(
        id=f"{business_id}_search_console",
        business_id=business_id,
        platform=Platform.SEARCH_CONSOLE,
        account_type=AccountType.OAUTH,
        platform_account_id=site_url,
        platform_name=f"Search Console: {site_url}",
        credentials={
            "site_url": site_url,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )
