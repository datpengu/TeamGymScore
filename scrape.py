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
    text = text.replace(",", ".")
    score_match = re.search(r"\d+\.\d+", text)
    score = float(score_match.group()) if score_match else None
    D = float(re.search(r"D:\s*([\d.]+)", text).group(1)) if re.search(r"D:\s*([\d.]+)", text) else None
    E = float(re.search(r"E:\s*([\d.]+)", text).group(1)) if re.search(r"E:\s*([\d.]+)", text) else None
    C = float(re.search(r"C:\s*([\d.]+)", text).group(1)) if re.search(r"C:\s*([\d.]+)", text) else None
    return {"score": score, "D": D, "E": E, "C": C}

if container:
    lines = [div.get_text(strip=True) for div in container.find_all("div") if div.get_text(strip=True)]
    
    # Remove header lines
    header_keywords = ["Pl", "Namn", "Fristående", "Tumbling", "Trampett", "Total", "Gap"]
    while lines and any(k in lines[0] for k in header_keywords):
        lines.pop(0)

    rank_counter = 1
    i = 0
    while i < len(lines):
        try:
            line = lines[i]

            # Start position is first number
            start_pos_match = re.match(r"(\d+)", line)
            if start_pos_match:
                start_pos = int(start_pos_match.group(1))
                name = line[start_pos_match.end():].strip()
            else:
                start_pos = None
                name = line.strip()

            # Skip lines that are clearly not team names
            if not name or name.startswith(","):
                # Find next non-score line
                for j in range(i+1, len(lines)):
                    if not re.match(r"[\d.,]+", lines[j]):
                        name = lines[j].strip()
                        break

            fx = parse_score(lines[i+1]) if i+1 < len(lines) else {"score": None, "D": None, "E": None, "C": None}
            tu = parse_score(lines[i+2]) if i+2 < len(lines) else {"score": None, "D": None, "E": None, "C": None}
            tr = parse_score(lines[i+3]) if i+3 < len(lines) else {"score": None, "D": None, "E": None, "C": None}

            total = None
            gap = None
            for j in range(i+4, i+6):
                if j < len(lines):
                    try:
                        val = float(lines[j].replace(",", "."))
                        if total is None:
                            total = val
                        else:
                            gap = val
                    except:
                        continue

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

            i += 5
            rank_counter += 1

        except Exception as e:
            print(f"⚠️ Skipped lines {i}-{i+4} due to error: {e}")
            i += 1

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ Parsed {len(results)} teams.")
