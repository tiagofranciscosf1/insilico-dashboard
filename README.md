# Insilico Medicine (HKEX 03696) — always-on live dashboard

A self-updating web dashboard (catalysts, news, lock-ups, share structure, holder
sell-likelihood, direction call). It runs **24/7 in the cloud, independent of your
computer**, using GitHub Actions (scheduler) + GitHub Pages (public URL). The refresh
job calls the Anthropic API with web search to gather news and re-assess direction.

## What's in here
- `index.html` — the live dashboard (served by GitHub Pages). Regenerated each run.
- `template.html` — the page shell; `__DATA_JSON__` is replaced with fresh data.
- `data.json` — last-good data (seed + state for change-flagging).
- `update_dashboard.py` — the refresh job (Claude + web search → new data → render).
- `.github/workflows/update.yml` — cloud cron: twice daily + manual "Run workflow".
- `requirements.txt` — Python deps.

## One-time setup (~10 minutes)

1. **Create a GitHub account** (free) if you don't have one: https://github.com/join

2. **Create a new repository and upload these files.**

   First create the repo: top-right **+** → **New repository**. Name it
   `insilico-dashboard`, set visibility to **Public** (free GitHub Pages needs Public
   unless you have a paid plan), tick **Add a README** so the repo isn't empty, then
   **Create repository**.

   The tricky part is the `.github/workflows/update.yml` file — it lives in nested
   folders, and GitHub's drag-and-drop uploader **cannot create folders**. Pick ONE of
   the three methods below.

   ### Method A — Web browser only (no software to install) — recommended for non-coders
   Do it in two passes:

   1. **Upload the five flat files.** On the repo's **Code** tab: **Add file → Upload
      files**. Drag in `index.html`, `template.html`, `data.json`,
      `update_dashboard.py`, and `requirements.txt` (NOT the `.github` folder). Scroll
      down, click **Commit changes**.
   2. **Create the workflow file by typing its path.** **Add file → Create new file.**
      In the filename box at the top, type exactly:

      ```
      .github/workflows/update.yml
      ```

      As you type each `/`, GitHub turns the segment into a folder automatically — so
      `.github/`, then `workflows/`, then the file name. Now open `update.yml` from this
      folder on your computer, copy ALL of its contents, paste into the big editor box,
      and click **Commit changes**.

   When done, your repo's file tree should look exactly like this:

   ```
   insilico-dashboard/
   ├─ index.html
   ├─ template.html
   ├─ data.json
   ├─ update_dashboard.py
   ├─ requirements.txt
   └─ .github/
      └─ workflows/
         └─ update.yml
   ```

   (The `README.md` from repo creation can stay; it's harmless.)

   ### Method B — GitHub Desktop (easiest if you'll tweak files later)
   1. Install **GitHub Desktop** (https://desktop.github.com), sign in.
   2. **File → New repository** (or **Clone** the one you made in step 2), pick a local
      folder.
   3. Copy ALL files from THIS folder — including the whole `.github` folder — into that
      local repo folder (Finder/Explorer). The folder structure is preserved as-is.
   4. In GitHub Desktop you'll see the changes listed. Type a summary like `initial`,
      click **Commit to main**, then **Push origin**.

   ### Method C — git on the command line (for the technically inclined)
   From inside this folder (it already contains `.github/workflows/update.yml`):

   ```bash
   git init
   git add .
   git commit -m "initial dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/insilico-dashboard.git
   git push -u origin main
   ```

   > Tip: don't rename or move files. The workflow expects `template.html`,
   > `data.json`, `update_dashboard.py`, and `requirements.txt` to sit at the repo root,
   > and the workflow itself at `.github/workflows/update.yml`. If `update.yml` is in the
   > wrong place, the **Actions** tab won't show the job in step 6.

3. **Get an Anthropic API key**: https://console.anthropic.com → API Keys → Create key.
   (Add a few dollars of credit; each refresh costs roughly a cent or two.)

4. **Add the key as a repo secret**: repo → **Settings → Secrets and variables →
   Actions → New repository secret**:
   - Name: `ANTHROPIC_API_KEY`  · Value: your key.
   - *(Optional email alerts)* add `RESEND_API_KEY` (from https://resend.com, free tier)
     and `ALERT_EMAIL_TO` (your email). Skip these to run without email.

5. **Enable Pages**: repo → **Settings → Pages** → Source = **GitHub Actions**.

6. **Run it once (then it's automatic).** Step by step:

   1. In your repo, click the **Actions** tab (top menu, between *Pull requests* and
      *Projects*).
   2. First visit only: GitHub may show *"Workflows aren't being run on this forked /
      new repository"* or *"Actions is disabled"* with a green button **I understand my
      workflows, go ahead and enable them** — click it. (If you don't see this, Actions
      is already on.)
   3. In the **left sidebar** under "All workflows", click **Update Insilico dashboard**
      (the name comes from the workflow file).
   4. On the right you'll see a blue banner: *"This workflow has a workflow_dispatch
      event trigger."* Click the **Run workflow** dropdown button (far right), leave the
      branch as **main**, and click the green **Run workflow** button.
   5. Wait ~5–10 seconds, then **refresh the page**. A new run appears with a yellow
      spinning dot (queued/running). Click into it to watch; click the **refresh** job
      to see live logs if you like. It usually finishes in **1–3 minutes**.
   6. Green check ✓ = success. The job did three things: fetched fresh data via the
      Anthropic API, committed the regenerated `index.html`, and deployed to Pages.
      - If you see a red ✗, open the failed step:
        - *"ANTHROPIC_API_KEY" / 401 / authentication* → the secret in step 4 is missing
          or wrong. Re-add it (Settings → Secrets → Actions) and re-run.
        - *credit / quota / 429* → add credit at console.anthropic.com, re-run.
        - *Pages / deploy error* → confirm step 5 set **Settings → Pages → Source =
          GitHub Actions**, then re-run.
        - Re-run anytime with **Re-run all jobs** (top-right of the run page).

   7. **Find your live URL.** Two ways:
      - Repo → **Settings → Pages** → at the top: *"Your site is live at
        https://<your-username>.github.io/insilico-dashboard/"* → click **Visit site**.
      - Or in the **Actions** run, open the **deploy** job — the page URL is printed in
        its summary.
      - First deploy can take 1–2 extra minutes to go live; a 404 right after the run
        usually just means "wait a minute and refresh."

   8. **Put it on your phone.** Open that URL in your phone browser:
      - iPhone (Safari): **Share** → **Add to Home Screen**.
      - Android (Chrome): **⋮ menu** → **Add to Home screen**.
      It now opens like an app and shows the latest data every time.

   From here you do nothing — the workflow re-runs on its schedule (twice daily,
   `0 6,16 * * *` UTC) and the live page updates itself. You can always trigger an
   immediate refresh by repeating sub-steps 1–5.

That's it. From then on it refreshes automatically twice a day and redeploys.

## Tuning
- **Schedule**: edit the `cron` in `.github/workflows/update.yml` (UTC). Current
  `0 6,16 * * *` ≈ 08:00 / 18:00 CET. (GitHub cron can run a few minutes late.)
- **Model/cost**: set repo variable `CLAUDE_MODEL` or edit the default in the script.
- **Email**: handled by the optional Resend step; remove those env lines to disable.

## Honest limitations
- **API cost**: small but non-zero (Anthropic usage per run).
- **LinkedIn**: CxO LinkedIn feeds can't be auto-pulled (ToS / blocking); the holder
  table links to profiles/sources, and executive quotes come from news search only.
- **Phone "push"**: this gives a live URL + optional email. True push notifications
  would need an extra service (e.g. Pushover/Telegram) wired into the email step.
- **Accuracy**: the page is model-generated from web search — point-in-time, may lag or
  err. Not investment advice; verify before trading.

## Run locally to test
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python update_dashboard.py      # writes index.html + data.json
open index.html
```
