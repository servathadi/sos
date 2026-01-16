"""
Base Marketing Adapter

Abstract base class for all marketing platform adapters.
Ensures consistent interface across platforms.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Optional, Dict, Any, List

from ..schemas import (
    MarketingAccount,
    AnalyticsData,
    AdsData,
    SearchConsoleData,
    ClarityData,
    Platform,
    AccountType,
)


class BaseMarketingAdapter(ABC):
    """
    Abstract base class for marketing adapters.

    All platform-specific adapters inherit from this.
    """

    # Override in subclass
    PLATFORM: Platform = Platform.CUSTOM
    REQUIRES_OAUTH: bool = True
    SCOPES: List[str] = []

    def __init__(self, account: MarketingAccount):
        self.account = account
        self._connected = False
        self._client: Any = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def business_id(self) -> str:
        return self.account.business_id

    # =========================================================================
    # CONNECTION
    # =========================================================================

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the platform using stored credentials.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        pass

    @abstractmethod
    async def refresh_credentials(self) -> bool:
        """
        Refresh OAuth tokens if needed.

        Returns:
            True if refresh successful
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the connection is still valid.

        Returns:
            True if connection is valid
        """
        pass

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    @abstractmethod
    async def fetch_data(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch data for a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            **kwargs: Platform-specific options

        Returns:
            Raw data from the platform
        """
        pass

    # =========================================================================
    # ACTIONS (Optional - Override if platform supports)
    # =========================================================================

    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pause an ad campaign."""
        raise NotImplementedError(f"{self.PLATFORM.value} doesn't support pausing campaigns")

    async def resume_campaign(self, campaign_id: str) -> bool:
        """Resume a paused campaign."""
        raise NotImplementedError(f"{self.PLATFORM.value} doesn't support resuming campaigns")

    async def set_budget(self, campaign_id: str, daily_budget: float) -> bool:
        """Set campaign daily budget."""
        raise NotImplementedError(f"{self.PLATFORM.value} doesn't support setting budgets")

    async def set_bid(self, campaign_id: str, bid: float) -> bool:
        """Set campaign bid."""
        raise NotImplementedError(f"{self.PLATFORM.value} doesn't support setting bids")

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_credential(self, key: str, default: Any = None) -> Any:
        """Get a credential value."""
        return self.account.credentials.get(key, default)

    def _update_last_sync(self) -> None:
        """Update the last sync timestamp."""
        self.account.last_sync = datetime.now(timezone.utc)

    def _set_error(self, error: str) -> None:
        """Set error message on account."""
        self.account.error = error
        self.account.connected = False

    def _clear_error(self) -> None:
        """Clear error message."""
        self.account.error = None
        self.account.connected = True

    @staticmethod
    def get_date_range_days(start_date: date, end_date: date) -> int:
        """Get number of days in range."""
        return (end_date - start_date).days + 1

    @staticmethod
    def get_previous_period(start_date: date, end_date: date) -> tuple[date, date]:
        """Get the previous period of same length for comparison."""
        days = (end_date - start_date).days + 1
        prev_end = start_date - __import__('datetime').timedelta(days=1)
        prev_start = prev_end - __import__('datetime').timedelta(days=days - 1)
        return (prev_start, prev_end)

    @staticmethod
    def calculate_change(current: float, previous: float) -> float:
        """Calculate percentage change."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100


class MockAdapter(BaseMarketingAdapter):
    """
    Mock adapter for testing.

    Returns fake data without connecting to any platform.
    """

    PLATFORM = Platform.CUSTOM
    REQUIRES_OAUTH = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def refresh_credentials(self) -> bool:
        return True

    async def test_connection(self) -> bool:
        return self._connected

    async def fetch_data(
        self,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """Return mock data."""
        import random

        return {
            "sessions": random.randint(100, 1000),
            "users": random.randint(80, 800),
            "pageviews": random.randint(200, 2000),
            "bounce_rate": random.uniform(0.3, 0.7),
            "avg_session_duration": random.uniform(60, 300),
        }
