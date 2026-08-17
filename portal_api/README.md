# Job Portal Backend

One Vercel Python (Flask) app, `app.py`, backing the portal at
`docs/index.html` (served free via GitHub Pages). It's a single app — not
one file per route — because Vercel's Python framework detection requires
exactly one Flask entrypoint per project once `flask` is in
`requirements.txt`; splitting routes into separate files under `api/` makes
Vercel unable to pick a default entrypoint.

- `POST /api/status` — updates a job's status (New/Shortlisted/Applied/
  Interview/Rejected) by committing `docs/status.json` back to the repo via
  the GitHub API.
- `POST /api/generate_cv` — looks up a job from `docs/jobs.json`, calls the
  Claude API to decide how to tailor the CV (which bullets, in what order,
  tailored summary — never inventing facts, see the system prompt in the
  file), builds the PDF with reportlab, and streams it back for download.

**Cost note:** `generate_cv.py` calls the Claude API on every click — that's
real, ongoing per-use billing on your Anthropic account, unlike the free job
-search APIs the digest bot itself uses.

## One-time setup

### 1. Enable GitHub Pages

Repo → **Settings → Pages** → Source: **Deploy from a branch** → Branch:
`main`, folder: `/docs` → Save. Your portal will be live at
`https://<you>.github.io/<repo-name>/` within a minute or two.

### 2. Create a GitHub personal access token

The backend needs write access to commit `docs/status.json` (and read access
to `docs/jobs.json`).

1. github.com → Settings → Developer settings → Personal access tokens →
   **Fine-grained tokens** → Generate new token.
2. Repository access: only this repo (`job-digest-bot`).
3. Permissions: **Contents: Read and write**.
4. Copy the token — you won't see it again.

### 3. Get an Anthropic API key

1. Sign up / log in at https://console.anthropic.com
2. Create an API key. **Add billing** — this key is billed per request,
   separate from any Claude subscription you have elsewhere.

### 4. Deploy to Vercel

1. Sign up free at https://vercel.com (GitHub login is easiest).
2. **New Project** → import the `job-digest-bot` repo.
3. When it asks for the root directory, set it to `portal_api`.
4. Framework preset: **Other** (it auto-detects the Python functions under `api/`).
5. Before the first deploy, add these **Environment Variables** (Project →
   Settings → Environment Variables):

   | Name | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | from step 3 |
   | `GITHUB_TOKEN` | from step 2 |
   | `GITHUB_REPO` | `<your-username>/job-digest-bot` |
   | `GITHUB_BRANCH` | `main` |
   | `MASTER_CV_JSON` | the full contents of `master_cv_for_portal.json` (saved to your Desktop\CV folder) as one line — see note below |
   | `ALLOWED_ORIGIN` | `https://<you>.github.io` (your GitHub Pages origin — tightens CORS instead of allowing any site) |

   **`MASTER_CV_JSON` note:** paste the *entire JSON file contents* as the
   env var value (Vercel accepts multi-line values in its UI, so you can
   paste it formatted). This is deliberately **not** committed to the repo —
   the repo is public, and this file has your name/phone/email in it.

6. Deploy.

### 5. Point the portal at your deployed backend

Edit `docs/config.js`:

```js
const API_BASE_URL = "https://job-digest-portal.vercel.app"; // your actual Vercel URL, no trailing slash
```

Commit and push. Reload the portal — the "Generate CV" and status-change
buttons should now work.

## Local testing

You can test `generate_cv.py`'s PDF-building logic (`build_pdf()`) without
any of the above — it's a pure function of `(master_cv dict, tailored dict)`
with no network calls. See the digest bot's own testing notes for the
pattern; the Claude call and GitHub commit logic do need real credentials
and are easiest to verify by deploying to Vercel and clicking the buttons
for real.

## Known limitations

- `docs/status.json` is committed via the GitHub Contents API on every status
  change — fine for personal, low-frequency use; would need a real database
  if this were multi-user or high-frequency.
- If the daily digest bot workflow and a portal status-update happen to race
  (extremely unlikely — the workflow runs at a fixed early-morning UTC time),
  the workflow's `git pull --rebase` before pushing handles the ordinary case.
- No auth on the API endpoints — anyone with the Vercel URL could call them.
  Fine for a personal tool with an obscure URL; add a shared-secret header
  check in `_shared.py` if you want to harden this.
