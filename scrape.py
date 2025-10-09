import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"

def fetch_mangkamp():
    resp = requests.get(URL)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    container = soup.find("div", id="TabContent")
    if not container:
        raise RuntimeError("No TabContent found")

    # Mångkamp tab has both 'tab-pane' and 'show active'
    mangkamp = container.find("div", class_="tab-pane fade show active")
    if not mangkamp:
        raise RuntimeError("Mångkamp tab not found")

    lines = [div.get_text(strip=True) for div in mangkamp.find_all("div", recursive=True) if div.get_text(strip=True)]
    return lines


def parse_team_line(line):
    m = re.match(r"(\d{1,2})(\d{1,2})([A-Za-zÅÄÖåäö].*)", line)
    if not m:
        return None, None, None
    return int(m.group(1)), int(m.group(2)), m.group(3).strip()


def parse_score_line(line):
    text = line.replace(",", ".")
    score_match = re.search(r"(\d+\.\d{3})", text)
    score = float(score_match.group(1)) if score_match else None

    D = E = C = None
    for label in ["D", "E", "C"]:
        match = re.search(rf"{label}:\s*([\d\.]+)", text)
        if match:
            val = float(match.group(1))
            if label == "D":
                D = val
            elif label == "E":
                E = val
            elif label == "C":
                C = val

    return {"score": score, "D": D, "E": E, "C": C}


def parse_table(lines):
    results = []
    i = 0
    rank_counter = 1

    while i < len(lines):
        line = lines[i]

        # Skip headers
        if any(h in line for h in ["Pl", "Namn", "Fristående", "Tumbling", "Trampett", "Total", "Gap"]):
            i += 1
            continue

        rank, start_pos, name = parse_team_line(line)
        if not name:
            i += 1
            continue

        fx = parse_score_line(lines[i + 1]) if i + 1 < len(lines) else None
        tu = parse_score_line(lines[i + 2]) if i + 2 < len(lines) else None
        tr = parse_score_line(lines[i + 3]) if i + 3 < len(lines) else None

        total = None
        if i + 4 < len(lines):
            total_match = re.search(r"(\d+\.\d{3})", lines[i + 4].replace(",", "."))
            if total_match:
                total = float(total_match.group(1))

        gap = None
        if rank_counter > 1 and i + 5 < len(lines):
            gap_match = re.search(r"(\d+\.\d{3})", lines[i + 5].replace(",", "."))
            if gap_match:
                gap = float(gap_match.group(1))

        results.append({
            "rank": rank_counter,
            "start_position": start_pos,
            "name": name,
            "fx": fx,
            "tu": tu,
            "tr": tr,
            "total": total,
            "gap": gap if rank_counter > 1 else None
        })

        rank_counter += 1
        i += 6

    return results


if __name__ == "__main__":
    lines = fetch_mangkamp()
    results = parse_table(lines)

    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "competition": "Mångkamp",
        "teams": results
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsed {len(results)} teams from Mångkamp.")
