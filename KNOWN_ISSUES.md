# LeadForge Sprint 1 – Known Issues

## Limitations

1. **Auth is a stub**: JWT auth is minimal. No password reset, no user management UI, no refresh tokens. Suitable for development/demo only.

2. **No real-time updates**: Admin leads list requires manual refresh to see new submissions.

3. **Score always null**: Lead scoring is not implemented in Sprint 1. The `score` column exists but is never populated.

4. **No file uploads**: Funnel fields only support text, select, and tel types.

5. **No rate limiting**: The public lead submission endpoint has no rate limiting. Only honeypot spam protection is implemented.

6. **Single database**: No read replicas or connection pooling beyond asyncpg's built-in pool.

7. **No email notifications**: No alerts when new leads come in.

8. **No funnel builder UI**: Funnels must be created via database/seed script. No admin UI for creating or editing funnels.

9. **Basic phone validation**: Phone validation only checks for minimum 10 digits. No country-specific formatting.

10. **No HTTPS**: Development setup runs on HTTP. Production deployment would need TLS termination.

## Sprint 2 Candidates

- Lead scoring engine
- Funnel builder UI (drag-and-drop)
- Email/SMS notifications
- Webhook integrations
- Advanced analytics dashboard
- Rate limiting + CAPTCHA
- Multi-user org management
- Funnel A/B testing
- Export leads as CSV

## Sprint 2 Known Issues

1. **Server Time for Working Hours**: Working hours use server time, not the funnel's timezone. Timezone support planned for Sprint 3.
2. **Simple Retry Logic**: Call retry uses asyncio.sleep (in-process). Not durable — lost on server restart. Production should use a task queue (Celery/etc).
3. **No Webhook Signature Validation**: Twilio webhooks use a simple shared secret query param rather than Twilio's request signature validation.
4. **Email is Basic**: Uses plain SMTP with text content. No HTML templates or rich formatting.
5. **AI Stub Only**: Without CLAUDE_API_KEY, AI scoring uses a simple deterministic stub. Real AI scoring requires an Anthropic API key.
6. **No SMS Opt-in Tracking**: SMS is sent based on funnel toggle only. No per-lead consent tracking.
7. **Single Call Retry**: Only retries once after 2 minutes. No exponential backoff or configurable retry policy.
8. **No Routing Rule Validation UI**: The routing rules editor does basic validation but doesn't preview rule matches.
