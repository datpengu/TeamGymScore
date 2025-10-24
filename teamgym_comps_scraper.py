import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

MAIN_URL = "https://live.sporteventsystems.se/Score/?country=swe"


def fetch_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


# 🏆 1. Get all TeamGym competitions from main listing
def get_teamgym_competitions():
    html = fetch_html(MAIN_URL)
    soup = BeautifulSoup(html, "html.parser")

    comps = []
    teamgym_section = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string=lambda s: s and "Teamgym" in s)
    if not teamgym_section:
        print("❌ No Teamgym section found")
        return comps

    # Traverse all rows after the Teamgym header until the next header div
    for row in teamgym_section.find_parent().find_next_siblings("div", class_="row"):
        header = row.find("div", class_="col fs-4 px-2 bg-dark-subtle")
        if header:  # next sport header encountered
            print("🛑 Reached next section, stopping Teamgym scrape.")
            break

        link = row.find("a", href=True)
        if not link:
            continue

        href = link["href"]
        title = link.get_text(strip=True)
        date_from = row.find("div", class_="col-12 col-md-6 col-xl-4 col-xxl-3 fs-6 d-block")
        place = row.find("div", class_="col-0 col-md-6 col-xl-4 col-xxl-6 fs-6  d-none d-md-block")

        comp_url = href if href.startswith("http") else f"https://live.sporteventsystems.se{href}"

        comps.append({
            "title": title,
            "url": comp_url,
            "date_from": date_from.get_text(strip=True) if date_from else None,
            "place": place.get_text(strip=True) if place else None
        })

    print(f"✅ Found {len(comps)} TeamGym competitions")
    return comps


# ⚙️ 2. Token-based parsing helpers
def tokenize_div(div):
    return [s for s in div.stripped_strings]


def is_rank_token(tok):
    return re.fullmatch(r"\d{1,2}", tok) is not None


def is_startpos_token(tok):
    return re.fullmatch(r"\d{1,2}", tok) is not None


def is_score_token(tok):
    return re.fullmatch(r"\d+,\d{3}", tok) is not None


def is_dec_token(tok):
    return re.fullmatch(r"[DEC]:\s*\d+,\d{3}", tok) is not None


# 🧩 3. Parse tokens into structured team data
def parse_tokens(tokens):
    teams = []
    i = 0
    while i < len(tokens):
        if i + 2 < len(tokens) and is_rank_token(tokens[i]) and is_startpos_token(tokens[i + 1]):
            rank = int(tokens[i])
            start_position = int(tokens[i + 1])
            name = tokens[i + 2].strip()
            j = i + 3
            scores = []
            decs = []

            while j < len(tokens):
                tok = tokens[j]
                if j + 1 < len(tokens) and is_rank_token(tokens[j]) and is_startpos_token(tokens[j + 1]):
                    break

                if is_score_token(tok):
                    scores.append(float(tok.replace(",", ".")))
                    j += 1
                    continue

                if is_dec_token(tok):
                    m = re.search(r"(\d+,\d{3})", tok)
                    if m:
                        decs.append(float(m.group(1).replace(",", ".")))
                    j += 1
                    continue

                if tok in ("D:", "E:", "C:") and j + 1 < len(tokens) and is_score_token(tokens[j + 1]):
                    decs.append(float(tokens[j + 1].replace(",", ".")))
                    j += 2
                    continue

                j += 1
                if j - i > 200:
                    break

            def dec_at(idx):
                return decs[idx] if idx < len(decs) else None

            fx = {"score": scores[0] if len(scores) > 0 else None, "D": dec_at(0), "E": dec_at(1), "C": dec_at(2)}
            tu = {"score": scores[1] if len(scores) > 1 else None, "D": dec_at(3), "E": dec_at(4), "C": dec_at(5)}
            tr = {"score": scores[2] if len(scores) > 2 else None, "D": dec_at(6), "E": dec_at(7), "C": dec_at(8)}

            total = scores[3] if len(scores) > 3 else None
            gap = scores[4] if len(scores) > 4 and rank != 1 else 0.0

            teams.append({
                "rank": rank,
                "start_position": start_position,
                "name": name,
                "fx": fx,
                "tu": tu,
                "tr": tr,
                "total": total,
                "gap": gap
            })
            i = j
        else:
            i += 1
    return teams


# 🏁 4. Parse competition results page with status detection
def parse_competition_page(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    active_div = soup.find("div", class_=lambda c: c and "show active" in c)
    if not active_div:
        active_div = soup.find("div", class_=lambda c: c and "tab-pane" in c)
    if not active_div:
        print(f"⚠️ No active result container in {url}")
        return {"status": "upcoming", "teams": []}

    tokens = tokenize_div(active_div)
    teams = parse_tokens(tokens)

    valid_teams = [t for t in teams if any([t["fx"]["score"], t["tu"]["score"], t["tr"]["score"], t["total"]])]

    if len(valid_teams) == 0:
        return {"status": "upcoming", "teams": []}

    fully_scored = sum(
        1 for t in valid_teams if all([t["fx"]["score"], t["tu"]["score"], t["tr"]["score"], t["total"]])
    )

    if fully_scored == len(valid_teams):
        status = "finished"
    else:
        status = "ongoing"

    print(f"✅ Parsed {len(valid_teams)} teams ({status}) from {url}")
    return {"status": status, "teams": valid_teams}


# 🧾 5. Main entry point
def main():
    competitions = get_teamgym_competitions()
    results = []

    for comp in competitions:
        print(f"🔍 Parsing {comp['title']}...")
        data = parse_competition_page(comp["url"])
        results.append({
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "competition": comp["title"],
            "status": data["status"],
            "date_from": comp["date_from"],
            "place": comp["place"],
            "teams": data["teams"]
        })

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(results)} competitions to results.json")


if __name__ == "__main__":
    main()
