import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"

response = requests.get(URL)
response.encoding = "utf-8"
soup = BeautifulSoup(response.text, "html.parser")

container = soup.find("div", id="TabContent")

def parse_team_block(text_block, rank_counter):
    """
    Parse a single team's full line including:
    - Rank, start position
    - Name
    - D/E/C and apparatus scores
    - Total and gap
    """

    # Match rank, start_position, and name until first 3-decimal score
    match = re.search(r"^(\d{1,2})(\d{1,2})(.+?)(?=\d+,\d{3})", text_block)
    if not match:
        return None

    rank = rank_counter
    start_pos = int(match.group(2))
    name = match.group(3).strip()

    # Extract all numeric scores (11,650 etc)
    score_matches = re.findall(r"\d+,\d{3}", text_block)
    scores = [float(s.replace(",", ".")) for s in score_matches]

    # Extract all D, E, C values in order
    dec_values = re.findall(r"[DEC]:\s*([\d,]+)", text_block)
    dec_values = [float(v.replace(",", ".")) for v in dec_values]

    def get_dec(index):
        return dec_values[index] if index < len(dec_values) else None

    fx = {
        "score": scores[0] if len(scores) > 0 else None,
        "D": get_dec(0),
        "E": get_dec(1),
        "C": get_dec(2),
    }
    tu = {
        "score": scores[1] if len(scores) > 1 else None,
        "D": get_dec(3),
        "E": get_dec(4),
        "C": get_dec(5),
    }
    tr = {
        "score": scores[2] if len(scores) > 2 else None,
        "D": get_dec(6),
        "E": get_dec(7),
        "C": get_dec(8),
    }

    total = scores[3] if len(scores) > 3 else None
    gap = scores[4] if len(scores) > 4 else None

    return {
        "rank": rank,
        "start_position": start_pos,
        "name": name,
        "fx": fx,
        "tu": tu,
        "tr": tr,
        "total": total,
        "gap": gap,
    }

# ---- Extract all text lines ----
lines = [div.get_text(" ", strip=True) for div in container.find_all("div") if div.get_text(strip=True)]

# Keep only lines that look like full team result rows
team_lines = [l for l in lines if re.match(r"^\d{1,2}\d{1,2}.*\d+,\d{3}", l)]

teams = []
rank_counter = 1
for line in team_lines:
    parsed = parse_team_block(line, rank_counter)
    if parsed:
        teams.append(parsed)
        rank_counter += 1

output = {
    "last_updated": datetime.utcnow().isoformat() + "Z",
    "competition": "Mångkamp",
    "teams": teams
}

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ Parsed {len(teams)} teams successfully.")
