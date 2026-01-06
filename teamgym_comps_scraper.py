import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from pathlib import Path
from time import time

BASE_URL = "https://live.sporteventsystems.se"

# --------------------------------------------------
# CACHE CONFIG
# --------------------------------------------------
CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 60 * 15  # 15 minutes

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def fetch_html(url: str) -> str:
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text

def cached_fetch(url: str, key: str) -> str:
    path = CACHE_DIR / f"{key}.html"
    if path.exists():
        if time() - path.stat().st_mtime < CACHE_TTL:
            return path.read_text(encoding="utf-8")

    html = fetch_html(url)
    path.write_text(html, encoding="utf-8")
    return html

def num(v):
    try:
        return float(v.replace(",", "."))
    except:
        return None

def tokens(div):
    return [s for s in div.stripped_strings] if div else []

def is_rank(t): return re.fullmatch(r"\d{1,2}", t)
def is_score(t): return re.fullmatch(r"\d+,\d{3}", t)

# --------------------------------------------------
# DISCOVER TEAMGYM (YEAR FALLBACK)
# --------------------------------------------------
def discover_teamgym():
    years = [
        datetime.utcnow().year,
        datetime.utcnow().year - 1,
        -1
    ]

    for year in years:
        print(f"🔍 Discovering TeamGym (year={year})")
        html = cached_fetch(
            f"{BASE_URL}/Score/?country=swe&year={year}",
            f"discover_{year}"
        )
        soup = BeautifulSoup(html, "html.parser")

        header = soup.find(
            "div",
            class_="col fs-4 px-2 bg-dark-subtle",
            string=re.compile("Teamgym", re.I)
        )
        if not header:
            continue

        row = header.find_parent("div", class_="row")
        out = []

        for sib in row.find_next_siblings("div"):
            if sib.find("div", class_="col fs-4 px-2 bg-dark-subtle"):
                break

            a = sib.find("a", href=True)
            if not a:
                continue

            cols = sib.select(
                ".col-12, .col-md-6, .col-xl-4, .col-xxl-3, .col-xxl-6"
            )

            out.append({
                "competition": a.get_text(strip=True),
                "url": urljoin(BASE_URL, a["href"]),
                "date_from": cols[0].get_text(strip=True) if len(cols) > 0 else None,
                "date_to": cols[1].get_text(strip=True) if len(cols) > 1 else None,
                "place": cols[-1].get_text(strip=True) if len(cols) > 2 else None,
                "source_year": year
            })

        if out:
            print(f"✅ Found {len(out)} competitions (year={year})")
            return out

    print("❌ No TeamGym competitions found")
    return []

# --------------------------------------------------
# FIND CLASS BUTTONS
# --------------------------------------------------
def find_classes(soup):
    box = soup.find("div", class_="d-none d-md-block mb-2")
    if not box:
        return []

    return [
        {"name": a.get_text(strip=True), "url": urljoin(BASE_URL, a["href"])}
        for a in box.find_all("a", href=True)
    ]

