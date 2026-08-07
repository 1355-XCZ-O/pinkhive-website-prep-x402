# Website Prep paid API — first-income candidate

## G5 EVM demand representative

## Salary-disclosure audit

`POST /v1/salary-disclosure-audit` assesses the salary fields in 1-25 supplied
JSON-LD `JobPosting` objects for **$0.01 USDC per successful request**. See
[`examples/salary_audit_request.json`](examples/salary_audit_request.json) for
the customer body. Retrying with an `Idempotency-Key` records just one meter
unit for the same paid identity and route; invalid bodies are not metered.
The explicit offer configuration is in `config/pricing.json` and can be
overridden through `SALARY_AUDIT_PRICE_USD`.

`POST /v1/base-transaction-receipt` is one representative EVM product, priced
at $0.01 USDC. It validates a Base-mainnet transaction hash, makes exactly two
read-only calls (`eth_getTransactionReceipt` and `eth_blockNumber`), and returns
a normalized receipt plus confirmation count. It never signs, sends, or
simulates a transaction. `BASE_RPC_URL` selects the zero-key upstream.

This experiment intentionally adds one endpoint rather than a family of related
products. A 402 challenge is not revenue; only an independent non-project wallet
settlement on Base mainnet passes the demand test.

## G2 distribution fusion

Public discovery repository:
https://github.com/1355-XCZ-O/pinkhive-website-prep-x402

This repository exposes two independent paid units through x402:

- `POST /v1/site-prep` — $0.01 USDC to convert supplied HTML into AI-discovery files.
- `POST /v1/claude-ship-guard` — $0.05 USDC to generate and immediately deliver
  a customized, deterministic Claude Code commit-guard ZIP with SHA-256 receipt.

G3 live audit: the deployed revision currently serves Site Prep, while the Ship
Guard route still returns HTTP 404. Ship Guard is prepared and locally tested,
but is not claimed as a live paid route until the public watcher observes 402.

The Ship Guard generator is public for inspection. Its paid value is hosted
parameter validation, customization, deterministic packaging, hashing, and
automatic delivery—not withholding source code. A runnable free sample is
published under the `ship-guard-sample-v1.0.0` Git tag; the separate full
static G1 product archive is not committed to this public repository.

One billable unit converts up to 20 caller-supplied HTML pages into `llms.txt`,
`llms-full.txt`, and normalized Markdown. The service does not crawl websites;
that keeps delivery deterministic, cheap, and free of model/GPU dependencies.

Current G2 mainnet offer: **$0.01 USDC per successful request** to Base address
`0x8CfB0c37Af0C40f96c44fd45FdEC30b430Bc6A6e`. Only a confirmed independent
mainnet settlement is counted as revenue.

The distribution offer is **$0.05 USDC per customized Ship Guard bundle** to
the same receiver. Both routes issue a payment challenge before product work.

[Deploy the mainnet x402 service on Render](https://render.com/deploy?repo=https://github.com/1355-XCZ-O/pinkhive-website-prep-x402)

That link is the current minimum persistent-hosting gate: Render asks the human
to sign in/authorize the GitHub repository and confirm creation of the free web
service. `render.yaml` already contains the public receiver, facilitator,
network, price, Dockerfile, and health path. No payment credential is required.

## Why this channel was selected

The artifact is channel-neutral, but the selected G2 settlement path is x402 on
Base through the no-key OpenX402 facilitator. Coinbase documents x402 for
per-request API sales, with a facilitator handling verification and settlement.
RapidAPI remains a discovery option, but its provider payout documentation
currently lists a 25% marketplace fee and end-of-following-month payout processing.

Sources checked 2026-08-07:

- https://docs.cdp.coinbase.com/x402/seller/quickstart
- https://docs.cdp.coinbase.com/x402/welcome
- https://x402.computer/
- https://docs.rapidapi.com/docs/payouts-and-finance
- https://render.com/docs/web-services
- https://render.com/docs/free

## Local prepaid-key mode

PowerShell:

```powershell
$env:API_KEYS_JSON='["local-paid-key"]'
$env:METER_DB='usage.sqlite3'
python -m app.server
```

In a second terminal:

```powershell
$env:WEBSITE_PREP_API_KEY='local-paid-key'
python examples/client.py
```

Free endpoints are `GET /health` and `GET /v1/pricing`. A missing/invalid key
cannot invoke the product. Successful calls write one metered unit to SQLite;
failed validation calls are not metered.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Deploy without settlement automation

1. Put this directory in a Git repository.
2. For prepaid mode, create a Blueprint from `render.prepaid.yaml` (or build `Dockerfile`).
3. Set `API_KEYS_JSON` to a JSON list of keys issued only after payment.
4. Verify `/health` reports `paid_route_ready: true`.
5. Give the buyer one key and the request example; inspect `/v1/usage` with it.

Render requires the service to listen on `0.0.0.0` and its assigned `PORT`; the
server does both. Free Render instances can sleep and their local SQLite file is
ephemeral, so use a persistent store before relying on the meter for invoicing.

## Real x402 settlement

`app/x402_server.py` follows Coinbase's current Python seller pattern. The human
external gate is intentionally small but cannot be automated without authority:

1. For the smallest testnet gate, provide a receiving address as `X402_PAY_TO`;
   the default Base Sepolia configuration uses the public test facilitator.
2. Or create a CDP API key and wallet secret, then set `CDP_API_KEY_ID`,
   `CDP_API_KEY_SECRET`, `CDP_WALLET_SECRET` to provision the receiver.
3. Install `requirements-x402.txt`.
4. Test on Base Sepolia (default):
   `python -m uvicorn app.x402_server:app --host 0.0.0.0 --port 8402`.
5. Confirm an unpaid request returns HTTP 402 and complete one test payment.
6. For real revenue set `X402_NETWORK=eip155:8453`. The included deployment uses
   the live-checked OpenX402 public facilitator, so no CDP credential is needed.
   Confirm the receiving address, then deploy the x402 image/start command.

An existing receiving address may instead be supplied with `X402_PAY_TO`.
`Dockerfile.x402` and `render.yaml` are the ready-to-configure mainnet path;
`render.x402.yaml` is retained as an equivalent explicit variant.
`settlement_proof` remains null until an independent explorer/facilitator record
shows a real mainnet payment.

`openapi.yaml` can be imported into an API marketplace if a later generation
decides that marketplace discovery is worth the fee and payout delay.

## Economics

Benchmark the included example with `tests/benchmark.py`. On this local machine,
the G1 result is recorded in `BEE_RESULT.json`; `G2_RESULT.json` records the
mainnet launch attempt. The G2 first-settlement price is $0.01
per successful request. Since conversion is CPU-only and sub-second, hosting,
discovery, payment fees, support, and idle time dominate the marginal compute.

## Current deployment status

The public service has been deployed at
`https://pinkhive-website-prep-x402.onrender.com`. Health returned HTTP 200 on
multiple probes, and an unpaid request to `/v1/site-prep` returned a valid
Base-mainnet HTTP 402 challenge with Bazaar metadata. Monitoring also observed
intermittent Render `404 x-render-routing:no-server` responses, so availability
is not yet stable. This proves deployment and payment gating only; revenue
remains zero until an independent payment settles.
