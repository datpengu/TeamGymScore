import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://raw.githubusercontent.com/datpengu/TeamGymScore/refs/heads/main/site.html"
response = requests.get(URL)
soup = BeautifulSoup(response.text, "html.parser")

container = soup.find("div", id="TabContent")
results = []

def parse_score(text):
    """Parse score with D/E/C into dict"""
    text = text.replace(",", ".")
    score_match = re.match(r"[\d.]+", text)
    score = float(score_match.group()) if score_match else None
    D = float(re.search(r"D:\s*([\d.]+)", text).group(1)) if re.search(r"D:\s*([\d.]+)", text) else None
    E = float(re.search(r"E:\s*([\d.]+)", text).group(1)) if re.search(r"E:\s*([\d.]+)", text) else None
    C = float(re.search(r"C:\s*([\d.]+)", text).group(1)) if re.search(r"C:\s*([\d.]+)", text) else None
    return {"score": score, "D": D, "E": E, "C": C}

if container:
    # Get all text lines inside TabContent, skip empty
    lines = [div.get_text(strip=True) for div in container.find_all("div", recursive=True) if div.get_text(strip=True)]

    # Skip header line
    header_keywords = ["Pl", "Namn", "Fristående", "Tumbling", "Trampett", "Total", "Gap"]
    while lines and any(k in lines[0] for k in header_keywords):
        print(f"Skipping header line: {lines[0]}")
        lines.pop(0)

    rank_counter = 1
    i = 0
    while i < len(lines):
        try:
            # Extract rank + start position from start of line
            line = lines[i]
            rank_len = len(str(rank_counter))
            rank = rank_counter
            start_pos = int(line[rank_len:rank_len+1])  # assumes start pos is 1 digit; adjust if necessary
            name = line[rank_len+1:].strip()

            fx = parse_score(lines[i+1])
            tu = parse_score(lines[i+2])
            tr = parse_score(lines[i+3])

            total_text = lines[i+4].replace(",", ".")
            total = float(total_text) if re.match(r"^[\d.]+$", total_text) else None

            gap_text = lines[i+5].replace(",", ".")
            gap = float(gap_text) if re.match(r"^[\d.]+$", gap_text) else None

            results.append({
                "rank": rank,
                "start_position": start_pos,
                "name": name,
                "fx": fx,
                "tu": tu,
                "tr": tr,
                "total": total,
                "gap": gap
            })

            i += 6
            rank_counter += 1

        except Exception as e:
            print(f"⚠️ Skipped lines {i}-{i+5} due to error: {e}")
            i += 1

# Save JSON
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ Parsed {len(results)} competitors.")
