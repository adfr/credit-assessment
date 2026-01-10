"""
News Search Tools for Credit Risk Agent

Uses Serper API to search for news about companies in the portfolio.
Helps analysts stay informed about credit-relevant news events.
"""

import os
import requests
from typing import Optional
from datetime import datetime, timedelta


SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_NEWS_URL = "https://google.serper.dev/news"


def search_company_news(
    company_name: str,
    query_context: Optional[str] = None,
    num_results: int = 5,
    time_period: str = "week"
) -> dict:
    """
    Search for news about a specific company.

    Args:
        company_name: Name of the company to search for
        query_context: Additional context like "bankruptcy", "earnings", "layoffs"
        num_results: Number of results to return (max 10)
        time_period: Time filter - "day", "week", "month", "year"

    Returns:
        dict with news articles and metadata
    """
    if not SERPER_API_KEY:
        return {
            "error": "SERPER_API_KEY not configured",
            "message": "Please set the SERPER_API_KEY environment variable"
        }

    # Build search query
    query = company_name
    if query_context:
        query = f"{company_name} {query_context}"

    # Add credit-relevant terms for better results
    query = f"{query} (financial OR credit OR debt OR earnings OR bankruptcy OR lawsuit OR rating)"

    # Time period mapping
    time_map = {
        "day": "d",
        "week": "w",
        "month": "m",
        "year": "y"
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "num": min(num_results, 10),
        "tbs": f"qdr:{time_map.get(time_period, 'w')}"  # Time-based search
    }

    try:
        response = requests.post(SERPER_NEWS_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Extract and format news articles
        articles = []
        for item in data.get("news", []):
            articles.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", ""),
                "date": item.get("date", ""),
                "link": item.get("link", ""),
            })

        return {
            "company": company_name,
            "query": query,
            "time_period": time_period,
            "article_count": len(articles),
            "articles": articles,
            "searched_at": datetime.now().isoformat(),
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"News search failed: {str(e)}",
            "company": company_name,
        }


def search_industry_news(
    industry: str,
    num_results: int = 5,
    time_period: str = "week"
) -> dict:
    """
    Search for news about a specific industry sector.

    Args:
        industry: Industry sector (e.g., "healthcare", "energy", "technology")
        num_results: Number of results to return
        time_period: Time filter - "day", "week", "month", "year"

    Returns:
        dict with news articles and metadata
    """
    if not SERPER_API_KEY:
        return {
            "error": "SERPER_API_KEY not configured",
            "message": "Please set the SERPER_API_KEY environment variable"
        }

    # Industry-specific search terms
    industry_terms = {
        "healthcare": "healthcare medical pharma hospital",
        "energy": "energy oil gas utilities renewable",
        "technology": "technology software tech startup",
        "financial_services": "banking finance fintech insurance",
        "manufacturing": "manufacturing industrial factory production",
        "retail": "retail consumer shopping ecommerce",
        "construction": "construction real estate building property",
        "transportation": "transportation logistics shipping airline",
    }

    search_terms = industry_terms.get(industry.lower(), industry)
    query = f"{search_terms} (credit risk OR default OR bankruptcy OR downgrade OR financial distress)"

    time_map = {
        "day": "d",
        "week": "w",
        "month": "m",
        "year": "y"
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "num": min(num_results, 10),
        "tbs": f"qdr:{time_map.get(time_period, 'w')}"
    }

    try:
        response = requests.post(SERPER_NEWS_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for item in data.get("news", []):
            articles.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", ""),
                "date": item.get("date", ""),
                "link": item.get("link", ""),
            })

        return {
            "industry": industry,
            "query": query,
            "time_period": time_period,
            "article_count": len(articles),
            "articles": articles,
            "searched_at": datetime.now().isoformat(),
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"News search failed: {str(e)}",
            "industry": industry,
        }


def search_credit_news(
    topic: str = "corporate credit",
    num_results: int = 5,
    time_period: str = "week"
) -> dict:
    """
    Search for general credit market news.

    Args:
        topic: Topic to search (default: "corporate credit")
        num_results: Number of results to return
        time_period: Time filter

    Returns:
        dict with news articles
    """
    if not SERPER_API_KEY:
        return {
            "error": "SERPER_API_KEY not configured",
            "message": "Please set the SERPER_API_KEY environment variable"
        }

    query = f"{topic} (default rates OR credit spreads OR downgrades OR loan losses OR NPL)"

    time_map = {"day": "d", "week": "w", "month": "m", "year": "y"}

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "num": min(num_results, 10),
        "tbs": f"qdr:{time_map.get(time_period, 'w')}"
    }

    try:
        response = requests.post(SERPER_NEWS_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for item in data.get("news", []):
            articles.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", ""),
                "date": item.get("date", ""),
                "link": item.get("link", ""),
            })

        return {
            "topic": topic,
            "article_count": len(articles),
            "articles": articles,
            "searched_at": datetime.now().isoformat(),
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"News search failed: {str(e)}",
            "topic": topic,
        }