# --------------------------------------------------
# PARSE ALLROUND
# --------------------------------------------------
def parse_allround(tok):
    teams, i = [], 0

    while i + 2 < len(tok):
        if not is_rank(tok[i]):
            i += 1
            continue

        rank = int(tok[i])
        start = int(tok[i+1]) if tok[i+1].isdigit() else None
        name = tok[i+2]

        scores, decs = [], []
        j = i + 3

        while j < len(tok):
            if j + 1 < len(tok) and is_rank(tok[j]) and tok[j+1].isdigit():
                break

            if is_score(tok[j]):
                scores.append(num(tok[j]))

            m = re.match(r"(D|E|C|HJ)[\:\-]?\s*(\d+,\d{3})", tok[j])
            if m:
                decs.append(num(m.group(2)))

            j += 1

        fx = {"score": scores[0] if len(scores) > 0 else None,
              "D": decs[0] if len(decs) > 0 else None,
              "E": decs[1] if len(decs) > 1 else None,
              "C": decs[2] if len(decs) > 2 else None,
              "HJ": None}

        tu = {"score": scores[1] if len(scores) > 1 else None,
              "D": decs[3] if len(decs) > 3 else None,
              "E": decs[4] if len(decs) > 4 else None,
              "C": decs[5] if len(decs) > 5 else None,
              "HJ": None}

        tr = {"score": scores[2] if len(scores) > 2 else None,
              "D": decs[6] if len(decs) > 6 else None,
              "E": decs[7] if len(decs) > 7 else None,
              "C": decs[8] if len(decs) > 8 else None,
              "HJ": None}

        total = scores[3] if len(scores) > 3 else None

        teams.append({
            "rank": rank,
            "start_position": start,
            "name": name,
            "fx": fx,
            "tu": tu,
            "tr": tr,
            "total": total,
            "gap": None
        })

        i = j

    if teams and teams[0]["total"] is not None:
        lead = teams[0]["total"]
        for t in teams:
            t["gap"] = 0.0 if t["rank"] == 1 else round(lead - (t["total"] or 0), 3)

    return teams

# --------------------------------------------------
# PARSE APPARATUS
# --------------------------------------------------
def parse_apparatus(tok):
    rows, i = [], 0

    while i + 2 < len(tok):
        if not is_rank(tok[i]):
            i += 1
            continue

        rank = int(tok[i])
        start = int(tok[i+1]) if tok[i+1].isdigit() else None
        name = tok[i+2]

        D = E = C = HJ = score = None
        j = i + 3

        while j < len(tok):
            if j + 1 < len(tok) and is_rank(tok[j]) and tok[j+1].isdigit():
                break

            if tok[j].startswith("D") and j+1 < len(tok):
                D = num(tok[j+1])
            if tok[j].startswith("E") and j+1 < len(tok):
                E = num(tok[j+1])
            if tok[j].startswith("C") and j+1 < len(tok):
                C = num(tok[j+1])
            if tok[j].startswith("HJ") and j+1 < len(tok):
                HJ = num(tok[j+1])
            if is_score(tok[j]):
                score = num(tok[j])

            j += 1

        rows.append({
            "rank": rank,
            "start_position": start,
            "name": name,
            "D": D, "E": E, "C": C, "HJ": HJ,
            "score": score,
            "gap": None
        })

        i = j

    if rows and rows[0]["score"] is not None:
        lead = rows[0]["score"]
        for r in rows:
            r["gap"] = 0.0 if r["rank"] == 1 else round(lead - (r["score"] or 0), 3)

    return rows

# --------------------------------------------------
# PARSE CLASS PAGE
# --------------------------------------------------
def parse_class(url):
    soup = BeautifulSoup(fetch_html(url), "html.parser")
    f = parse_qs(urlparse(url).query).get("f", [None])[0]
    if not f:
        return None

    def tab(id): return soup.find("div", id=id)

    allround = parse_allround(tokens(tab(f"Allround-{f}")))
    fx = parse_apparatus(tokens(tab(f"App1-{f}")))
    tu = parse_apparatus(tokens(tab(f"App2-{f}")))
    tr = parse_apparatus(tokens(tab(f"App3-{f}")))

    return {
        "teams": allround,
        "fx_app": fx,
        "tu_app": tu,
        "tr_app": tr
    }

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    competitions = discover_teamgym()
    results = []

    for comp in competitions:
        print(f"\n🏆 {comp['competition']}")
        soup = BeautifulSoup(fetch_html(comp["url"]), "html.parser")
        classes = find_classes(soup)

        entry = {
            "competition": comp["competition"],
            "date_from": comp["date_from"],
            "date_to": comp["date_to"],
            "place": comp["place"],
            "classes": []
        }

        for cls in classes:
            parsed = parse_class(cls["url"])
            if parsed:
                entry["classes"].append({
                    "class_name": cls["name"],
                    "url": cls["url"],
                    **parsed
                })

        results.append(entry)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump({
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "competitions": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Scraped {len(results)} competitions")

if __name__ == "__main__":
    main()
