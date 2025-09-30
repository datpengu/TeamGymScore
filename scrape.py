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
    """
    Parses a string like '12,100D: 2,000E: 8,100C: 2,000' into a dict.
    """
    text = text.replace(",", ".")
    score_match = re.match(r"[\d.]+", text)
    score = float(score_match.group()) if score_match else None
    D = float(re.search(r"D:\s*([\d.]+)", text).group(1)) if re.search(r"D:\s*([\d.]+)", text) else None
    E = float(re.search(r"E:\s*([\d.]+)", text).group(1)) if re.search(r"E:\s*([\d.]+)", text) else None
    C = float(re.search(r"C:\s*([\d.]+)", text).group(1)) if re.search(r"C:\s*([\d.]+)", text) else None
    return {"score": score, "D": D, "E": E, "C": C}

if container:
    lines = [div.get_text(strip=True) for div in container.find_all("div", recursive=True) if div.get_text(strip=True)]
    i = 0
    while i < len(lines):
        if re.match(r"^\d+", lines[i]):
            try:
                rank = lines[i]
                name = lines[i+1]
                club = lines[i+2]

                fx = parse_score(lines[i+3])
                tu = parse_score(lines[i+4])
                tr = parse_score(lines[i+5])

                total_text = lines[i+6].replace(",", ".")
                total = float(total_text) if re.match(r"^[\d.]+$", total_text) else None

                results.append({
                    "rank": rank,
                    "name": name,
                    "club": club,
                    "fx": fx,
                    "tu": tu,
                    "tr": tr,
                    "total": total
                })
                i += 7
            except IndexError:
                print(f"⚠️ Skipped incomplete competitor block starting at line {i}: {lines[i:i+7]}")
                break
            except Exception as e:
                print(f"⚠️ Error parsing competitor block starting at line {i}: {lines[i:i+7]} — {e}")
                i += 7
        else:
            # log skipped lines not starting with rank
            print(f"ℹ️ Skipped line {i} (not a rank): {lines[i]}")
            i += 1

# Save JSON
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ Parsed {len(results)} competitors.")
