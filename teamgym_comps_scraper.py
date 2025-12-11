import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

BASE_URL = "https://live.sporteventsystems.se"

# ---------------------------
# BASIC UTILITIES
# ---------------------------
def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text

def safe(lst, idx):
    return lst[idx] if idx < len(lst) else None

def number(tok):
    try: return float(tok.replace(",", "."))
    except: return None

def strip_tokens(div):
    return [s for s in div.stripped_strings]

def is_rank(tok): return re.fullmatch(r"\d{1,2}", tok) is not None
def is_start(tok): return re.fullmatch(r"\d{1,2}", tok) is not None
def is_score(tok): return re.fullmatch(r"\d+,\d{3}", tok) is not None

# ---------------------------
# DISCOVER ALL TEAMGYM COMPETITIONS
# ---------------------------
def discover_teamgym_competitions():
    html = fetch_html(f"{BASE_URL}/Score/?country=swe")
    soup = BeautifulSoup(html, "html.parser")

    results = []
    header = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string=re.compile("Teamgym", re.I))
    if not header:
        return results

    row = header.find_parent("div", class_="row")
    for sibling in row.find_next_siblings("div"):
        next_header = sibling.find("div", class_="col fs-4 px-2 bg-dark-subtle")
        if next_header:
            break

        a = sibling.find("a", href=True)
        if not a: continue
        link = urljoin(BASE_URL, a["href"])
        name = a.get_text(strip=True)

        cols = sibling.select(".col-12, .col-md-6, .col-xl-4, .col-xxl-3, .col-xxl-6")
        date_from = cols[0].get_text(strip=True) if len(cols) else None
        date_to = cols[1].get_text(strip=True) if len(cols) > 1 else None
        place = cols[-1].get_text(strip=True) if len(cols) else None

        results.append({
            "competition": name,
            "url": link,
            "date_from": date_from,
            "date_to": date_to,
            "place": place
        })

    return results

# ---------------------------
# GET CLASS BUTTONS
# ---------------------------
def find_class_buttons(soup):
    container = soup.find("div", class_="d-none d-md-block mb-2")
    if not container:
        return []
    links = []
    for a in container.find_all("a", href=True):
        links.append({
            "name": a.get_text(strip=True),
            "url": urljoin(BASE_URL, a["href"])
        })
    return links

# ---------------------------
# TAB IDS
# ---------------------------
def tab_ids(f):
    return (
        f"Allround-{f}",
        f"App1-{f}",
        f"App2-{f}",
        f"App3-{f}"
    )

# ---------------------------
# PARSE ALLROUND TOKENS
# ---------------------------
def parse_allround_tokens(tokens):
    teams = []
    i = 0

    while i < len(tokens):
        if i+2 < len(tokens) and is_rank(tokens[i]) and is_start(tokens[i+1]):
            rank = int(tokens[i])
            start = int(tokens[i+1])
            name = tokens[i+2]
            j = i + 3

            scores, decs = [], []

            while j < len(tokens):
                if j+1 < len(tokens) and is_rank(tokens[j]) and is_start(tokens[j+1]):
                    break

                tok = tokens[j]

                if is_score(tok):
                    scores.append(number(tok))
                    j += 1
                    continue

                m = re.match(r"^(D|E|C)[:\-]?\s*(\d+,\d{3})$", tok)
                if m:
                    decs.append(number(m.group(2)))
                    j += 1
                    continue

                if tok in ("D","D:","E","E:","C","C:") and j+1 < len(tokens) and is_score(tokens[j+1]):
                    decs.append(number(tokens[j+1]))
                    j += 2
                    continue

                j += 1

            fx = {"score": safe(scores,0), "D": safe(decs,0), "E": safe(decs,1), "C": safe(decs,2), "HJ": None}
            tu = {"score": safe(scores,1), "D": safe(decs,3), "E": safe(decs,4), "C": safe(decs,5), "HJ": None}
            tr = {"score": safe(scores,2), "D": safe(decs,6), "E": safe(decs,7), "C": safe(decs,8), "HJ": None}
            total = safe(scores,3)
            gap = 0.0 if rank == 1 else safe(scores,4)

            teams.append({
                "rank": rank,
                "start_position": start,
                "name": name,
                "fx": fx, "tu": tu, "tr": tr,
                "total": total,
                "gap": gap
            })

            i = j
        else:
            i += 1

    return teams

