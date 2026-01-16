"""
Marketing Adapters

Platform-specific adapters for marketing integrations.
"""

from .base import BaseMarketingAdapter
from .google_analytics import GoogleAnalyticsAdapter
from .google_ads import GoogleAdsAdapter
from .facebook_ads import FacebookAdsAdapter
from .search_console import SearchConsoleAdapter
from .clarity import ClarityAdapter

__all__ = [
    "BaseMarketingAdapter",
    "GoogleAnalyticsAdapter",
    "GoogleAdsAdapter",
    "FacebookAdsAdapter",
    "SearchConsoleAdapter",
    "ClarityAdapter",
]
