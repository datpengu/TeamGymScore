import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

MAIN_URL = "https://live.sporteventsystems.se/Score/?country=swe"

# ------------------ Utility ------------------

def fetch_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


# ------------------ Step 1: Find all TeamGym competitions ------------------

def get_teamgym_competitions():
    html = fetch_html(MAIN_URL)
    soup = BeautifulSoup(html, "html.parser")

    comps = []
    teamgym_section = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string=lambda s: s and "Teamgym" in s)
    if not teamgym_section:
        print("❌ No Teamgym section found")
        return comps

    # Traverse rows after the Teamgym header until the next header div
    for row in teamgym_section.find_parent().find_next_siblings("div", class_="row"):
        header = row.find("div", class_="col fs-4 px-2 bg-dark-subtle")
        if header:  # stop if we hit a new header (like "Artistic Gymnastics")
            print("🛑 Reached next section, stopping Teamgym scrape.")
            break

        link = row.find("a", href=True)
        if not link:
            continue

        href = link["href"]
        title = link.get_text(strip=True)

        # Extract date_from, date_to, and place
        date_tags = row.find_all(string=re.compile(r"\d{4}-\d{2}-\d{2}"))
        date_from = date_tags[0].strip() if len(date_tags) > 0 else None
        date_to = date_tags[1].strip() if len(date_tags) > 1 else None

        place_tag = row.find(lambda tag: tag.name == "div" and tag.get_text(strip=True)
                             and not re.search(r"\d{4}-\d{2}-\d{2}", tag.get_text()))
        place = None
        if place_tag:
            place_text = place_tag.get_text(strip=True).replace("\xa0", " ")
            if not re.match(r"\d{4}-\d{2}-\d{2}", place_text):
                place = place_text

        comp_url = href if href.startswith("http") else f"https://live.sporteventsystems.se{href}"

        comps.append({
            "title": title,
            "url": comp_url,
            "date_from": date_from,
            "date_to": date_to,
            "place": place
        })

    print(f"✅ Found {len(comps)} TeamGym competitions with date/place")
    return comps


# ------------------ Step 2: Parse one competition page ------------------

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


def parse_tokens(tokens):
    teams = []
    i = 0
    while i < len(tokens):
        if i + 2 < len(tokens) and is_rank_token(tokens[i]) and is_startpos_token(tokens[i+1]):
            rank = int(tokens[i])
            start_position = int(tokens[i+1])
            name = tokens[i+2].strip()
            j = i + 3
            scores, decs = [], []

            while j < len(tokens):
                tok = tokens[j]
                if j + 1 < len(tokens) and is_rank_token(tokens[j]) and is_startpos_token(tokens[j+1]):
                    break
                if is_score_token(tok):
                    scores.append(float(tok.replace(",", ".")))
                elif is_dec_token(tok):
                    m = re.search(r"(\d+,\d{3})", tok)
                    if m:
                        decs.append(float(m.group(1).replace(",", ".")))
                elif tok in ("D:", "E:", "C:") and j + 1 < len(tokens) and is_score_token(tokens[j+1]):
                    decs.append(float(tokens[j+1].replace(",", ".")))
                    j += 1
                j += 1

            def dec_at(idx): return decs[idx] if idx < len(decs) else None

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


def parse_competition_page(url):
    """Parse teams from one competition page, allowing partial results and tagging status."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    active_div = soup.find("div", class_=lambda c: c and "show active" in c)
    if not active_div:
        active_div = soup.find("div", class_=lambda c: c and "tab-pane" in c)
    if not active_div:
        print(f"⚠️ No active result container found in {url}")
        return None

    tokens = tokenize_div(active_div)
    teams = parse_tokens(tokens)

    valid_teams = [t for t in teams if any([t["fx"]["score"], t["tu"]["score"], t["tr"]["score"], t["total"]])]

    if len(valid_teams) == 0:
        status = "upcoming"
        print(f"⏭️ {url} — no teams have results yet.")
        return {"status": status, "teams": []}

    fully_scored = sum(
        1 for t in valid_teams
        if all([t["fx"]["score"], t["tu"]["score"], t["tr"]["score"], t["total"]])
    )

    if fully_scored == len(valid_teams):
        status = "finished"
    elif fully_scored == 0:
        status = "ongoing"
    else:
        status = "ongoing"

    print(f"✅ Parsed {len(valid_teams)} teams ({status}) from {url}")

    return {"status": status, "teams": valid_teams}


# ------------------ Step 3: Main ------------------

def main():
    competitions = get_teamgym_competitions()
    results = []

    for comp in competitions:
        comp_data = parse_competition_page(comp["url"])
        if not comp_data:
            continue

        results.append({
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "competition": comp["title"],
            "status": comp_data["status"],
            "date_from": comp["date_from"],
            "date_to": comp["date_to"],
            "place": comp["place"],
            "teams": comp_data["teams"]
        })

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n🏁 Done — saved {len(results)} competitions to results.json")


if __name__ == "__main__":
    main()
