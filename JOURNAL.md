# Unit 7 - Issue selection

**Issue link:** https://github.com/codepath/pathreview-ai201-fa26-howard/issues/40

**Issue title:** Add a "Copy link" button to share a public review summary

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Why this issue (tier fit and scope):**

I chose Tier 2 because it matches my experience. I have built and shipped multi-module projects, including a monorepo clinic management platform and an Electron, React and TypeScript desktop app, so I am comfortable working across a front end and the backend behind it. I read the tier definitions before choosing. Tier 1 covers fixes contained in one or two files, and this issue goes beyond that: it touches the review page UI (`frontend/src/pages/ReviewPage.tsx`), the frontend service layer (`frontend/src/services/shareService.ts`), and the API routes (`api/routes/reviews.py`), and the three must work together to create, store, and serve a share link. Tier 3 covers full-system, infrastructure, or AI pipeline changes, and this issue does not touch those. The estimated effort is 5 to 8 hours, which fits the time available to me. The main risks are enforcing the 30-day expiration correctly and serving a read-only view without login while still exposing only the intended review summary. I plan to handle them by validating the link token and its expiry on the server for every request and by testing both an active and an expired link locally.

**Problem summary:**

- **What the issue is:** Users can view their review summary, but they cannot share it with someone else. The issue asks for a way to generate a shareable link that opens a read-only view of the summary, so a person can send their results to others without giving them access to the account.
- **What is currently missing:** There is no share feature. The app has no control for generating a link, no service call to request one, and no API route that serves a review summary to someone who is not logged in. The only way to show a summary to another person today is to give them access to the account.
- **What a successful fix accomplishes:** A user can generate a share link from the review page and copy it. Anyone with the link can open a read-only view of that review summary without logging in. The link stops working after 30 days, and the person opening it sees that it has expired.

**Branch name:** feature/40-copy-link-button

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

## Unit 8 — Reproduction & solution planning

**Reproduction commit link:** [link to commit documenting the reproduced issue]

**Reproduction summary:**
[1–2 sentences: How did you reproduce the issue? What did you observe?]

**PLAN.md link:** [link to PLAN.md in your fork]

**Blockers or open questions:**
[Anything you're still uncertain about going into Unit 9, or leave blank]