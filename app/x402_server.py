"""Optional real x402 settlement adapter following Coinbase's Python seller flow."""
import asyncio
import os

from cdp import CdpClient
from cdp.x402 import create_facilitator_config
from fastapi import FastAPI, HTTPException
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer
from x402.extensions.bazaar import OutputConfig, bazaar_resource_server_extension, declare_discovery_extension

from .core import build_site_bundle
from .metering import Meter

NETWORK = os.environ.get("X402_NETWORK", "eip155:84532")
PRICE = os.environ.get("PRICE_USD", "0.02")
DEFAULT_PAY_TO = "0x8CfB0c37Af0C40f96c44fd45FdEC30b430Bc6A6e"


async def resolve_pay_to() -> str:
    explicit = os.environ.get("X402_PAY_TO", DEFAULT_PAY_TO)
    if explicit:
        return explicit
    async with CdpClient() as cdp:
        account = await cdp.evm.get_or_create_account(name="pinkhive-website-prep-receiver")
        return account.address


PAY_TO = asyncio.run(resolve_pay_to())
facilitator_url = os.environ.get("X402_FACILITATOR_URL")
if facilitator_url:
    facilitator_config = FacilitatorConfig(url=facilitator_url)
elif NETWORK == "eip155:84532" and not os.environ.get("CDP_API_KEY_ID"):
    facilitator_config = FacilitatorConfig(url="https://x402.org/facilitator")
elif NETWORK == "eip155:8453" and not os.environ.get("CDP_API_KEY_ID"):
    facilitator_config = FacilitatorConfig(url="https://facilitator.openx402.ai")
else:
    facilitator_config = create_facilitator_config()
resource_server = x402ResourceServer(HTTPFacilitatorClient(facilitator_config))
resource_server.register(NETWORK, ExactEvmServerScheme())
resource_server.register_extension(bazaar_resource_server_extension)
discovery = declare_discovery_extension(
    input={
        "site_name": "Example Docs",
        "site_summary": "Documentation prepared for AI-agent discovery.",
        "pages": [{"url": "https://example.com/guide", "html": "<h1>Guide</h1><p>Start here.</p>"}],
    },
    input_schema={
        "type": "object",
        "properties": {
            "site_name": {"type": "string", "minLength": 1},
            "site_summary": {"type": "string", "minLength": 1},
            "pages": {
                "type": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {"url": {"type": "string", "format": "uri"}, "html": {"type": "string", "minLength": 1}},
                    "required": ["url", "html"],
                },
            },
        },
        "required": ["site_name", "site_summary", "pages"],
    },
    body_type="json",
    output=OutputConfig(
        example={"request_id": "uuid", "metered_units": 1, "llms_txt": "# Example Docs", "llms_full_txt": "# Example Docs"},
        schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "metered_units": {"type": "integer"},
                "llms_txt": {"type": "string"},
                "llms_full_txt": {"type": "string"},
            },
            "required": ["request_id", "metered_units", "llms_txt", "llms_full_txt"],
        },
    ),
)
# The route adapter enriches this too, but setting it before middleware
# validation avoids a false "method required" warning in x402 2.18.0.
discovery["bazaar"]["info"]["input"]["method"] = "POST"
routes = {
    "POST /v1/site-prep": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price=f"${PRICE}", network=NETWORK)],
        mime_type="application/json",
        description="Convert supplied website HTML into llms.txt and llms-full.txt",
        service_name="PinkHive Website Prep",
        tags=["llms.txt", "html", "markdown", "website", "ai-discovery"],
        extensions=discovery,
    )
}
app = FastAPI(title="Website Prep paid API", version="0.1.0")
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=resource_server)
meter = Meter()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "payment": "x402",
        "network": NETWORK,
        "pay_to": PAY_TO,
        "price_usd": PRICE,
        "facilitator": facilitator_config.url,
        "discovery_extension": "bazaar",
    }


@app.get("/")
async def product():
    return {
        "name": "PinkHive Website Prep",
        "description": "Convert supplied HTML pages into llms.txt, llms-full.txt, and normalized Markdown.",
        "paid_endpoint": "POST /v1/site-prep",
        "health": "/health",
        "price_usd": PRICE,
        "network": NETWORK,
        "pay_to": PAY_TO,
    }


@app.post("/v1/site-prep")
async def site_prep(payload: dict):
    try:
        result = build_site_bundle(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    request_id = meter.record("x402-settled", "/v1/site-prep", 200, 1, result["unit"]["input_html_chars"], 0)
    result.update({"request_id": request_id, "metered_units": 1})
    return result
