from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

import requests


YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
YAHOO_QUOTE_SUMMARY_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
FMP_V3_BASE_URL = "https://financialmodelingprep.com/api/v3"
FMP_V4_BASE_URL = "https://financialmodelingprep.com/api/v4"
AV_BASE_URL = "https://www.alphavantage.co/query"
DEFAULT_TIMEOUT = 8


@dataclass(frozen=True)
class CompanySearchResult:
    symbol: str
    name: str
    exchange: str = ""
    quote_type: str = ""
    logo_url: str | None = None
    website: str | None = None


@dataclass(frozen=True)
class CompanyProfile:
    symbol: str
    name: str
    exchange: str = ""
    quote_type: str = ""
    website: str | None = None
    logo_url: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    current_price: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    shares_outstanding: float | None = None


@dataclass(frozen=True)
class PeerCompany:
    symbol: str
    name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    price: float | None = None
    ev_revenue: float | None = None
    ev_ebitda: float | None = None
    pe_ratio: float | None = None
    revenue_growth: float | None = None
    ebitda_margin: float | None = None
    logo_url: str | None = None


@dataclass(frozen=True)
class AnalystSnapshot:
    target_high: float | None = None
    target_low: float | None = None
    target_consensus: float | None = None
    target_median: float | None = None
    revenue_estimate_current_year: float | None = None
    revenue_estimate_next_year: float | None = None
    eps_estimate_current_year: float | None = None
    eps_estimate_next_year: float | None = None
    analyst_count: int | None = None


@dataclass(frozen=True)
class EarningsEvent:
    date: str
    eps_estimated: float | None = None
    eps_actual: float | None = None
    revenue_estimated: float | None = None
    revenue_actual: float | None = None
    fiscal_date_ending: str | None = None


@dataclass(frozen=True)
class PrecedentTransaction:
    published_date: str
    title: str
    link: str | None = None


@dataclass(frozen=True)
class ResearchPack:
    peers: list[PeerCompany]
    analyst_snapshot: AnalystSnapshot | None
    earnings_events: list[EarningsEvent]
    precedents: list[PrecedentTransaction]
    provider: str


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            )
        }
    )
    return session


def fmp_api_key() -> str | None:
    return os.getenv("FMP_API_KEY") or os.getenv("FINANCIAL_MODELING_PREP_API_KEY")


def fmp_enabled() -> bool:
    return bool(fmp_api_key())


def alpha_vantage_api_key() -> str | None:
    return os.getenv("ALPHA_VANTAGE_API_KEY")


