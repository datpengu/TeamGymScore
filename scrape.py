import requests
from bs4 import BeautifulSoup
import re
import json

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"

def get_lines():
    response = requests.get(URL)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", id="TabContent")
    if not container:
        raise RuntimeError("❌ Could not find TabContent in HTML")
    return [div.get_text(strip=True) for div in container.find_all("div") if div.get_text(strip=True)]

def parse_score_line(line):
    """Extract score, D, E, and C values from an apparatus line."""
    line = line.replace(",", ".")
    score_match = re.search(r"(\d+\.\d{3})", line)
    score = float(score_match.group(1)) if score_match else None

    D = re.search(r"D:\s*([\d.]+)", line)
    E = re.search(r"E:\s*([\d.]+)", line)
    C = re.search(r"C:\s*([\d.]+)", line)

    return {
        "score": score,
        "D": float(D.group(1)) if D else None,
        "E": float(E.group(1)) if E else None,
        "C": float(C.group(1)) if C else None
    }

def parse_team_line(line):
    """Extract rank, start position, and name from a team header line."""
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

        # Skip headers or non-team lines
        if any(h in line for h in ["Pl", "Namn", "Fristående", "Tumbling", "Trampett", "Total", "Gap"]) or not line:
            i += 1
            continue

        rank, start_pos, name = parse_team_line(line)
        if not name:
            i += 1
            continue

        # Parse next 3 lines as apparatus scores
        fx = tu = tr = None
        total = gap = None

        if i + 1 < len(lines):
            fx = parse_score_line(lines[i + 1])
        if i + 2 < len(lines):
            tu = parse_score_line(lines[i + 2])
        if i + 3 < len(lines):
            tr = parse_score_line(lines[i + 3])

        # Next line: total
        if i + 4 < len(lines):
            total_match = re.search(r"(\d+\.\d{3})", lines[i + 4].replace(",", "."))
            total = float(total_match.group(1)) if total_match else None

        # Optional gap line
        if i + 5 < len(lines):
            gap_match = re.search(r"(\d+\.\d{3})", lines[i + 5].replace(",", "."))
            gap = float(gap_match.group(1)) if gap_match else None

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
        i += 6  # Skip to next team block

    return results


if __name__ == "__main__":
    lines = get_lines()
    results = parse_blocks(lines)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsed {len(results)} teams successfully.")
