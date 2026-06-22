#!/usr/bin/env python3
"""
Insilico Medicine (HKEX 03696) live dashboard updater.

Runs in the cloud (GitHub Actions). It:
  1. Asks Claude (with the web_search tool) to gather the latest news, catalysts,
     price, lock-up status, and to re-assess direction + sell-likelihood.
  2. Gets back a strict JSON object matching the dashboard DATA schema.
  3. Injects it into template.html -> writes index.html (served by GitHub Pages).
  4. Saves data.json (last-good state) and, optionally, emails an alert digest.

Requires env var ANTHROPIC_API_KEY. Optional email: RESEND_API_KEY + ALERT_EMAIL_TO.
"""
import os, re, json, sys, datetime, urllib.request

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
HERE = os.path.dirname(os.path.abspath(__file__))

SCHEMA_KEYS = ["updated","direction","metrics","rationale","note","catalysts","news",
               "lockups","lockupNote","shares","structNote","holders","holderNote","execs"]

INSTRUCTIONS = r"""
You are maintaining a live investment monitor for Insilico Medicine (HKEX: 03696.HK;
entity InSilico Medicine Cayman TopCo), an AI-driven drug-discovery company, for a
long-term (5-10yr) retail holder sizing a small position.

Use the web_search tool to gather, with EXACT dates and source URLs:
- Company news in the last ~10 days (press releases, clinical/pipeline readouts,
  partnerships/licensing, regulatory CDE/FDA/EMA, analyst rating/target changes).
  For each item capture precise date AND time WITH timezone (PRNewswire shows e.g.
  "Jan 04, 2026, 19:30 ET"; HKEX uses HKT). If no time is published, write "time n/d".
- Catalyst updates: rentosertib (ISM001-055) IPF oral Phase 3 (guided H2 2026) &
  inhalation Phase 1; ISM5411 (IBD, BETHESDA); ISM8969 (NLRP3/CNS, Hygtia); ISM6331
  (pan-TEAD) & ISM3412 (MAT2A) oncology Phase 1; FY results dates.
- Lock-up status: ~6-month lock-ups from the 30 Dec 2025 listing (cornerstone 29 Jun
  2026; pre-IPO & founder undertakings ~30 Jun 2026). NO controlling shareholder
  (founder Zhavoronkov ~8.37% of votes). Check HKEXnews "Disclosure of Interests" for
  actual post-lock-up selling; set a lockup status to "open" once its date has passed.
- Current share price in HK$.
- Public executive commentary (Zhavoronkov; co-CEO/CSO Feng Ren). Do NOT attempt to
  read LinkedIn directly; use only publicly reported quotes from search results.

Then RE-ASSESS:
- direction.call: one of "CONDITIONAL BUY", "BUY", "PASS / REDUCE"; direction.cls:
  "b-cond", "b-buy", or "b-sell" respectively. rationale = 3-4 short bullets balancing
  bull and bear. If nothing changed, keep the prior call.
- holders[].pct = integer 0-100, subjective probability that holder trims/exits after
  lock-up (founders/strategics like Lilly lowest; asset managers/VCs highest). Spike a
  holder's pct if HKEXnews shows actual disposals. KEEP each holder's "link" field.

OUTPUT: Return ONLY a single JSON object (no markdown, no prose) matching EXACTLY this
shape and these keys; preserve field names and the "cls"/"type"/"sent"/"status" enums:

{
 "updated": "DD Mon YYYY, HH:MM UTC",
 "direction": {"call":"CONDITIONAL BUY","cls":"b-cond"},
 "metrics": {"price":"HK$..","ipo":"HK$24.05","high":"HK$80.90","cash":"US$393m"},
 "rationale": ["..",".."],
 "note": "one-line risk/sizing caveat",
 "catalysts": [{"date":"H2 2026","type":"clin|risk|corp","t":"title","pill":"KEY (optional)","d":"detail"}],
 "news": [{"date":"DD Mon YYYY, HH:MM TZ","src":"source","hl":"headline","sent":"pos|neg|neu","url":"https://..","summary":"1-2 sentences","km":["msg1","msg2"]}],
 "lockups": [{"cls":"holder class","basis":"basis","expiry":"date","status":"soon|open|locked"}],
 "lockupNote": "..",
 "shares": {"total":"557,418,500","mktcap":"HK$13.4bn","offer":"94,690,500","conv":"383,418,500"},
 "structNote": "..",
 "holders": [{"who":"name","type":"CxO|Strategic / cornerstone|..","stake":"..","lock":"..","pct":10,"link":"https://.."}],
 "holderNote": "..",
 "execs": [{"n":"name","r":"role","url":"https://.."}]
}

News: newest first, ~6-8 items max, always include summary + 2-3 km bullets.
Keep the founder/share-structure facts (557,418,500 total shares; Zhavoronkov 7.64%
direct / 8.37% with proxy; no controlling shareholder) unless a filing changes them.
"""


def load_last_good():
    try:
        with open(os.path.join(HERE, "data.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def fetch_new_data():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    last = load_last_good()
    seed = ("\nPrior state (update only what changed; keep stable facts):\n"
            + json.dumps(last)) if last else ""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": INSTRUCTIONS + seed}],
    )
    # concatenate the model's final text blocks and pull the JSON object out
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in model output")
    data = json.loads(text[start:end + 1])
    missing = [k for k in SCHEMA_KEYS if k not in data]
    if missing:
        raise ValueError(f"Model output missing keys: {missing}")
    return data


def render(data):
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    html = tpl.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def diff_sections(old, new):
    if not old:
        return ["initial build"]
    changed = []
    for k in SCHEMA_KEYS:
        if k == "updated":
            continue
        if json.dumps(old.get(k), sort_keys=True) != json.dumps(new.get(k), sort_keys=True):
            changed.append(k)
    return changed or ["no material change"]


def send_email(subject, body):
    key, to = os.environ.get("RESEND_API_KEY"), os.environ.get("ALERT_EMAIL_TO")
    if not key or not to:
        print("Email skipped (RESEND_API_KEY / ALERT_EMAIL_TO not set).")
        return
    payload = json.dumps({
        "from": "Insilico Monitor <onboarding@resend.dev>",
        "to": [to], "subject": subject, "text": body,
    }).encode()
    req = urllib.request.Request("https://api.resend.com/emails", data=payload,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
        print("Alert email sent.")
    except Exception as e:
        print(f"Email failed: {e}")


def main():
    old = load_last_good()
    try:
        data = fetch_new_data()
    except Exception as e:
        print(f"Refresh failed ({e}); keeping last-good dashboard.")
        if old:
            render(old)
        sys.exit(0)
    changed = diff_sections(old, data)
    render(data)
    call = data.get("direction", {}).get("call", "?")
    top = data.get("news", [{}])[0]
    body = (f"Insilico (03696) monitor — {data.get('updated')}\n\n"
            f"DIRECTION: {call}\n"
            f"Top item: {top.get('hl','')} ({top.get('date','')})\n"
            f"{top.get('url','')}\n\n"
            f"Sections changed: {', '.join(changed)}\n")
    print(body)
    send_email(f"Insilico (03696) — {call} — {data.get('updated')}", body)


if __name__ == "__main__":
    main()
