# Website Prep paid API — first-income candidate

One billable unit converts up to 20 caller-supplied HTML pages into `llms.txt`,
`llms-full.txt`, and normalized Markdown. The service does not crawl websites;
that keeps delivery deterministic, cheap, and free of model/GPU dependencies.

Current G2 mainnet offer: **$0.01 USDC per successful request** to Base address
`0x8CfB0c37Af0C40f96c44fd45FdEC30b430Bc6A6e`. Only a confirmed independent
mainnet settlement is counted as revenue.

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
2. In Render, create a Blueprint from `render.yaml` (or build `Dockerfile`).
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
`Dockerfile.x402` and `render.x402.yaml` are the ready-to-configure hosted path.
`settlement_proof` remains null until an independent explorer/facilitator record
shows a real mainnet payment.

`openapi.yaml` can be imported into an API marketplace if a later generation
decides that marketplace discovery is worth the fee and payout delay.

## Economics

Benchmark the included example with `tests/benchmark.py`. On this local machine,
the actual result is recorded in `BEE_RESULT.json`. The initial price is $0.02
per successful request. Since conversion is CPU-only and sub-second, hosting,
discovery, payment fees, support, and idle time dominate the marginal compute.
