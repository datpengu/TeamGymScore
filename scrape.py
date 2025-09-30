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
    Returns: {'score': 12.1, 'D': 2.0, 'E': 8.1, 'C': 2.0}
    """
    # Replace comma with dot for floats
    text = text.replace(",", ".")
    # Extract main score
    score_match = re.match(r"[\d.]+", text)
    score = float(score_match.group()) if score_match else None
    # Extract D, E, C
    D = float(re.search(r"D:\s*([\d.]+)", text).group(1)) if re.search(r"D:\s*([\d.]+)", text) else None
    E = float(re.search(r"E:\s*([\d.]+)", text).group(1)) if re.search(r"E:\s*([\d.]+)", text) else None
    C = float(re.search(r"C:\s*([\d.]+)", text).group(1)) if re.search(r"C:\s*([\d.]+)", text) else None
    return {"score": score, "D": D, "E": E, "C": C}

if container:
    divs = container.find_all("div", recursive=False)
    i = 0
    while i < len(divs):
        text = divs[i].get_text(strip=True)
        if text.isdigit():  # rank
            rank = text
            name = divs[i+1].get_text(strip=True)
            club = divs[i+2].get_text(strip=True)
            
            fx = parse_score(divs[i+3].get_text(strip=True))
            tu = parse_score(divs[i+4].get_text(strip=True))
            tr = parse_score(divs[i+5].get_text(strip=True))
            
            total_text = divs[i+6].get_text(strip=True).replace(",", ".")
            total = float(total_text) if total_text else None
            
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
        else:
            i += 1

# Save JSON
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(json.dumps(results, ensure_ascii=False, indent=2))
