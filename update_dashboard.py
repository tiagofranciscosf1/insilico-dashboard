#!/usr/bin/env python3
"""
Insilico Medicine (HKEX 03696) live dashboard updater.

Runs in the cloud (GitHub Actions). It:
  1. Loads the existing data.json (the full dashboard state, incl. the rich
     sections: projection bands, share structure, Phase 3 timeline, catalysts).
  2. Asks Claude (with web_search) for a SMALL PATCH of only the volatile fields
     (price, news, direction, holder sell-likelihood, lock-up status, today's
     close for the sparkline).
  3. MERGES the patch into the existing state — preserving every other section —
     then renders index.html from template.html.
  4. Saves data.json and (optionally) emails an alert digest via Resend.

Requires env var ANTHROPIC_API_KEY. Optional email: RESEND_API_KEY + ALERT_EMAIL_TO.
This merge approach means new sections added to data.json/template.html are kept
automatically; the model never regenerates the whole object from a fixed schema.
"""
import os, json, sys, datetime, urllib.request

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
HERE = os.path.dirname(os.path.abspath(__file__))

PATCH_INSTRUCTIONS = r"""
You maintain a live monitor for Insilico Medicine (HKEX: 03696.HK; entity InSilico
Medicine Cayman TopCo), an AI-driven drug-discovery company, for a long-term retail
holder. Use the web_search tool to gather TODAY's facts, then return a JSON PATCH of
ONLY the volatile fields below. Do NOT return any other keys — everything else in the
dashboard (projection bands, share structure, Phase 3 timeline, catalysts, execs) is
preserved automatically and must not be touched.

Research (with web_search), capturing dates + source URLs:
- Current HK$ share price and 1-day % change.
- Company news in the last ~10 days (press releases, clinical/pipeline readouts,
  partnerships, regulatory, analyst actions) with precise date+time+timezone
  ("Jan 04, 2026, 19:30 ET"; HKT for HKEX). If no time, write "time n/d".
- Lock-up status: ~6-mo lock-ups from the 30 Dec 2025 listing expire ~29-30 Jun 2026.
  Check HKEXnews "Disclosure of Interests" for any actual post-lock-up selling.
- Re-assess direction and each holder's sell-likelihood. Do NOT scrape LinkedIn.

Return ONLY this JSON object (exact keys; omit a key only if you truly have no update):
{
  "updated": "DD Mon YYYY, HH:MM CET",
  "direction": {"call": "CONDITIONAL BUY|BUY|PASS / REDUCE", "cls": "b-cond|b-buy|b-sell"},
  "rationale": ["3-4 short bullets"],
  "note": "one-line sizing/risk caveat",
  "price_hkd": "40.02",            // numeric string; USD is derived as hkd/7.80
  "price_chg": "+2.1% (1d)",
  "price_dir": "up|down",
  "news": [ {"date":"DD Mon YYYY, HH:MM TZ","src":"..","hl":"..","sent":"pos|neg|neu","url":"https://..","summary":"1-2 sentences","km":["..",".."]} ],   // newest first, 6-8 items
  "holders_pct": { "Alex Zhavoronkov (Founder, CEO)": 10, "Feng Ren (Co-CEO, CSO)": 15, "Aleksandr Aliper (President)": 12, "Eli Lilly": 15, "Tencent": 35, "Temasek": 35, "Schroders": 62, "Qiming / Value Partners (round leads)": 70, "Mesolite Gem Investments": 58 },
  "lockups_status": { "Cornerstone investors": "soon|open|locked", "Pre-IPO / Series A–E investors": "soon|open|locked", "Founder Zhavoronkov": "soon|open|locked" }
}
Rules: news newest first with summary + 2-3 km bullets; holders_pct keys must match the
existing holder "who" names exactly; set a lockup status to "open" once its date passes.
Output ONLY the JSON object, no prose, no markdown fences.
"""


def load_data():
    with open(os.path.join(HERE, "data.json"), encoding="utf-8") as f:
        return json.load(f)


