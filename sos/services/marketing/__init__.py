"""
SOS Marketing Toolkit

Modular marketing integrations for any SOS-powered project.

Supports:
- Google Analytics 4 (GA4)
- Google Ads
- Facebook/Meta Ads
- Google Search Console
- Microsoft Clarity
- Custom landing pages

Usage:
    from sos.services.marketing import MarketingClient

    client = MarketingClient(business_id="smile_dental")
    await client.connect_google(credentials)

    # Get unified dashboard
    dashboard = await client.get_dashboard()

    # Get insights
    insights = await client.analyze()
"""

from .schemas import (
    MarketingAccount,
    AnalyticsData,
    AdsData,
    AdsCampaign,
    SearchConsoleData,
    ClarityData,
    MarketingDashboard,
    MarketingInsight,
    AccountType,
    Platform,
)

from .client import MarketingClient, get_marketing_client

from .adapters.base import BaseMarketingAdapter

__version__ = "1.0.0"

__all__ = [
    # Client
    "MarketingClient",
    "get_marketing_client",
    # Schemas
    "MarketingAccount",
    "AnalyticsData",
    "AdsData",
    "AdsCampaign",
    "SearchConsoleData",
    "ClarityData",
    "MarketingDashboard",
    "MarketingInsight",
    "AccountType",
    "Platform",
    # Base
    "BaseMarketingAdapter",
]
