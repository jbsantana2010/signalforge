// INF-02: Sentry client-side init with PII scrubbing.
//
// Install: npm install @sentry/nextjs
// Configure: set NEXT_PUBLIC_SENTRY_DSN in the frontend environment.
// No-op when DSN is unset (local dev stays untouched).

import * as Sentry from "@sentry/nextjs";

const SENSITIVE_KEYS = new Set([
  "phone", "phone_number", "rep_phone", "rep_phone_number",
  "email", "email_address",
  "message", "message_body", "body", "sms_body",
  "password", "pass", "secret",
  "authorization", "auth", "token", "access_token", "refresh_token",
  "jwt", "cookie", "set-cookie",
]);

const PHONE_RE = /\+?\d[\d\-\s().]{7,}\d/g;
const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;

function scrubValue(value: unknown): unknown {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = SENSITIVE_KEYS.has(k.toLowerCase()) ? "[Filtered]" : scrubValue(v);
    }
    return out;
  }
  if (Array.isArray(value)) return value.map(scrubValue);
  if (typeof value === "string") {
    return value.replace(PHONE_RE, "[phone]").replace(EMAIL_RE, "[email]");
  }
  return value;
}

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENV ?? "production",
    release: process.env.NEXT_PUBLIC_WARDER_RELEASE,
    tracesSampleRate: 0.05,
    replaysSessionSampleRate: 0.0,
    replaysOnErrorSampleRate: 0.0,
    sendDefaultPii: false,
    beforeSend(event) {
      try {
        if (event.request) {
          for (const k of ["headers", "cookies", "data", "query_string"] as const) {
            if ((event.request as Record<string, unknown>)[k]) {
              (event.request as Record<string, unknown>)[k] = scrubValue(
                (event.request as Record<string, unknown>)[k],
              );
            }
          }
        }
        if (event.extra)    event.extra    = scrubValue(event.extra)    as typeof event.extra;
        if (event.contexts) event.contexts = scrubValue(event.contexts) as typeof event.contexts;
        if (event.tags)     event.tags     = scrubValue(event.tags)     as typeof event.tags;

        for (const ex of event.exception?.values ?? []) {
          if (typeof ex.value === "string") ex.value = scrubValue(ex.value) as string;
        }
        for (const bc of event.breadcrumbs ?? []) {
          if (bc.message)       bc.message = scrubValue(bc.message) as string;
          if (bc.data)          bc.data    = scrubValue(bc.data) as typeof bc.data;
        }
      } catch {
        // Drop on scrubber failure — never send an unscrubbed event.
        return null;
      }
      return event;
    },
  });
}
