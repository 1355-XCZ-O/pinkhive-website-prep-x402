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
from .ship_guard import build_ship_guard_bundle

NETWORK = os.environ.get("X402_NETWORK", "eip155:84532")
PRICE = os.environ.get("PRICE_USD", "0.02")
SHIP_GUARD_PRICE = os.environ.get("SHIP_GUARD_PRICE_USD", "0.05")
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
site_discovery = declare_discovery_extension(
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
site_discovery["bazaar"]["info"]["input"]["method"] = "POST"
ship_guard_discovery = declare_discovery_extension(
    input={
        "project_name": "Acme Docs",
        "commit_style": "conventional",
        "secret_presets": ["cloud", "github", "generic"],
        "max_subject_length": 72,
    },
    input_schema={
        "type": "object",
        "properties": {
            "project_name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 80,
                "description": "Project name inserted into the generated local workflow documentation",
            },
            "commit_style": {
                "type": "string",
                "enum": ["descriptive", "conventional"],
                "description": "Commit message validation style",
            },
            "secret_presets": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "uniqueItems": True,
                "items": {"type": "string", "enum": ["cloud", "github", "generic"]},
                "description": "Credential-pattern families included in the generated guard",
            },
            "max_subject_length": {
                "type": "integer",
                "minimum": 50,
                "maximum": 100,
                "description": "Maximum commit subject length",
            },
        },
        "required": ["project_name"],
    },
    body_type="json",
    output=OutputConfig(
        example={
            "product": "Claude Ship Guard — custom bundle",
            "version": "1.0.0-generator.1",
            "filename": "claude-ship-guard-custom.zip",
            "media_type": "application/zip",
            "bytes": 4096,
            "sha256": "64-character SHA-256",
            "files": ["claude-ship-guard/.claude/settings.json"],
            "zip_base64": "base64-encoded customized ZIP",
        },
        schema={
            "type": "object",
            "properties": {
                "product": {"type": "string"},
                "version": {"type": "string"},
                "filename": {"type": "string"},
                "media_type": {"type": "string"},
                "bytes": {"type": "integer"},
                "sha256": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "zip_base64": {"type": "string"},
                "decode": {"type": "string"},
            },
            "required": ["product", "version", "filename", "media_type", "bytes", "sha256", "files", "zip_base64"],
        },
    ),
)
ship_guard_discovery["bazaar"]["info"]["input"]["method"] = "POST"
routes = {
    "POST /v1/site-prep": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price=f"${PRICE}", network=NETWORK)],
        mime_type="application/json",
        description="Convert supplied website HTML into llms.txt and llms-full.txt",
        service_name="PinkHive Website Prep",
        tags=["llms.txt", "html", "markdown", "website", "ai-discovery"],
        extensions=site_discovery,
    ),
    "POST /v1/claude-ship-guard": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price=f"${SHIP_GUARD_PRICE}", network=NETWORK)],
        mime_type="application/json",
        description="Generate and deliver a customized, deterministic Claude Code commit-guard ZIP",
        service_name="PinkHive Claude Ship Guard Generator",
        tags=["claude-code", "developer-tools", "git", "security", "zip", "automation"],
        extensions=ship_guard_discovery,
    ),
}
app = FastAPI(title="PinkHive paid utility API", version="0.2.0")
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
        "ship_guard_price_usd": SHIP_GUARD_PRICE,
        "facilitator": facilitator_config.url,
        "discovery_extension": "bazaar",
    }


@app.get("/")
async def product():
    return {
        "name": "PinkHive paid utility API",
        "description": "Small deterministic products with automatic Base USDC settlement and delivery.",
        "paid_endpoints": [
            {"route": "POST /v1/site-prep", "price_usd": PRICE, "unit": "convert 1-20 supplied HTML pages"},
            {"route": "POST /v1/claude-ship-guard", "price_usd": SHIP_GUARD_PRICE, "unit": "generate one customized guard ZIP"},
        ],
        "health": "/health",
        "docs": "/docs",
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


@app.post("/v1/claude-ship-guard")
async def claude_ship_guard(payload: dict):
    try:
        result = build_ship_guard_bundle(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    input_chars = len(str(payload))
    request_id = meter.record("x402-settled", "/v1/claude-ship-guard", 200, 1, input_chars, result["bytes"])
    result.update({"request_id": request_id, "metered_units": 1})
    return result