def fetch_patch():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    resp = client.messages.create(
        model=MODEL, max_tokens=6000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": PATCH_INSTRUCTIONS}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("No JSON object in model output")
    return json.loads(text[s:e + 1])


def apply_patch(data, p):
    changed = []
    if "updated" in p:
        data["updated"] = p["updated"]
    if "direction" in p and p["direction"] != data.get("direction"):
        data["direction"] = p["direction"]; changed.append("direction")
    if "rationale" in p:
        data["rationale"] = p["rationale"]
    if "note" in p:
        data["note"] = p["note"]
    # price -> metrics.price, px (hkd/usd/chg/dir/asof), proj.anchor, sparkline series
    if p.get("price_hkd"):
        hkd = str(p["price_hkd"]).replace("HK$", "").strip()
        try:
            hk = float(hkd); usd = f"{hk/7.80:.2f}"
        except ValueError:
            hk = data.get("proj", {}).get("anchor", 0); usd = data.get("px", {}).get("usd", "")
        today = datetime.date.today().strftime("%d %b %Y")
        data.setdefault("metrics", {})["price"] = f"HK${hkd}"
        px = data.setdefault("px", {})
        old_hkd = px.get("hkd")
        px.update({"hkd": hkd, "usd": usd, "chg": p.get("price_chg", px.get("chg", "")),
                   "dir": p.get("price_dir", px.get("dir", "up")), "asof": today})
        if "proj" in data and hk:
            data["proj"]["anchor"] = hk
            data["proj"]["anchorLabel"] = f"HK${hkd} ({today})"
        # append today's close to the sparkline series (replace same-day point), cap 60
        ser = data.setdefault("series", [])
        d_short = datetime.date.today().strftime("%d %b %y")
        if ser and ser[-1].get("d") == d_short:
            ser[-1]["p"] = hk
        else:
            ser.append({"d": d_short, "p": hk})
        data["series"] = ser[-60:]
        if old_hkd != hkd:
            changed.append(f"price {old_hkd}->{hkd}")
    if "news" in p and p["news"]:
        if json.dumps(p["news"], sort_keys=True) != json.dumps(data.get("news"), sort_keys=True):
            changed.append(f"news ({len(p['news'])})")
        data["news"] = p["news"]
    if "holders_pct" in p:
        for h in data.get("holders", []):
            np_ = p["holders_pct"].get(h["who"])
            if isinstance(np_, int) and np_ != h.get("pct"):
                changed.append(f"{h['who'].split(' (')[0]} {h.get('pct')}->{np_}")
                h["pct"] = np_
    if "lockups_status" in p:
        for lk in data.get("lockups", []):
            ns = p["lockups_status"].get(lk["cls"])
            if ns and ns != lk.get("status"):
                changed.append(f"lockup {lk['cls']} ->{ns}")
                lk["status"] = ns
    return data, (changed or ["no material change"])


def render(data):
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    html = tpl.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send_email(subject, body):
    key, to = os.environ.get("RESEND_API_KEY"), os.environ.get("ALERT_EMAIL_TO")
    if not key or not to:
        print("Email skipped (RESEND_API_KEY / ALERT_EMAIL_TO not set).")
        return
    payload = json.dumps({"from": "Insilico Monitor <onboarding@resend.dev>",
                          "to": [to], "subject": subject, "text": body}).encode()
    req = urllib.request.Request("https://api.resend.com/emails", data=payload,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20); print("Alert email sent.")
    except Exception as ex:
        print(f"Email failed: {ex}")


def main():
    data = load_data()
    try:
        patch = fetch_patch()
    except Exception as ex:
        print(f"Refresh failed ({ex}); re-rendering last-good dashboard.")
        render(data); sys.exit(0)
    data, changed = apply_patch(data, patch)
    render(data)
    call = data.get("direction", {}).get("call", "?")
    px = data.get("px", {})
    top = (data.get("news") or [{}])[0]
    body = (f"Insilico (03696) monitor - {data.get('updated')}\n\n"
            f"DIRECTION: {call}\n"
            f"Price: HK${px.get('hkd','?')} / US${px.get('usd','?')} ({px.get('chg','')})\n"
            f"Top item: {top.get('hl','')} ({top.get('date','')})\n{top.get('url','')}\n\n"
            f"Sections changed: {', '.join(changed)}\n")
    print(body)
    send_email(f"Insilico (03696) - {call} - {data.get('updated')}", body)


if __name__ == "__main__":
    main()
