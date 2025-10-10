import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"

def fetch_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text

def find_competition_title(soup):
    # The title is often in a header or tab label. Let’s try a few possibilities.
    # Look for <h2> or <h1> or a tab nav item containing the active competition name.
    # Fallback: “Competition” default.
    possible = soup.select("h1, h2")
    for tag in possible:
        text = tag.get_text(strip=True)
        # Avoid generic headers
        if len(text) > 3 and not text.lower().startswith("pl"):
            return text
    # Try nav tab
    nav = soup.select_one("ul.nav li.active a")
    if nav:
        return nav.get_text(strip=True)
    return "Competition"

def get_active_mangkamp_div(soup):
    # prefer the div with class "show active"
    div = soup.find("div", class_=lambda c: c and "show active" in c)
    if div:
        return div
    # fallback to first .tab-pane
    div = soup.find("div", class_=lambda c: c and "tab-pane" in c)
    return div

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
            scores = []
            decs = []
            while j < len(tokens):
                tok = tokens[j]
                if j + 1 < len(tokens) and is_rank_token(tokens[j]) and is_startpos_token(tokens[j+1]):
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
                if tok in ("D:", "E:", "C:") and j + 1 < len(tokens) and is_score_token(tokens[j+1]):
                    decs.append(float(tokens[j+1].replace(",", ".")))
                    j += 2
                    continue
                j += 1
                if j - i > 200:
                    break

            def dec_at(idx):
                return decs[idx] if idx < len(decs) else None

            fx = {
                "score": scores[0] if len(scores) > 0 else None,
                "D": dec_at(0),
                "E": dec_at(1),
                "C": dec_at(2)
            }
            tu = {
                "score": scores[1] if len(scores) > 1 else None,
                "D": dec_at(3),
                "E": dec_at(4),
                "C": dec_at(5)
            }
            tr = {
                "score": scores[2] if len(scores) > 2 else None,
                "D": dec_at(6),
                "E": dec_at(7),
                "C": dec_at(8)
            }
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

def main():
    html = fetch_html(URL)
    soup = BeautifulSoup(html, "html.parser")
    comp_title = find_competition_title(soup)

    div = get_active_mangkamp_div(soup)
    if not div:
        raise SystemExit("No active competition div found")

    tokens = tokenize_div(div)
    teams = parse_tokens(tokens)

    output = [{
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "competition": comp_title,
        "teams": teams
    }]

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsed {len(teams)} teams for competition '{comp_title}'")

if __name__ == "__main__":
    main()
