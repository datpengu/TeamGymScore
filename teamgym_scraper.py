import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

URL = "https://live.sporteventsystems.se/Score/?country=swe"
BASE_URL = "https://live.sporteventsystems.se"

response = requests.get(URL)
soup = BeautifulSoup(response.text, "html.parser")

competitions = []

# ✅ Find the "Teamgym" section header
teamgym_header = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string="Teamgym")

if teamgym_header:
    # The rows after the Teamgym header contain competitions
    for row in teamgym_header.find_all_next("div", class_="row"):
        cols = row.find_all("div", class_="fs-6")
        if not cols:
            continue
        
        # Extract details if link exists
        link = row.find("a", href=True)
        if link and "WebScore" in link["href"]:
            date_from = cols[0].get_text(strip=True) if len(cols) > 0 else ""
            date_to = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            place = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            title = link.get_text(strip=True)
            href = link["href"]
            full_url = href if href.startswith("http") else BASE_URL + href

            competitions.append({
                "title": title,
                "url": full_url,
                "date_from": date_from,
                "date_to": date_to,
                "place": place
            })

# Save the results to JSON
output = {
    "last_updated": datetime.utcnow().isoformat() + "Z",
    "competitions": competitions
}

with open("competitions.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ Saved {len(competitions)} competitions to competitions.json")
