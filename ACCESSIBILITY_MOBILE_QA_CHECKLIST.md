# Accessibility and Mobile-First QA Checklist

Last updated: 2026-03-25

Use this checklist for every portal workflow before release.

## Scope

Applies to:
- forms
- tables and list cards
- action buttons
- keyboard navigation
- responsive layouts in `apps/web/app/(portal)/**`

## 1. Forms

- [ ] Every input has a visible label.
- [ ] Label is programmatically associated to the input.
- [ ] Required fields are indicated in text, not color only.
- [ ] Error messages are clear, actionable, and announced via `aria-live`.
- [ ] Success/info messages are announced via `aria-live`.
- [ ] Input focus order is logical in desktop and mobile layouts.
- [ ] Input targets are at least 44x44 CSS px on mobile.
- [ ] Number/date fields support keyboard-only entry.
- [ ] Validation does not trap focus or reset user-entered data unexpectedly.

## 2. Tables and Dense Data Cards

- [ ] Data regions have a clear heading.
- [ ] List/table containers expose semantic roles (`table`, `list`, `listitem`) as appropriate.
- [ ] Rows/cards remain readable at 320px viewport width.
- [ ] Horizontal overflow has an intentional strategy (wrap, stacked cards, or scroll with hint).
- [ ] Status badges include text labels and are not color-only.
- [ ] Empty states explain what to do next.
- [ ] Loading states and skeletons are keyboard-safe.

## 3. Action Buttons and Critical Controls

- [ ] Every icon-only action includes an accessible name.
- [ ] Destructive actions have confirmation or undo path.
- [ ] Disabled buttons include a visible reason nearby when blocked.
- [ ] Critical actions expose busy state (`aria-busy` and text change).
- [ ] Button groups wrap correctly on narrow mobile widths.
- [ ] Touch spacing prevents accidental taps.

## 4. Keyboard Navigation

- [ ] Entire page is operable with keyboard only.
- [ ] Focus indicator is visible on all interactive elements.
- [ ] No keyboard trap in dialogs, dropdowns, timelines, or toasts.
- [ ] Enter and Space both work where expected.
- [ ] Escape closes dismissible overlays/panels.
- [ ] Tabbing order follows visual order.

## 5. Mobile-First Layout and Responsiveness

- [ ] Core workflows are usable at 320px, 375px, and 768px widths.
- [ ] Primary actions remain visible without horizontal scrolling.
- [ ] Long strings (IDs, timestamps, emails) wrap safely.
- [ ] Bottom-fixed toasts/panels do not hide primary CTAs.
- [ ] Safe area insets are respected on modern mobile devices.
- [ ] Realtime updates do not cause scroll jumps.

## 6. Realtime and Async UX

- [ ] Optimistic updates clearly reconcile with server truth.
- [ ] WebSocket disconnect state is visible and recoverable.
- [ ] Duplicate realtime events are deduplicated in UI.
- [ ] Event timelines preserve chronological ordering after reconciliation.
- [ ] Pending items have clear state (`queued`, `sending`, `confirmed`, `failed`).

## 7. Verification Protocol

- [ ] Manual keyboard pass completed.
- [ ] Screen-reader spot check completed on at least one portal workflow.
- [ ] Browser responsive emulator pass completed.
- [ ] Unit/E2E coverage updated for critical regressions.
- [ ] Findings documented in release notes or QA log.
