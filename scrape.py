import requests
from bs4 import BeautifulSoup
import json

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"

response = requests.get(URL)
soup = BeautifulSoup(response.text, "html.parser")

table = soup.find("table")
results = []

if table:
    rows = table.find_all("tr")[1:]  # skip header
    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) >= 8:  # make sure row has enough columns
            results.append({
                "rank": cols[0],
                "name": cols[1],
                "club": cols[2],
                "execution": cols[3],
                "difficulty": cols[4],
                "composition": cols[5],
                "penalties": cols[6],
                "total": cols[7],
                "note": cols[8] if len(cols) > 8 else ""
            })

# Write to results.json
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
