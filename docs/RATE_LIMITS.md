# API request limits

The backend applies these one-minute budgets by default:

| Budget | Requests | Environment variable |
| --- | --- | --- |
| Login per IP, including malformed requests | 5 | `RATE_LIMIT_LOGIN_PER_MINUTE` |
| Requests without Authorization per IP | 30 | `RATE_LIMIT_ANON_PER_MINUTE` |
| All API requests per IP, including invalid tokens | 120 | `RATE_LIMIT_IP_PER_MINUTE` |
| Authenticated requests per user across IPs | 120 | `RATE_LIMIT_USER_PER_MINUTE` |
| Multipart writes per authenticated user | 10 | `RATE_LIMIT_UPLOAD_PER_MINUTE` |

Exceeded budgets return JSON with HTTP 429 and `Retry-After` in seconds. CSV
exports are assembled in the browser from paginated list requests; each page
counts against the general budgets. Multipart writes include forms without files.
People sharing a public IP share the IP budgets.

## Activate shared counters on Render

Create a Render Key Value service in the same region as the backend. Put its
internal Redis connection URL into the backend's Render environment variable
`RATE_LIMIT_REDIS_URL`, then redeploy. Keep this URL out of GitHub and frontend
environment variables. External providers can use a TLS `rediss://` URL.

With Redis configured, increment and expiry are atomic in one Lua operation,
and workers share counters. Redis outages return 503 with a short retry delay
instead of silently disabling limits. Without a Redis URL, a locked local-memory
cache provides per-process limits only, reset on restart. This fallback is not
a shared production limit. A fixed window starts on the first request and lasts
60 seconds; requests may burst around window boundaries.

Render documents that its edge sets the first `X-Forwarded-For` address to the
client IP. The backend trusts that header only when Render supplies its hostname
(or `RATE_LIMIT_TRUST_RENDER_PROXY=True` is explicitly configured). Leave this
false for directly exposed servers without a trusted proxy. Vercel forwarding
may group clients under proxy IPs; use Vercel's edge rules to limit visitors
before forwarding. Per-user limits do not depend on proxy IPs.

## Edge protection

These limits run inside Django and also apply to direct Render API requests.
They do not prevent traffic from reaching the application or replace provider
DDoS protection. Configure Vercel firewall rules for `/api/`, particularly
`/api/v1/auth/login`, in the Vercel dashboard. No firewall rules or paid services
are provisioned by this code change. Keep Render's provider protection enabled.

## Verification

Run `python manage.py test common.test_rate_limits accounts common --settings=ps_backend.test_settings`.
Tests use an isolated SQLite database and in-memory counters, not Supabase.
