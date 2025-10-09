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

def parse_team_block(block_text, rank):
    """Parse one team's Mångkamp line into structured JSON"""

    # Find rank, start position, and team name
    match = re.match(r"^(\d{1,2})(\d{1,2})([A-Za-zÅÄÖåäö0-9\s\-]+?)(?=\d+,\d{3})", block_text)
    if not match:
        return None

    start_pos = int(match.group(2))
    name = match.group(3).strip()

    # Extract all numeric scores with 3 decimals
    score_matches = re.findall(r"\d+,\d{3}", block_text)
    scores = [float(s.replace(",", ".")) for s in score_matches]

    # Extract D/E/C pattern values
    dec_matches = re.findall(r"D:\s*([\d,]+)|E:\s*([\d,]+)|C:\s*([\d,]+)", block_text)
    dec_values = [float(v.replace(",", ".")) for tup in dec_matches for v in tup if v]

    def dec(i):
        return dec_values[i] if i < len(dec_values) else None

    fx = {"score": scores[0] if len(scores) > 0 else None, "D": dec(0), "E": dec(1), "C": dec(2)}
    tu = {"score": scores[1] if len(scores) > 1 else None, "D": dec(3), "E": dec(4), "C": dec(5)}
    tr = {"score": scores[2] if len(scores) > 2 else None, "D": dec(6), "E": dec(7), "C": dec(8)}

    total = scores[3] if len(scores) > 3 else None
    gap = scores[4] if (len(scores) > 4 and rank != 1) else 0.0

    return {
        "rank": rank,
        "start_position": start_pos,
        "name": name,
        "fx": fx,
        "tu": tu,
        "tr": tr,
        "total": total,
        "gap": gap
    }

teams = []
rank = 1

if container:
    text = container.get_text(" ", strip=True)

    # Find Mångkamp section (before FX/TU/TR headings)
    main_block_match = re.search(r"Pl#Namn.*?(?=Pl#Namn|$)", text)
    if main_block_match:
        block = main_block_match.group(0)

        # Split into potential team chunks
        chunks = re.split(r"(?=\d{1,2}\d{1,2}[A-ZÅÄÖa-zåäö])", block)

        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) < 15:
                continue
            parsed = parse_team_block(chunk, rank)
            if parsed:
                teams.append(parsed)
                rank += 1

# Trim to top 10 teams
teams = teams[:10]

output = {
    "last_updated": datetime.utcnow().isoformat() + "Z",
    "competition": "Mångkamp",
    "teams": teams
}

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ Parsed {len(teams)} teams successfully.")
