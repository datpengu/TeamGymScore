import requests
from bs4 import BeautifulSoup
import re
import json

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"

def get_lines():
    """Fetch all text lines from the scoreboard HTML."""
    response = requests.get(URL)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", id="TabContent")
    if not container:
        raise RuntimeError("❌ Could not find TabContent in HTML")
    return [div.get_text(strip=True) for div in container.find_all("div") if div.get_text(strip=True)]

def extract_score_segments(text):
    """
    Extract all scores with exactly 3 decimal places.
    Example: 12.550, 11.650, etc.
    """
    text = text.replace(",", ".")
    return re.findall(r"\d+\.\d{3}", text)

def parse_team_line(line):
    """
    Parse a team line like '19Sandvikens GA' -> (rank=1, start_pos=9, name='Sandvikens GA')
    or '117Team A' -> (rank=11, start_pos=7, name='Team A')
    """
    match = re.match(r"(\d{1,2})(\d{1,2})([A-Za-zÅÄÖåäö].+)", line)
    if not match:
        return None, None, None
    rank = int(match.group(1))
    start_pos = int(match.group(2))
    name = match.group(3).strip()
    return rank, start_pos, name

def parse_blocks(lines):
    results = []
    i = 0
    rank_counter = 1

    while i < len(lines):
        line = lines[i].strip()

        # Skip headers or empty lines
        if any(h in line for h in ["Pl", "Namn", "Fristående", "Tumbling", "Trampett", "Total", "Gap"]) or not line:
            i += 1
            continue

        rank, start_pos, name = parse_team_line(line)
        if not name:
            i += 1
            continue

        fx = tu = tr = total = gap = None
        j = i + 1
        scores_found = []

        # Collect following lines to extract up to 5 scores (.XXX pattern)
        while j < len(lines) and len(scores_found) < 5:
            segs = extract_score_segments(lines[j])
            for s in segs:
                scores_found.append(float(s))
            j += 1

        if len(scores_found) >= 3:
            fx = scores_found[0]
            tu = scores_found[1]
            tr = scores_found[2]
        if len(scores_found) >= 4:
            total = scores_found[3]
        if len(scores_found) >= 5:
            gap = scores_found[4]

        results.append({
            "rank": rank_counter,
            "start_position": start_pos,
            "name": name,
            "fx": fx,
            "tu": tu,
            "tr": tr,
            "total": total,
            "gap": gap if rank_counter != 1 else None
        })

        rank_counter += 1
        i = j

    return results


if __name__ == "__main__":
    lines = get_lines()
    results = parse_blocks(lines)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsed {len(results)} teams successfully.")