# ---------------------------
# PARSE APPARATUS TOKENS (FX/TU/TR)
# ---------------------------
def parse_apparatus_tokens(tokens):
    teams = []
    i = 0

    while i < len(tokens):
        if i+2 < len(tokens) and is_rank(tokens[i]) and is_start(tokens[i+1]):
            rank = int(tokens[i])
            start = int(tokens[i+1])
            name = tokens[i+2]
            j = i + 3

            D=E=C=HJ=score=gap=None

            while j < len(tokens):
                if j+1 < len(tokens) and is_rank(tokens[j]) and is_start(tokens[j+1]):
                    break

                tok = tokens[j]

                if tok.startswith("D") and j+1<len(tokens) and is_score(tokens[j+1]):
                    D=number(tokens[j+1]); j+=2; continue
                if tok.startswith("E") and j+1<len(tokens) and is_score(tokens[j+1]):
                    E=number(tokens[j+1]); j+=2; continue
                if tok.startswith("C") and j+1<len(tokens) and is_score(tokens[j+1]):
                    C=number(tokens[j+1]); j+=2; continue
                if tok.startswith("HJ") and j+1<len(tokens) and is_score(tokens[j+1]):
                    HJ=number(tokens[j+1]); j+=2; continue

                if is_score(tok):
                    if score is None: score=number(tok)
                    elif gap is None: gap=number(tok)
                    j+=1
                    continue

                j+=1

            teams.append({
                "rank": rank,
                "start_position": start,
                "name": name,
                "D": D, "E": E, "C": C, "HJ": HJ,
                "score": score,
                "gap": 0.0 if rank == 1 else gap
            })

            i = j
        else:
            i += 1

    return teams

# ---------------------------
# FILL MISSING APPARATUS FIELDS USING ALLROUND
# ---------------------------
def fill_missing(app_list, allround_list, key):
    lookup = {t["name"]: t[key] for t in allround_list}

    for entry in app_list:
        name = entry["name"]
        if name not in lookup:
            continue

        full = lookup[name]

        if entry.get("D") is None: entry["D"] = full["D"]
        if entry.get("E") is None: entry["E"] = full["E"]
        if entry.get("C") is None: entry["C"] = full["C"]
        if entry.get("HJ") is None: entry["HJ"] = full.get("HJ")
        if entry.get("score") is None: entry["score"] = full["score"]

# ---------------------------
# DETERMINE STATUS
# ---------------------------
def determine_status(teams):
    if not teams:
        return "upcoming"
    finished = sum(1 for t in teams if t.get("total"))
    if finished == 0:
        return "upcoming"
    if finished < len(teams):
        return "ongoing"
    return "finished"

# ---------------------------
# FETCH TEAM NAMES FOR UPCOMING COMPETITIONS
# ---------------------------
def get_upcoming_team_names(soup):
    """
    Team names are listed in a table header row even before scores exist.
    """
    names = []
    table = soup.find("table")
    if not table:
        return []

    for row in table.find_all("tr"):
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) >= 3:
            # structure: PL | # | NAME ...
            if cols[0].isdigit():
                names.append(cols[2])
    return names

# ---------------------------
# PARSE CLASS PAGE
# ---------------------------
def parse_class_page(url: str):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    f_val = parse_qs(urlparse(url).query).get("f", [None])[0]
    if not f_val:
        return {"teams": [], "apparatus": {}, "status": "upcoming"}

    allround_id, fx_id, tu_id, tr_id = tab_ids(f_val)

    def toks(tab):
        div = soup.find("div", id=tab)
        return strip_tokens(div) if div else []

    allround = parse_allround_tokens(toks(allround_id))

    fx = parse_apparatus_tokens(toks(fx_id))
    tu = parse_apparatus_tokens(toks(tu_id))
    tr = parse_apparatus_tokens(toks(tr_id))

    # fill missing values
    fill_missing(fx, allround, "fx")
    fill_missing(tu, allround, "tu")
    fill_missing(tr, allround, "tr")

    # status
    status = determine_status(allround)

    # If upcoming → extract team names
    if status == "upcoming":
        team_names = get_upcoming_team_names(soup)
        allround = [{"rank": None, "start_position": None, "name": name,
                     "fx": {}, "tu": {}, "tr": {}, "total": None, "gap": None}
                    for name in team_names]

    return {
        "teams": allround,
        "apparatus": {"fx": fx, "tu": tu, "tr": tr},
        "status": status
    }

# ---------------------------
# PARSE FULL COMPETITION
# ---------------------------
def parse_full_competition(url, meta):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    classes = find_class_buttons(soup)

    comp_out = {
        "competition": meta["competition"],
        "date_from": meta["date_from"],
        "date_to": meta["date_to"],
        "place": meta["place"],
        "classes": []
    }

    for cls in classes:
        parsed = parse_class_page(cls["url"])
        comp_out["classes"].append({
            "class_name":
            cls["name"],
            "url":
            cls["url"],
            **parsed
        })

    return comp_out

# ---------------------------
# MAIN
# ---------------------------
def main():
    comps = discover_teamgym_competitions()

    # newest → oldest
    comps.sort(key=lambda c: c["date_from"] or "0", reverse=True)

    results = []
    for comp in comps:
        try:
            results.append(parse_full_competition(comp["url"], comp))
        except Exception as e:
            print(f"❌ Failed {comp['competition']}: {e}")

    final = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "competitions": results
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"✓ Wrote {len(results)} competitions.")

if __name__ == "__main__":
    main()
