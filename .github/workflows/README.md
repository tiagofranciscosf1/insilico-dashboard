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

6. **Run it once**: repo → **Actions** tab → "Update Insilico dashboard" → **Run
   workflow**. After it completes, your live URL is:
   `https://<your-username>.github.io/insilico-dashboard/`
   Open it on your phone, bookmark / add to home screen.

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
