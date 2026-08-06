# Public experiment log

This repository is a PinkHive first-income experiment. The objective is to see
whether an autonomous worker can turn an inherited, tested transformation into
a real machine-purchasable service while keeping every economic claim auditable.

## G1 — delivery unit

- Reused an HTML-to-Markdown converter and llms.txt generator.
- Defined one bounded unit: a successful request with 1-20 caller-supplied HTML pages.
- Added prepaid-key entitlement, health/pricing endpoints, SQLite metering,
  OpenAPI, Docker/Render configs, and customer examples.
- Local service tests: 5/5 passing.
- 100-run conversion benchmark: median approximately 0.5 ms for the example.
- Revenue: $0. No public deployment or settlement existed.

## G2 — mainnet and discovery mutation

- Public receiver: `0x8CfB0c37Af0C40f96c44fd45FdEC30b430Bc6A6e`.
- Reduced introductory price from $0.02 to $0.01 to optimize for the first
  independently settled unit.
- Live-checked the `/supported` endpoints of OpenX402 and xpay; both advertised
  x402 v2 exact settlement on Base mainnet without an API key.
- Selected `https://facilitator.openx402.ai` because its live response also
  advertised the discovery extension. The facilitator is replaceable by env var.
- Added Bazaar input/output metadata. A locally hosted mainnet middleware smoke
  test returned HTTP 402, advertised 10,000 atomic USDC ($0.01), the expected
  Base USDC asset, the public receiver, and a POST Bazaar declaration.
- No private key was accessed, no payment was signed, and no on-chain transaction
  was initiated by the seller.
- Published the complete experiment at
  `https://github.com/1355-XCZ-O/pinkhive-website-prep-x402`.
- Attempted one bounded Cloudflare Quick Tunnel. The local mainnet service was
  healthy, but the tunnel returned no auditable public URL in the allotted
  window. Both owned processes were stopped; this is recorded as environmental
  failure rather than a deployment or revenue success.
- Prepared a Render Blueprint link as the minimum durable-hosting gate. It needs
  a human Render sign-in/OAuth confirmation but no payment secret.
- The human confirmed the Blueprint. Monitoring observed the expected Render
  hostname transition from `404 no-server` to two consecutive healthy `200`
  responses at `https://pinkhive-website-prep-x402.onrender.com/health`.
- An unpaid public POST returned HTTP 402 with `PAYMENT-REQUIRED`: exact scheme,
  Base mainnet, Base USDC, amount 10,000 atomic units ($0.01), the configured
  receiver, and Bazaar POST metadata. This proves gating, not income.

## Revenue accounting rule

Repository stars, test calls, testnet assets, self-payments, and simulated usage
all count as zero revenue. Only an independently observable Base-mainnet
settlement transferring USDC to the receiver counts as income.

## Known constraints

- A free temporary tunnel is not durable hosting.
- Discovery registration is facilitator-specific and may require a real paid
  call before an endpoint is cataloged.
- Local SQLite metering is ephemeral on free hosts. The Base settlement is the
  authoritative revenue proof until persistent operational storage is added.
- Public facilitators are external dependencies and should be continuously
  monitored or replaced if their observed behavior changes.
