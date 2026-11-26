"""Fenn football scores, data-saver edition: built to use as little data as possible. Stdlib only.
Network: site.api.espn.com public scoreboard JSON (unofficial, no key), requested gzip-compressed.
- La Liga and the Champions League: live updates (every 60 s) only while a match is on, otherwise asleep until kick-off.
- Other leagues: no live updates. One check after full time; the final results are saved on disk."""
import gzip, json, os, sys, threading, time, urllib.request
from datetime import datetime

LEAGUES = [("PL", "eng.1"), ("La Liga", "esp.1"), ("Serie A", "ita.1"),
           ("Bundesliga", "ger.1"), ("Ligue 1", "fra.1"), ("UCL", "uefa.champions")]
LIVE_LEAGUES = {"esp.1", "uefa.champions"}   # the only leagues that get live updates
LIVE_EVERY = 60          # seconds between updates during a live match
LEAD = 120               # start live polling this many seconds before kick-off
MATCH_LEN = 135 * 60     # non-live leagues: look for the final result this long after kick-off
RETRY = 600              # non-live leagues: retry interval if a match isn't finished yet
LONG = 6 * 3600          # nothing pending: look for new fixtures this often
STALE = 4 * 3600         # ignore unfinished matches this long after kick-off (postponed etc.)
ERR_RETRY = 300          # after a network error

DATA = os.environ.get("FENN_DATA_DIR") or os.environ.get("NOOK_DATA_DIR") or "."   # NOOK_DATA_DIR is the older name
CFG_PATH = os.path.join(DATA, "config.json")
CACHE_PATH = os.path.join(DATA, "cache.json")
out_lock, lock, trigger = threading.Lock(), threading.RLock(), threading.Event()
cfg = {"league": 0, "team": ""}
cache = {}               # league code -> {"at", "next", "matches"}
err, tile_w, force = "", 104, False


def send(msg):
    with out_lock:
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


def _load(path, into):
    try:
        with open(path, encoding="utf-8") as f:
            into.update(json.load(f))
    except (OSError, ValueError):
        pass


def _save(path, obj):
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f)
    except OSError as e:
        print("save failed:", e, file=sys.stderr)


def txt(text, **kw):
    return {"type": "text", "text": text, **kw}


def parse(data):
    ms = []
    for ev in data.get("events", []):
        comp = ev["competitions"][0]
        side = {c["homeAway"]: c for c in comp["competitors"]}
        st = ev["status"]["type"]
        state = st.get("state", "pre")
        ko = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        detail = ko.astimezone().strftime("%a %H:%M") if state == "pre" else st.get("shortDetail", "")
        name = lambda s: side[s]["team"].get("shortDisplayName") or side[s]["team"].get("displayName", "?")
        abbr = lambda s: side[s]["team"].get("abbreviation") or name(s)[:3].upper()
        ms.append({"id": str(ev.get("id", len(ms))), "home": name("home"), "away": name("away"),
                   "ha": abbr("home"), "aa": abbr("away"),
                   "hs": side["home"].get("score", "0"), "as": side["away"].get("score", "0"),
                   "state": state, "detail": detail, "ko": ko.timestamp()})
    return ms


def plan(code, ms, now):
    """When to look again. This is where the data is saved."""
    open_ = [m for m in ms if m["state"] != "post" and m["ko"] > now - STALE]
    if not open_:
        return now + LONG
    first = min(m["ko"] for m in open_)
    if code in LIVE_LEAGUES:
        if any(m["state"] == "in" for m in open_) or first <= now + LEAD:
            return now + LIVE_EVERY
        return min(first - LEAD, now + LONG)
    end = first + MATCH_LEN
    return min(end, now + LONG) if end > now else now + RETRY


def friendly(e):
    s = str(e)
    if any(k in s for k in ("11001", "getaddrinfo", "Name or service", "unreachable", "10051", "10065")):
        return "No internet, retrying"
    if "timed out" in s:
        return "Timed out, retrying"
    return s[:40]


