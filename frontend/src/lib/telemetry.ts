type Props = Record<string, string | number | boolean | null | undefined>;

/**
 * Telemetry wrapper. Currently a no-op; will route to PostHog in a future
 * task. The function signature is final, so call sites are stable.
 */
export function track(event: string, props?: Props): void {
  if (typeof window === "undefined") return;
  // Stub: no-op for now. Future: posthog?.capture(event, props)
  // Keep a console.debug behind a flag to help local debugging without
  // polluting production console.
  if (process.env.NODE_ENV === "development") {
    console.debug(`[telemetry] ${event}`, props ?? {});
  }
}
