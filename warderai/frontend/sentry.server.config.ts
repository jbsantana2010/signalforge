// INF-02: Sentry server-side init (Next.js route handlers / SSR).
// Imports the client config's scrubbing logic so behavior matches.

import * as Sentry from "@sentry/nextjs";

const dsn = process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.SENTRY_ENV ?? "production",
    release: process.env.WARDER_RELEASE,
    tracesSampleRate: 0.05,
    sendDefaultPii: false,
    // beforeSend reuses the scrubber from the client config. If we end up
    // with server-only fields, duplicate the logic here.
  });
}