def fetch(code):
    global err
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard"
    req = urllib.request.Request(url, headers={"User-Agent": "fenn-footballsaver-plugin", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
        ms = parse(json.loads(raw))
        now = time.time()
        with lock:
            cache[code] = {"at": now, "next": plan(code, ms, now), "matches": ms}
            err = ""
            _save(CACHE_PATH, cache)
    except Exception as e:
        print("fetch failed:", e, file=sys.stderr)
        with lock:
            err = friendly(e)
            c = cache.setdefault(code, {"at": 0, "matches": []})
            c["next"] = time.time() + ERR_RETRY


def pick(ms):
    t = cfg["team"].strip().lower()
    if t:
        for m in ms:
            if t in (m["home"] + " " + m["away"]).lower():
                return m
    for m in ms:
        if m["state"] == "in":
            return m
    return ms[0] if ms else None


def label(m):
    return m["detail"] if m["state"] == "pre" else f'{m["hs"]} - {m["as"]}  {m["detail"]}'


def render():
    code = LEAGUES[cfg["league"]][1]
    tracked = code in LIVE_LEAGUES
    with lock:
        c = cache.get(code) or {}
        raw, e = list(c.get("matches", [])), err
        at = c.get("at", 0)
    # a match that was live at the last check but isn't tracked live: don't show a stale score
    ms = [m if (tracked or m["state"] != "in") else dict(m, state="pre", detail="In play") for m in raw]
    m = pick(ms)
    live = tracked and any(x["state"] == "in" for x in ms)
    hot = bool(m) and tracked and m["state"] == "in"
    if m and tile_w < 70:
        tile = {"type": "column", "align": "center", "justify": "center", "gap": 0, "children": [
            {"type": "icon", "icon": "soccer-ball", "size": 20, "color": "red" if hot else "accent"},
            txt("v" if m["state"] == "pre" else f'{m["hs"]}-{m["as"]}', size="small", bold=True)]}
    elif m:
        tile = {"type": "row", "align": "center", "gap": 10, "children": [
            {"type": "icon", "icon": "soccer-ball", "size": 26, "color": "red" if hot else "accent"},
            {"type": "column", "gap": 0, "children": [
                txt(f'{m["ha"]} v {m["aa"]}', size="small", color="dim"),
                txt(label(m), size="title")]}]}
    else:
        tile = {"type": "row", "align": "center", "gap": 8, "children": [
            {"type": "icon", "icon": "soccer-ball", "size": 24, "color": "dim"},
            txt(e or ("Loading…" if not at else "No matches today"), size="small", color="dim", wrap=True)]}
    send({"type": "tile", "view": tile})
    send({"type": "badge", "badge": {"kind": "pulse"} if live else None})

    items = [{"id": x["id"], "title": f'{x["home"]}  {"v" if x["state"] == "pre" else x["hs"] + " - " + x["as"]}  {x["away"]}',
              "trailing": x["detail"], "icon": "soccer-ball", "selected": x["state"] == "in"} for x in ms]
    upd = "Updated " + datetime.fromtimestamp(at).strftime("%H:%M") if at else "Not updated yet"
    note = "Live scores on." if tracked else "No live scores in this league: final results update after full time."
    body = [{"type": "list", "id": "matches", "items": items}] if items else [
        txt(e or "No matches today in this league.", color="dim", wrap=True)]
    page = {"type": "column", "gap": 8, "scroll": True, "children": [
        {"type": "chips", "id": "league", "options": [n for n, _ in LEAGUES], "selected": cfg["league"]},
        {"type": "row", "align": "center", "gap": 8, "children": [
            {"type": "input", "id": "team", "value": cfg["team"], "hint": "Favourite team (optional)", "width": 220},
            {"type": "spacer"},
            {"type": "button", "id": "refresh", "icon": "arrow-clockwise", "tooltip": "Refresh now"}]},
        txt(f"{upd}. {note}", size="small", color="dim", wrap=True),
        *body]}
    send({"type": "page", "view": page})


def refresher():
    global force
    while True:
        code = LEAGUES[cfg["league"]][1]
        with lock:
            due = (cache.get(code) or {}).get("next", 0)
        if force or time.time() >= due:
            force = False
            fetch(code)
        render()
        with lock:
            nxt = (cache.get(code) or {}).get("next", time.time() + ERR_RETRY)
        trigger.wait(max(5, nxt - time.time()))
        trigger.clear()


def main():
    global tile_w, force
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass
    _load(CFG_PATH, cfg)
    _load(CACHE_PATH, cache)
    cfg["league"] = max(0, min(len(LEAGUES) - 1, int(cfg.get("league", 0))))
    render()
    threading.Thread(target=refresher, daemon=True).start()
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        t = msg.get("type")
        if t == "event":
            i, v = msg.get("id"), msg.get("value")
            if i == "league" and isinstance(v, dict):
                cfg["league"] = max(0, min(len(LEAGUES) - 1, int(v.get("index", 0))))
                _save(CFG_PATH, cfg)
                trigger.set()      # fetches only if this league has no fresh data
            elif i == "team" and msg.get("kind") == "submit":
                cfg["team"] = str(v or "").strip()
                _save(CFG_PATH, cfg)
                render()
            elif i == "refresh":
                force = True
                trigger.set()
        elif t == "layout" and msg.get("target") == "tile":
            tile_w = msg.get("width", tile_w)
            render()
        elif t == "shutdown":
            _save(CFG_PATH, cfg)
            return


if __name__ == "__main__":
    main()
