"""FastAPI application exposing Razorpay Test Mode order connectivity."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from app.config import ConfigurationError, Settings
from app.models import NormalizedOrder, OpportunitiesResponse, OrdersResponse
from app.opportunities import detect_opportunities
from app.razorpay import (
    RazorpayAPIError,
    RazorpayAuthenticationError,
    RazorpayClient,
    RazorpayError,
    RazorpayNetworkError,
)

app = FastAPI(title="FinGraph", version="0.1.0")


def _fetch_razorpay_orders(*, count: int, skip: int) -> list[NormalizedOrder]:
    """Fetch normalized Razorpay Test Mode orders with safe upstream failures."""
    client = None
    try:
        settings = Settings.from_environment()
        client = RazorpayClient(settings)
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        return client.list_orders(count=count, skip=skip)
    except RazorpayAuthenticationError as exc:
        raise HTTPException(status_code=502, detail="Razorpay Test Mode authentication failed.") from exc
    except RazorpayNetworkError as exc:
        raise HTTPException(status_code=503, detail="Razorpay Test Mode is unavailable.") from exc
    except RazorpayAPIError as exc:
        raise HTTPException(status_code=502, detail="Razorpay Test Mode returned an API error.") from exc
    except RazorpayError as exc:
        raise HTTPException(status_code=502, detail="Razorpay Test Mode returned an invalid response.") from exc
    finally:
        if client is not None:
            client.close()


@app.get("/api/razorpay/orders", response_model=OrdersResponse)
def get_razorpay_orders(
    count: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> OrdersResponse:
    """Fetch normalized orders from the configured Razorpay Test Mode account."""
    orders = _fetch_razorpay_orders(count=count, skip=skip)
    return OrdersResponse(count=len(orders), orders=orders)


@app.get("/api/opportunities", response_model=OpportunitiesResponse)
def get_opportunities(
    count: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> OpportunitiesResponse:
    """Derive deterministic order-level opportunities from Razorpay Test Mode data."""
    orders = _fetch_razorpay_orders(count=count, skip=skip)
    opportunities = detect_opportunities(orders)
    return OpportunitiesResponse(count=len(opportunities), opportunities=opportunities)
