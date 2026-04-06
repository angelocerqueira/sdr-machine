# LP Preview Page — Design Spec

## Summary

Create a dedicated full-screen landing page preview at `/lp/[id]` with Desktop/Mobile toggle. The mobile view shows the LP inside an iPhone frame mockup. Add "Ver LP" buttons to the existing lead-sheet and lead-detail components.

## Route

`/lp/[id]` — where `id` is the lead ID.

## Layout

This page does NOT use the default app layout (no sidebar). It's a standalone full-screen view.

### Header Bar

- Dark background (`bg-surface` / `#111`)
- Left: back button (← arrow, navigates to previous page or `/kanban`)
- Center: lead name
- Right: toggle group with Desktop and Mobile buttons (icons + text)

### Desktop Mode

- iframe at 100% width, fills remaining viewport height below header
- `src` points to `GET /api/leads/{id}/lp` (existing backend endpoint)

### Mobile Mode

- Dark background (`bg-bg`) behind the device frame
- iPhone-style frame centered on screen:
  - Rounded corners (border-radius ~40px)
  - Top notch/dynamic island
  - Bottom home indicator bar
  - Inner iframe at 375px width, ~812px height (iPhone viewport)
- Frame is CSS-only (no images)

## Existing Changes

### lead-sheet.tsx

Add a "Ver LP" button below the existing LP iframe preview. Opens `/lp/[leadId]` in a new tab. Only visible when `lead.lp_html` exists.

### lead-detail.tsx

Add a "Ver LP em tela cheia" button/link above or beside the existing iframe. Opens `/lp/[leadId]` in a new tab. Only visible when `lead.lp_html` exists.

## New Files

- `src/app/lp/[id]/page.tsx` — the preview page
- `src/components/lp-preview.tsx` — the preview component (header + iframe + device frame)

## Data Fetching

The page only needs the lead name for the header. Fetch via `getLead(id)` from `lib/api.ts`. The iframe src uses `getLeadLpUrl(id)` (already exists).

## No Backend Changes

The existing `GET /api/leads/{id}/lp` endpoint already serves raw HTML. No new endpoints needed.
