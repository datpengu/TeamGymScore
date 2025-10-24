import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

BASE_URL = "https://live.sporteventsystems.se"
INDEX_URL = f"{BASE_URL}/Score/?country=swe"

# ----------------- HTML Fetcher -----------------
def fetch_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


# ----------------- Token-based Parser (your old one) -----------------
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
                "gap": gap,
            })
            i = j
        else:
            i += 1
    return teams


def parse_competition_page(url):
    """Parse teams from one competition page, allowing partial results."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # Try to find the main active result div
    active_div = soup.find("div", class_=lambda c: c and "show active" in c)
    if not active_div:
        active_div = soup.find("div", class_=lambda c: c and "tab-pane" in c)
    if not active_div:
        print(f"⚠️ No active result container found in {url}")
        return []

    tokens = tokenize_div(active_div)
    teams = parse_tokens(tokens)

    # 🧩 Filter logic: remove teams with absolutely no data
    valid_teams = []
    for t in teams:
        has_any_score = any([
            t["fx"]["score"], t["tu"]["score"], t["tr"]["score"], t["total"]
        ])
        if has_any_score:
            valid_teams.append(t)

    # 🪫 If no teams have any score — skip this competition
    if len(valid_teams) == 0:
        print(f"⏭️ Skipping {url} (no team has results yet)")
        return []

    # 💡 But if only some teams are missing — keep them all
    print(f"✅ Parsed {len(valid_teams)} valid teams (of {len(teams)}) from {url}")
    return valid_teams

# ----------------- TeamGym Competition Scraper -----------------
def scrape_teamgym_list():
    html = fetch_html(INDEX_URL)
    soup = BeautifulSoup(html, "html.parser")

    competitions = []

    header = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string="Teamgym")
    if not header:
        print("⚠️ Could not find Teamgym section.")
        return competitions

    for row in header.find_all_next("div", class_="row"):
        next_header = row.find("div", class_="col fs-4 px-2 bg-dark-subtle")
        if next_header:
            break

        cols = row.find_all("div", class_="fs-6")
        if not cols:
            continue

        link = row.find("a", href=True)
        if not link or "WebScore" not in link["href"]:
            continue

        date_from = cols[0].get_text(strip=True) if len(cols) > 0 else ""
        date_to = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        place = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        title = link.get_text(strip=True)
        href = link["href"]
        full_url = href if href.startswith("http") else BASE_URL + href

        competitions.append({
            "title": title,
            "url": full_url,
            "date_from": date_from,
            "date_to": date_to,
            "place": place,
        })

    return competitions


# ----------------- Main -----------------
if __name__ == "__main__":
    competitions = scrape_teamgym_list()
    all_data = {"last_updated": datetime.utcnow().isoformat() + "Z", "competitions": []}

    for comp in competitions:
        print(f"\n🏆 Processing {comp['title']} ({comp['place']})")
        teams = parse_competition_page(comp["url"])
        comp["teams"] = teams
        all_data["competitions"].append(comp)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(competitions)} competitions to results.json")
