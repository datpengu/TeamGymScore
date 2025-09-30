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
    """Parse a line containing a score with optional D/E/C"""
    text = text.replace(",", ".")
    score_match = re.search(r"[\d]+\.[\d]{3}", text)
    score = float(score_match.group()) if score_match else None
    D = float(re.search(r"D:\s*([\d.]+)", text).group(1)) if re.search(r"D:\s*([\d.]+)", text) else None
    E = float(re.search(r"E:\s*([\d.]+)", text).group(1)) if re.search(r"E:\s*([\d.]+)", text) else None
    C = float(re.search(r"C:\s*([\d.]+)", text).group(1)) if re.search(r"C:\s*([\d.]+)", text) else None
    return {"score": score, "D": D, "E": E, "C": C}

if container:
    # Get all non-empty div texts
    lines = [div.get_text(strip=True) for div in container.find_all("div", recursive=True) if div.get_text(strip=True)]

    # Remove header lines
    header_keywords = ["Pl", "Namn", "Fristående", "Tumbling", "Trampett", "Total", "Gap"]
    while lines and any(k in lines[0] for k in header_keywords):
        lines.pop(0)

    rank_counter = 1
    i = 0
    while i < len(lines):
        try:
            line = lines[i]

            # Rank is sequential
            start_pos_match = re.match(r"(\d+)", line)
            if not start_pos_match:
                i += 1
                continue
            start_pos = int(start_pos_match.group(1))

            # Team name is everything after start position digits up to next score line
            name = line[start_pos_match.end():].strip()
            if not name:
                # fallback if empty, pick next non-score line
                for j in range(i+1, len(lines)):
                    if re.match(r"^\D", lines[j]):
                        name = lines[j].strip()
                        break

            # Parse fx, tu, tr lines
            fx = parse_score(lines[i+1])
            tu = parse_score(lines[i+2])
            tr = parse_score(lines[i+3])

            # Total: first line with three decimals
            total = None
            gap = None
            for j in range(i+4, i+6):
                if j < len(lines) and re.match(r"^\d+\.\d{3}$", lines[j].replace(",", ".")):
                    total = float(lines[j].replace(",", "."))
                elif j < len(lines) and re.match(r"^\d+\.\d{3}$", lines[j].replace(",", ".")) is None:
                    try:
                        gap = float(lines[j].replace(",", "."))
                    except:
                        gap = None

            results.append({
                "rank": rank_counter,
                "start_position": start_pos,
                "name": name,
                "fx": fx,
                "tu": tu,
                "tr": tr,
                "total": total,
                "gap": gap
            })

            # Increment counters
            i += 5
            rank_counter += 1

        except Exception as e:
            print(f"⚠️ Skipped lines {i}-{i+4} due to error: {e}")
            i += 1

# Save clean JSON
with open("clean_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ Parsed {len(results)} teams.")