def _av_search(query: str, limit: int = 8) -> list[CompanySearchResult]:
    """Search via Alpha Vantage SYMBOL_SEARCH endpoint."""
    api_key = alpha_vantage_api_key()
    if not api_key:
        return []
    try:
        response = _session().get(
            AV_BASE_URL,
            params={"function": "SYMBOL_SEARCH", "keywords": query, "apikey": api_key},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for match in data.get("bestMatches", [])[:limit]:
            symbol = match.get("1. symbol", "").upper()
            if not symbol:
                continue
            region = match.get("4. region", "")
            match_type = match.get("3. type", "Equity")
            if match_type not in ("Equity", "ETF"):
                continue
            results.append(
                CompanySearchResult(
                    symbol=symbol,
                    name=match.get("2. name") or symbol,
                    exchange=region,
                    quote_type=match_type,
                    logo_url=_ticker_logo(symbol),
                )
            )
        return results
    except Exception:
        return []


def _logo_from_website(website: str | None) -> str | None:
    if not website:
        return None
    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    domain = parsed.netloc.replace("www.", "")
    if not domain:
        return None
    return f"https://logo.clearbit.com/{domain}"


def _ticker_logo(symbol: str) -> str:
    return f"https://financialmodelingprep.com/image-stock/{symbol.upper()}.png"


def _raw_value(value):
    if isinstance(value, dict):
        return value.get("raw")
    return value


def _fmp_get(base_url: str, path: str, params: dict | None = None):
    api_key = fmp_api_key()
    if not api_key:
        raise RuntimeError("FMP API key not configured.")
    payload = dict(params or {})
    payload["apikey"] = api_key
    response = _session().get(f"{base_url}{path}", params=payload, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def search_companies(query: str, limit: int = 8) -> list[CompanySearchResult]:
    query = query.strip()
    if not query:
        return []

    if fmp_enabled():
        try:
            payload = _fmp_get(
                FMP_V3_BASE_URL,
                "/search",
                {"query": query, "limit": limit, "exchange": "NASDAQ,NYSE,AMEX"},
            )
            results = []
            for item in payload[:limit]:
                symbol = item.get("symbol")
                if not symbol:
                    continue
                results.append(
                    CompanySearchResult(
                        symbol=symbol.upper(),
                        name=item.get("name") or symbol.upper(),
                        exchange=item.get("stockExchange") or item.get("exchangeShortName") or "",
                        quote_type=item.get("type") or "Equity",
                        logo_url=_ticker_logo(symbol),
                    )
                )
            if results:
                return results
        except Exception:
            pass

    # Try Alpha Vantage search (reliable, no FMP key needed)
    av_results = _av_search(query, limit)
    if av_results:
        return av_results

    # Fall back to Yahoo Finance search
    try:
        response = _session().get(
            YAHOO_SEARCH_URL,
            params={"q": query, "quotesCount": limit, "newsCount": 0},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return _fallback_search(query)[:limit]

    results: list[CompanySearchResult] = []
    for quote in payload.get("quotes", []):
        symbol = quote.get("symbol")
        if not symbol:
            continue
        results.append(
            CompanySearchResult(
                symbol=symbol.upper(),
                name=quote.get("shortname") or quote.get("longname") or symbol.upper(),
                exchange=quote.get("exchDisp") or quote.get("exchange") or "",
                quote_type=quote.get("quoteType") or quote.get("typeDisp") or "",
                logo_url=_ticker_logo(symbol),
            )
        )
    return results[:limit]


def _fallback_search(query: str) -> list[CompanySearchResult]:
    normalized = query.upper().replace(".", "-").strip()
    if not normalized or len(normalized) > 7 or not normalized.replace("-", "").isalnum():
        return []
    try:
        profile = resolve_company_profile(normalized, fallback_name=normalized)
        return [
            CompanySearchResult(
                symbol=profile.symbol,
                name=profile.name,
                exchange=profile.exchange,
                quote_type=profile.quote_type,
                logo_url=profile.logo_url or _ticker_logo(profile.symbol),
                website=profile.website,
            )
        ]
    except Exception:
        return [
            CompanySearchResult(
                symbol=normalized,
                name=normalized,
                exchange="Manual ticker entry",
                quote_type="Equity",
                logo_url=_ticker_logo(normalized),
            )
        ]


def resolve_company_profile(symbol: str, fallback_name: str | None = None) -> CompanyProfile:
    if fmp_enabled():
        try:
            profile_payload = _fmp_get(FMP_V3_BASE_URL, f"/profile/{symbol}", {})
            profile = profile_payload[0] if isinstance(profile_payload, list) and profile_payload else {}
            if profile:
                return CompanyProfile(
                    symbol=symbol.upper(),
                    name=profile.get("companyName") or fallback_name or symbol.upper(),
                    exchange=profile.get("exchangeShortName") or profile.get("exchange") or "",
                    quote_type=profile.get("type") or "Equity",
                    website=profile.get("website"),
                    logo_url=profile.get("image") or _logo_from_website(profile.get("website")) or _ticker_logo(symbol),
                    sector=profile.get("sector"),
                    industry=profile.get("industry"),
                    currency=profile.get("currency"),
                    current_price=profile.get("price"),
                    market_cap=profile.get("mktCap"),
                    enterprise_value=profile.get("enterpriseValue"),
                    shares_outstanding=profile.get("sharesOutstanding"),
                )
        except Exception:
            pass

    params = {"modules": "price,assetProfile,defaultKeyStatistics,financialData"}
    response = _session().get(
        YAHOO_QUOTE_SUMMARY_URL.format(symbol=symbol),
        params=params,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    root = response.json().get("quoteSummary", {}).get("result", [{}])[0]
    price = root.get("price", {})
    asset_profile = root.get("assetProfile", {})
    stats = root.get("defaultKeyStatistics", {})
    fin = root.get("financialData", {})
    website = asset_profile.get("website")
    return CompanyProfile(
        symbol=symbol.upper(),
        name=price.get("longName") or price.get("shortName") or fallback_name or symbol.upper(),
        exchange=price.get("exchangeName") or "",
        quote_type=price.get("quoteType") or "",
        website=website,
        logo_url=_logo_from_website(website) or _ticker_logo(symbol),
        sector=asset_profile.get("sector"),
        industry=asset_profile.get("industry"),
        currency=price.get("currency"),
        current_price=_raw_value(price.get("regularMarketPrice")),
        market_cap=_raw_value(price.get("marketCap")),
        enterprise_value=_raw_value(fin.get("enterpriseValue")),
        shares_outstanding=_raw_value(stats.get("sharesOutstanding")),
    )


def build_research_pack(symbol: str, profile: CompanyProfile | None = None) -> ResearchPack | None:
    if not fmp_enabled():
        return None

    peers = _fetch_peer_companies(symbol)
    analyst_snapshot = _fetch_analyst_snapshot(symbol)
    earnings = _fetch_earnings_events(symbol)
    precedents = _fetch_precedent_transactions(profile.industry if profile else None, profile.sector if profile else None)
    return ResearchPack(
        peers=peers,
        analyst_snapshot=analyst_snapshot,
        earnings_events=earnings,
        precedents=precedents,
        provider="Financial Modeling Prep",
    )


def _fetch_peer_companies(symbol: str, limit: int = 8) -> list[PeerCompany]:
    peer_payload = _fmp_get(FMP_V4_BASE_URL, "/stock_peers", {"symbol": symbol})
    peer_symbols = []
    if isinstance(peer_payload, list) and peer_payload:
        peer_symbols = [s for s in peer_payload[0].get("peersList", []) if s and s.upper() != symbol.upper()]
    peers: list[PeerCompany] = []
    for peer_symbol in peer_symbols[:limit]:
        try:
            profile_payload = _fmp_get(FMP_V3_BASE_URL, f"/profile/{peer_symbol}", {})
            ratios_payload = _fmp_get(FMP_V3_BASE_URL, f"/ratios-ttm/{peer_symbol}", {})
            growth_payload = _fmp_get(FMP_V3_BASE_URL, f"/key-metrics-ttm/{peer_symbol}", {})
        except Exception:
            continue

        profile = profile_payload[0] if profile_payload else {}
        ratios = ratios_payload[0] if ratios_payload else {}
        growth = growth_payload[0] if growth_payload else {}
        peers.append(
            PeerCompany(
                symbol=peer_symbol.upper(),
                name=profile.get("companyName") or peer_symbol.upper(),
                sector=profile.get("sector"),
                industry=profile.get("industry"),
                market_cap=profile.get("mktCap"),
                enterprise_value=profile.get("enterpriseValue"),
                price=profile.get("price"),
                ev_revenue=ratios.get("enterpriseValueOverRevenueTTM"),
                ev_ebitda=ratios.get("enterpriseValueOverEBITDATTM"),
                pe_ratio=ratios.get("peRatioTTM"),
                revenue_growth=growth.get("revenuePerShareTTM"),
                ebitda_margin=ratios.get("ebitdaMarginTTM"),
                logo_url=profile.get("image") or _ticker_logo(peer_symbol),
            )
        )
    return peers


def _fetch_analyst_snapshot(symbol: str) -> AnalystSnapshot | None:
    try:
        target_payload = _fmp_get(FMP_V4_BASE_URL, "/price-target-consensus", {"symbol": symbol})
        estimate_payload = _fmp_get(FMP_V3_BASE_URL, f"/analyst-estimates/{symbol}", {"limit": 2})
    except Exception:
        return None

    target = target_payload[0] if target_payload else {}
    current = estimate_payload[0] if estimate_payload else {}
    next_year = estimate_payload[1] if len(estimate_payload) > 1 else {}
    return AnalystSnapshot(
        target_high=target.get("targetHigh"),
        target_low=target.get("targetLow"),
        target_consensus=target.get("targetConsensus"),
        target_median=target.get("targetMedian"),
        analyst_count=target.get("analystCount"),
        revenue_estimate_current_year=current.get("estimatedRevenueAvg"),
        revenue_estimate_next_year=next_year.get("estimatedRevenueAvg"),
        eps_estimate_current_year=current.get("estimatedEpsAvg"),
        eps_estimate_next_year=next_year.get("estimatedEpsAvg"),
    )


def _fetch_earnings_events(symbol: str, limit: int = 6) -> list[EarningsEvent]:
    try:
        payload = _fmp_get(FMP_V3_BASE_URL, f"/historical/earning_calendar/{symbol}", {"limit": limit})
    except Exception:
        return []
    events = []
    for item in payload[:limit]:
        events.append(
            EarningsEvent(
                date=item.get("date") or "",
                eps_estimated=item.get("epsEstimated"),
                eps_actual=item.get("eps"),
                revenue_estimated=item.get("revenueEstimated"),
                revenue_actual=item.get("revenue"),
                fiscal_date_ending=item.get("fiscalDateEnding"),
            )
        )
    return events


def _fetch_precedent_transactions(industry: str | None, sector: str | None, limit: int = 8) -> list[PrecedentTransaction]:
    keyword = (industry or sector or "").lower()
    try:
        payload = _fmp_get(FMP_V4_BASE_URL, "/mergers-acquisitions-rss-feed", {"page": 0})
    except Exception:
        return []
    precedents = []
    for item in payload:
        title = item.get("title") or ""
        if keyword and keyword not in title.lower():
            continue
        precedents.append(
            PrecedentTransaction(
                published_date=item.get("publishedDate") or item.get("date") or "",
                title=title,
                link=item.get("link"),
            )
        )
        if len(precedents) >= limit:
            break
    return precedents
