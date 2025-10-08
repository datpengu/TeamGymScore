import requests
from bs4 import BeautifulSoup
import re
import json

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"

def parse_score_line(line):
    """Extract score and optional D/E/C from a line like '12,100D: 2,000E: 8,100C: 2,000'."""
    line = line.replace(",", ".")
    # main score
    score_m = re.search(r"(\d+\.\d+)", line)
    score = float(score_m.group(1)) if score_m else None
    D = float(re.search(r"D:\s*([\d.]+)", line).group(1)) if re.search(r"D:\s*([\d.]+)", line) else None
    E = float(re.search(r"E:\s*([\d.]+)", line).group(1)) if re.search(r"E:\s*([\d.]+)", line) else None
    C = float(re.search(r"C:\s*([\d.]+)", line).group(1)) if re.search(r"C:\s*([\d.]+)", line) else None
    return {"score": score, "D": D, "E": E, "C": C}

def is_total_line(line):
    """Detect if this line is probably the team total (a float not part of D/E/C)."""
    s = line.replace(",", ".").strip()
    return re.fullmatch(r"\d+\.\d+", s) is not None and not re.search(r"[DEC]:", line)

def get_lines():
    response = requests.get(URL)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", id="TabContent")
    if not container:
        raise RuntimeError("Could not find TabContent container in HTML")
    lines = [div.get_text(strip=True) for div in container.find_all("div", recursive=True) if div.get_text(strip=True)]
    return lines

def parse_blocks(lines):
    results = []
    i = 0
    rank = 1
    while i < len(lines):
        line = lines[i].strip()
        # Skip header or weird
        if any(h in line for h in ["Pl", "Namn", "Fristående", "Tumbling", "Trampett", "Total", "Gap"]) or not line:
            i += 1
            continue

        # Extract prefix for rank/start position
        prefix_match = re.match(r"(\d+)(\d+)([A-Za-z].*)", line)
        if not prefix_match:
            i += 1
            continue

        rank_prefix = prefix_match.group(1)
        start_pos = int(prefix_match.group(2))
        name = prefix_match.group(3).strip()

        fx = tu = tr = None
        total = None
        gap = None

        # Look at next few lines for fx, tu, tr, total, gap
        for j in range(1, 7):
            if i + j >= len(lines):
                break
            ln = lines[i + j].strip()
            if is_total_line(ln):
                total = float(ln.replace(",", "."))
                # gap is next line if exists and numeric
                if i + j + 1 < len(lines):
                    nm = lines[i + j + 1].replace(",", ".").strip()
                    if re.fullmatch(r"\d+\.\d+", nm):
                        gap = float(nm)
                break
            else:
                parsed = parse_score_line(ln)
                if fx is None:
                    fx = parsed
                elif tu is None:
                    tu = parsed
                elif tr is None:
                    tr = parsed

        results.append({
            "rank": rank,
            "start_position": start_pos,
            "name": name,
            "fx": fx or {"score": None, "D": None, "E": None, "C": None},
            "tu": tu or {"score": None, "D": None, "E": None, "C": None},
            "tr": tr or {"score": None, "D": None, "E": None, "C": None},
            "total": total,
            "gap": gap if rank != 1 else None
        })

        # Move forward
        if total is not None:
            for j in range(1, 7):
                if i + j < len(lines) and is_total_line(lines[i + j]):
                    i = i + j + 2
                    break
        else:
            i += 1

        rank += 1

    return results


if __name__ == "__main__":
    lines = get_lines()
    results = parse_blocks(lines)
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ Parsed {len(results)} teams successfully.")
