"""
Google Analytics 4 (GA4) Adapter

Fetches analytics data from Google Analytics 4 via the Data API.

Requires:
- OAuth credentials with analytics.readonly scope
- GA4 property ID

Docs: https://developers.google.com/analytics/devguides/reporting/data/v1
"""

import os
from datetime import date
from typing import Optional, Dict, Any, List

import httpx

from .base import BaseMarketingAdapter
from ..schemas import (
    MarketingAccount,
    AnalyticsData,
    Platform,
    AccountType,
)


class GoogleAnalyticsAdapter(BaseMarketingAdapter):
    """
    Google Analytics 4 adapter.

    Uses the GA4 Data API to fetch analytics data.
    """

    PLATFORM = Platform.GOOGLE_ANALYTICS
    REQUIRES_OAUTH = True
    SCOPES = [
        "https://www.googleapis.com/auth/analytics.readonly",
    ]

    # API endpoints
    BASE_URL = "https://analyticsdata.googleapis.com/v1beta"

    def __init__(self, account: MarketingAccount):
        super().__init__(account)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def property_id(self) -> Optional[str]:
        """GA4 property ID (e.g., 'properties/123456789')."""
        prop_id = self._get_credential("property_id")
        if prop_id and not prop_id.startswith("properties/"):
            return f"properties/{prop_id}"
        return prop_id

    @property
    def access_token(self) -> Optional[str]:
        """OAuth access token."""
        return self._get_credential("access_token")

    # =========================================================================
    # CONNECTION
    # =========================================================================

    async def connect(self) -> bool:
        """Connect using OAuth credentials."""
        if not self.access_token:
            self._set_error("No access token configured")
            return False

        if not self.property_id:
            self._set_error("No GA4 property ID configured")
            return False

        try:
            self._http_client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            # Test connection
            if await self.test_connection():
                self._connected = True
                self._clear_error()
                return True
            else:
                return False

        except Exception as e:
            self._set_error(f"Connection failed: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    async def refresh_credentials(self) -> bool:
        """
        Refresh the OAuth access token.

        Requires refresh_token in credentials.
        """
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
                    if "refresh_token" in data:
                        self.account.credentials["refresh_token"] = data["refresh_token"]
                    return True
                else:
                    self._set_error(f"Token refresh failed: {response.status_code}")
                    return False

        except Exception as e:
            self._set_error(f"Token refresh error: {str(e)}")
            return False

    async def test_connection(self) -> bool:
        """Test connection by fetching metadata."""
        if not self._http_client:
            return False

        try:
            # Use runReport with minimal data to test
            response = await self._http_client.post(
                f"{self.BASE_URL}/{self.property_id}:runReport",
                json={
                    "dateRanges": [{"startDate": "yesterday", "endDate": "yesterday"}],
                    "metrics": [{"name": "sessions"}],
                    "limit": 1,
                },
            )

            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                # Try refresh
                if await self.refresh_credentials():
                    return await self.test_connection()
                return False
            else:
                self._set_error(f"API error: {response.status_code}")
                return False

        except Exception as e:
            self._set_error(f"Connection test failed: {str(e)}")
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
        """Fetch raw analytics data."""
        if not self._connected or not self._http_client:
            await self.connect()

        response = await self._http_client.post(
            f"{self.BASE_URL}/{self.property_id}:runReport",
            json={
                "dateRanges": [
                    {
                        "startDate": start_date.isoformat(),
                        "endDate": end_date.isoformat(),
                    }
                ],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "totalUsers"},
                    {"name": "newUsers"},
                    {"name": "screenPageViews"},
                    {"name": "averageSessionDuration"},
                    {"name": "bounceRate"},
                    {"name": "screenPageViewsPerSession"},
                    {"name": "conversions"},
                ],
                "dimensions": [],
            },
        )

        if response.status_code != 200:
            raise Exception(f"GA4 API error: {response.status_code} - {response.text}")

        return response.json()

    async def get_analytics_data(
        self,
        start_date: date,
        end_date: date,
        include_comparison: bool = True,
    ) -> AnalyticsData:
        """
        Get formatted analytics data.

        Args:
            start_date: Start of date range
            end_date: End of date range
            include_comparison: Include comparison to previous period

        Returns:
            AnalyticsData object
        """
        # Fetch current period
        raw_data = await self.fetch_data(start_date, end_date)
        data = self._parse_report(raw_data)

        # Fetch previous period for comparison
        comparison = {}
        if include_comparison:
            prev_start, prev_end = self.get_previous_period(start_date, end_date)
            try:
                prev_raw = await self.fetch_data(prev_start, prev_end)
                comparison = self._parse_report(prev_raw)
            except Exception:
                pass

        # Get traffic sources
        traffic_sources = await self._get_traffic_sources(start_date, end_date)

        # Get top pages
        top_pages = await self._get_top_pages(start_date, end_date)

        self._update_last_sync()

        return AnalyticsData(
            business_id=self.business_id,
            date_range=(start_date, end_date),
            sessions=data.get("sessions", 0),
            users=data.get("totalUsers", 0),
            new_users=data.get("newUsers", 0),
            pageviews=data.get("screenPageViews", 0),
            avg_session_duration=data.get("averageSessionDuration", 0),
            bounce_rate=data.get("bounceRate", 0),
            pages_per_session=data.get("screenPageViewsPerSession", 0),
            conversions=data.get("conversions", 0),
            conversion_rate=self._calc_conversion_rate(data),
            traffic_sources=traffic_sources,
            top_pages=top_pages,
            sessions_change=self.calculate_change(
                data.get("sessions", 0),
                comparison.get("sessions", 0)
            ) if comparison else 0,
            users_change=self.calculate_change(
                data.get("totalUsers", 0),
                comparison.get("totalUsers", 0)
            ) if comparison else 0,
            conversions_change=self.calculate_change(
                data.get("conversions", 0),
                comparison.get("conversions", 0)
            ) if comparison else 0,
            platform=Platform.GOOGLE_ANALYTICS,
        )

    async def _get_traffic_sources(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, int]:
        """Get traffic by source."""
        if not self._http_client:
            return {}

        try:
            response = await self._http_client.post(
                f"{self.BASE_URL}/{self.property_id}:runReport",
                json={
                    "dateRanges": [
                        {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}
                    ],
                    "metrics": [{"name": "sessions"}],
                    "dimensions": [{"name": "sessionSource"}],
                    "limit": 10,
                },
            )

            if response.status_code != 200:
                return {}

            data = response.json()
            sources = {}

            for row in data.get("rows", []):
                source = row.get("dimensionValues", [{}])[0].get("value", "unknown")
                sessions = int(row.get("metricValues", [{}])[0].get("value", 0))
                sources[source] = sessions

            return sources

        except Exception:
            return {}

    async def _get_top_pages(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get top pages by views."""
        if not self._http_client:
            return []

        try:
            response = await self._http_client.post(
                f"{self.BASE_URL}/{self.property_id}:runReport",
                json={
                    "dateRanges": [
                        {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}
                    ],
                    "metrics": [{"name": "screenPageViews"}],
                    "dimensions": [{"name": "pagePath"}],
                    "limit": 10,
                    "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}],
                },
            )

            if response.status_code != 200:
                return []

            data = response.json()
            pages = []

            for row in data.get("rows", []):
                path = row.get("dimensionValues", [{}])[0].get("value", "/")
                views = int(row.get("metricValues", [{}])[0].get("value", 0))
                pages.append({"path": path, "views": views})

            return pages

        except Exception:
            return []

    def _parse_report(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse GA4 report response into simple dict."""
        result = {}
        rows = raw_data.get("rows", [])

        if not rows:
            return result

        metric_headers = raw_data.get("metricHeaders", [])
        metric_values = rows[0].get("metricValues", [])

        for i, header in enumerate(metric_headers):
            name = header.get("name", "")
            value = metric_values[i].get("value", "0") if i < len(metric_values) else "0"

            # Convert to appropriate type
            try:
                if "." in value:
                    result[name] = float(value)
                else:
                    result[name] = int(value)
            except ValueError:
                result[name] = value

        return result

    def _calc_conversion_rate(self, data: Dict[str, Any]) -> float:
        """Calculate conversion rate."""
        sessions = data.get("sessions", 0)
        conversions = data.get("conversions", 0)
        if sessions == 0:
            return 0.0
        return (conversions / sessions) * 100


# =============================================================================
# FACTORY
# =============================================================================

def create_ga4_account(
    business_id: str,
    property_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
) -> MarketingAccount:
    """
    Create a Google Analytics account configuration.

    Args:
        business_id: ID of the business
        property_id: GA4 property ID (numbers only, e.g., "123456789")
        access_token: OAuth access token
        refresh_token: OAuth refresh token (for auto-renewal)

    Returns:
        MarketingAccount configured for GA4
    """
    return MarketingAccount(
        id=f"{business_id}_ga4",
        business_id=business_id,
        platform=Platform.GOOGLE_ANALYTICS,
        account_type=AccountType.OAUTH,
        platform_account_id=property_id,
        platform_name=f"GA4 Property {property_id}",
        credentials={
            "property_id": property_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )
