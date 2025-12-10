# WalletService — Backend README

Aim
Build a backend wallet service that allows users to deposit via Paystack, view/manage wallet balances, inspect transaction history, and transfer funds between users. All wallet actions must be accessible via Google JWT authentication or API keys (for services).

Objectives
- Understand basic wallet system mechanics.
- Implement Paystack deposits into a user wallet.
- Allow users to view balance and transaction history.
- Enable wallet-to-wallet transfers.
- Support authentication via Google JWT and API keys.
- Enforce API key permissions, limits (max 5 active), expiry, revocation, and rollover.
- Mandatory Paystack webhook handling to finalize deposits.

Scope
In-Scope
- Google sign-in to generate/validate JWT tokens.
- Wallet creation per user.
- Wallet deposits using Paystack (init + webhook).
- Wallet balance, transaction history, and transaction status.
- Wallet-to-wallet transfers.
- API key system for service-to-service access with permissions and limits.
- API key expiry, revocation, and rollover support.
- Paystack webhook handling (mandatory).

Out of Scope
- Frontend/UI.
- Manual bank transfers or other payment providers.
- Advanced fraud detection.

High-Level Architecture
- API server exposing REST endpoints (or GraphQL).
- Persistent DB (Postgres recommended) with transactions to maintain balances.
- Authentication middleware:
  - JWT validator (Google ID tokens)
  - API key middleware (service-to-service)
- Paystack integration module for init and verify.
- Webhook endpoint to receive Paystack events (signature-verified, idempotent).
- Background job queue (optional) for asynchronous tasks (email, webhook retries).
- Optional metrics & monitoring.

Core Data Models (example fields)
- User { id, email, name, created_at }
- Wallet { id, user_id, balance_cents, currency, created_at, updated_at }
- Transaction { id, wallet_id, type: [deposit, transfer_in, transfer_out], amount_cents, currency, status: [pending, success, failed], reference, meta JSON, created_at, related_wallet_id }
- ApiKey { id, user_id, key_hash, permissions[], expires_at, revoked_at, created_at }
- WebhookLog { id, provider, event, payload, signature, processed_at, status, error }

Design notes
- Store money in integer minor units (cents/kobo).
- Use DB transactions and SELECT ... FOR UPDATE to avoid race conditions on balance updates.
- Enforce idempotency for Paystack webhook (use reference + event id).
- Keep API keys hashed in DB; compare using constant-time methods.
- Limit max 5 active (not revoked and not expired) API keys per user.

Authentication & Authorization
- Google JWT:
  - Verify Google ID token (via Google public keys or SDK).
  - Map token to local user record; create user/wallet on first sign-in.
- API Keys:
  - API keys created by authenticated users.
  - Each key has permissions (e.g., deposit:init, deposit:webhook, wallet:read, transfer:create).
  - Keys expire; can be revoked; max 5 active keys per user.
  - Auth middleware checks either valid JWT or valid API key and required permission.

Permissions (example)
- wallet:read — view balance & transactions
- wallet:transfer — initiate transfers
- deposit:init — initialize Paystack transactions
- deposit:webhook — accept webhook events (services that need to post events)

API Endpoints (REST examples)
- POST /auth/google — accept Google ID token, return JWT for app access
- GET /wallet — GET current user's wallet balance (JWT or API key with wallet:read)
- GET /wallet/transactions?limit=&cursor= — transaction history (wallet:read)
- POST /wallet/deposit/init — init Paystack transaction (deposit:init)
  - Body: { amount_cents, currency, callback_url?, metadata? }
  - Response: { payment_url, reference }
- POST /webhooks/paystack — Paystack webhook receiver (no JWT; verify signature; permission deposit:webhook for APIkey access if used)
- POST /wallet/transfer — transfer to another user's wallet (wallet:transfer)
  - Body: { to_user_id_or_email, amount_cents, currency, idempotency_key? }
- GET /keys — list user's API keys
- POST /keys — create new API key with permissions & expiry
- POST /keys/:id/revoke — revoke API key
- POST /keys/:id/rollover — generate new key with same permissions, expire old one

Paystack Integration
- Initialization:
  - Server calls Paystack initialize API with amount & metadata, stores reference & status=pending, returns payment link to caller.
- Webhook:
  - Mandatory endpoint to receive Paystack notifications.
  - Verify Paystack signature (use PAYSTACK_SECRET_KEY to validate header signature).
  - Idempotent processing: check if transaction reference already processed.
  - On successful payment event:
    - Mark transaction as success.
    - Increment wallet balance in an atomic DB transaction.
    - Record a Transaction row for deposit and update statuses.
- Manual verify:
  - Support a fallback endpoint to call Paystack verify endpoint using stored reference to recheck status.

Webhook Security & Idempotency
- Verify signature using Paystack secret and headers.
- Use idempotency key: mark WebhookLog processed; ignore duplicates.
- Lock or transactionally update wallet balances to avoid double-crediting.
- Log raw payloads for audits.

API Key Lifecycle
- Creation:
  - User requests new key with permissions and expiry.
  - System ensures user has <5 active keys.
  - Return plaintext key once; store only hash.
- Active keys:
  - Active = not revoked && expires_at > now.
- Revocation:
  - Mark revoked_at; key immediately invalid.
- Rollover:
  - Create new key with same permissions + expiry; revoke old key.
  - Use transactional operation to ensure count limit preserved.

Rate Limiting & Limits
- Apply per-user and per-key rate limits (e.g., 60 req/min).
- Throttle heavy endpoints like transfer and deposit:init.
- Limit maximum transfer per call (configurable) and daily limits if required.

Error Handling & Retries
- Use HTTP standard codes: 400 (bad request), 401 (unauth), 403 (forbidden), 404, 429, 500.
- Return structured error payloads { code, message, details? }.
- For transient failures (Paystack API down), retry with backoff; ensure idempotency.

Database Migrations
- Provide SQL migrations to create tables above, with indices:
  - Unique index on transaction.reference
  - Index on wallet.user_id
  - Index on api_key.user_id + revoked_at + expires_at
- Use a migration tool (e.g., Flyway, Knex, Alembic).

Environment Variables
- NODE_ENV (production|development)
- PORT
- DATABASE_URL (Postgres connection)
- JWT_PUBLIC_KEYS / GOOGLE_CLIENT_ID (for Google token validation)
- JWT_SIGNING_SECRET (for app JWTs if issuing)
- PAYSTACK_SECRET_KEY
- PAYSTACK_PUBLIC_KEY (optional)
- API_KEY_HASH_SALT / pepper (for hashing keys)
- RATE_LIMIT_CONFIG
- OPTIONAL: SENTRY_DSN, METRICS_ENDPOINT

Setup (local)
1. Clone repo.
2. Copy .env.example → .env and set values.
3. Run DB migrations.
4. npm install && npm run dev
5. Create a test user via Google sign-in flow or seed script.
6. Create API key if service access needed.

Testing
- Unit tests for:
  - Auth middleware (JWT + API key)
  - Wallet balance atomic updates
  - Transfer validations (sufficient funds, recipient exists)
  - Webhook idempotency and signature verification
- Integration tests:
  - Full deposit flow: init -> Paystack simulate webhook -> confirm wallet balance
  - API key create/list/revoke/rollover and limit enforcement.

Example curl flows
- Initialize deposit (user JWT)
  curl -X POST https://api.example.com/wallet/deposit/init \
    -H "Authorization: Bearer <JWT>" \
    -H "Content-Type: application/json" \
    -d '{"amount_cents":10000,"currency":"NGN"}'

- Paystack webhook (server-side; Paystack calls this endpoint)
  POST /webhooks/paystack
  - Verify X-Paystack-Signature (HMAC-SHA512 with PAYSTACK_SECRET_KEY)

- Transfer between users
  curl -X POST https://api.example.com/wallet/transfer \
    -H "Authorization: Bearer <JWT or APIKEY>" \
    -H "Content-Type: application/json" \
    -d '{"to_user_email":"bob@example.com","amount_cents":5000,"idempotency_key":"tx-abc-123"}'

Operational notes
- Monitor webhook delivery failures and implement retry/backoff.
- Keep Paystack secret and API keys in secret manager.
- Consider job queue for heavy reconciliation tasks.
- Implement admin endpoints for dispute resolution & manual adjustments (restricted).

Security checklist
- Verify Google tokens correctly and cache public keys per Google OIDC suggestions.
- Hash API keys, never log plaintext keys.
- Validate all inputs and enforce currency/amount limits.
- Enforce TLS for all endpoints.
- Log audit trails for money movement.

Deliverables
- API server implementing endpoints above.
- Migrations and models.
- Tests covering critical flows.
- Documentation (this README) and example requests.

Notes
- This README is an implementation guide; adapt details (naming, exact routes, RPC vs REST) to your stack.
- Paystack specifics: consult Paystack docs for initialize, verify endpoints and webhook signature header names.

License & credits
- Choose a project license (MIT recommended) and add at repo root.

