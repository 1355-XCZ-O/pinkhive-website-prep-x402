# Salary audit deployment outbox

Prepared change: `POST /v1/salary-disclosure-audit`, priced at `$0.01` USDC per
successful request, with `Idempotency-Key` metering. The local stdlib/prepaid
suite passes, including a billable request and duplicate-key meter assertion.

Do not push this revision yet. The local runtime lacks the production x402
packages (`cdp-sdk` and `x402`), so `python -c "import app.x402_server"` cannot
exercise the payment middleware. The current Render health probe also returned
HTTP 503 (`Render - Application loading`) at 2026-08-07T11:28:38Z.

Once a runtime with `requirements-x402.txt` installed has imported and tested
the x402 app, and public `/health` is stable, stage the files below and run:

```powershell
git add README.md Dockerfile.x402 render.yaml openapi.yaml config/pricing.json app tests examples DEPLOYMENT_OUTBOX.md
git commit -m "feat: add paid salary disclosure auditor"
git push origin main
```

Then use the public HTTP observer to retain a `/health` receipt and an unpaid
`POST /v1/salary-disclosure-audit` x402 challenge receipt. Neither challenge is
a payment receipt.
