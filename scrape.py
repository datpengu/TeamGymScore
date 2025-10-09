# scrape.py
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

URL = "https://live.sporteventsystems.se/Score/WebScore/3304?f=7543&country=swe&year=-1"
TOP_N = 8  # change if you want more than top 10

def get_active_mangkamp_div(soup):
    # Prefer the div that has "show active" in its class (the active tab)
    div = soup.find("div", class_=lambda c: c and "show active" in c)
    if div:
        return div
    # fallback: first tab-pane
    div = soup.find("div", class_=lambda c: c and "tab-pane" in c)
    return div

def tokenize_div(div):
    """
    Return a cleaned list of tokens (strings) from the Mångkamp div,
    preserving lines like 'D: 2,000' and numeric scores '11,650'.
    """
    raw = list(div.stripped_strings)
    # Remove headings and repeated labels that are not useful (but keep 'D:' tokens)
    skip_exact = {
        "Pl", "#", "Namn", "Fristående", "Tumbling", "Trampett",
        "Total", "Gap", "FX", "TU", "TR", "D", "E", "C",  # single-letter headings (without colon)
        "Senaste poäng:", "Resultat från Sport Event Systems", "Last Update:"
    }
    tokens = [t for t in raw if t not in skip_exact]
    return tokens

def is_rank_token(tok):
    return re.fullmatch(r"\d{1,2}", tok) is not None

def is_startpos_token(tok):
    return re.fullmatch(r"\d{1,3}", tok) is not None

def is_score_token(tok):
    # matches numbers like 12,100 or 0,350
    return re.fullmatch(r"\d+,\d{3}", tok) is not None

def is_dec_token(tok):
    # matches "D: 2,000" or "E: 7,250" or "C: 2,000"
    return re.fullmatch(r"[DEC]:\s*\d+,\d{3}", tok) is not None

def parse_tokens(tokens):
    teams = []
    i = 0
    while i < len(tokens):
        # find a team start: rank, startpos, name
        if i + 2 < len(tokens) and is_rank_token(tokens[i]) and is_startpos_token(tokens[i+1]):
            rank_token = tokens[i]
            startpos_token = tokens[i+1]
            name_token = tokens[i+2]

            # sanity: name_token should not be a score
            if is_score_token(name_token) or is_dec_token(name_token):
                i += 1
                continue

            rank = int(rank_token)
            start_position = int(startpos_token)
            name = name_token.strip()

            # advance pointer to just after name
            j = i + 3

            scores = []   # fx, tu, tr, total, gap (in that order, if present)
            decs = []     # sequence of D/E/C numeric values in the order they appear

            # Walk forward collecting score tokens and D/E/C tokens until we've
            # seen at least fx, tu, tr, total (or until next team starts).
            while j < len(tokens):
                tok = tokens[j]

                # stop early if next team seems to start here (rank + startpos)
                if j + 1 < len(tokens) and is_rank_token(tokens[j]) and is_startpos_token(tokens[j+1]):
                    break

                if is_score_token(tok):
                    scores.append(float(tok.replace(",", ".")))
                    j += 1
                    continue

                if is_dec_token(tok):
                    # extract numeric part
                    m = re.search(r"(\d+,\d{3})$", tok)
                    if m:
                        decs.append(float(m.group(1).replace(",", ".")))
                    j += 1
                    continue

                # special case: sometimes tokens separate the colon and value
                # e.g. "D:" then "2,000" -> handle that
                if tok in ("D:", "E:", "C:") and j + 1 < len(tokens) and is_score_token(tokens[j+1]):
                    decs.append(float(tokens[j+1].replace(",", ".")))
                    j += 2
                    continue

                # otherwise skip headings like 'FX','TU','TR' or stray tokens
                j += 1

                # guard: prevent infinite loop (shouldn't happen)
                if j - i > 200:
                    break

            # Map decs to apparatus: first 3 => fx D/E/C, next 3 => tu D/E/C, next 3 => tr D/E/C
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
            gap = scores[4] if len(scores) > 4 else None

            # Per your request: rank 1 should have gap = 0.0
            if rank == 1:
                gap = 0.0

            team = {
                "rank": rank,
                "start_position": start_position,
                "name": name,
                "fx": fx,
                "tu": tu,
                "tr": tr,
                "total": total,
                "gap": gap
            }
            teams.append(team)

            # move i to j (next unread token)
            i = j
        else:
            i += 1
    return teams

def main():
    resp = requests.get(URL, timeout=15)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    mangkamp_div = get_active_mangkamp_div(soup)
    if not mangkamp_div:
        raise SystemExit("❌ Could not find Mångkamp/active tab on page")

    tokens = tokenize_div(mangkamp_div)
    teams = parse_tokens(tokens)

    # keep only top N
    teams = teams[:TOP_N]

    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "competition": "Mångkamp",
        "teams": teams
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsed {len(teams)} teams and wrote results.json")

if __name__ == "__main__":
    main()
