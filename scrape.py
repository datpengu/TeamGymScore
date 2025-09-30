import requests
from bs4 import BeautifulSoup
import json

URL = "https://live.sporteventsystems.se/Score/WebScore/3303?f=7545&country=swe&year=-1"
response = requests.get(URL)
soup = BeautifulSoup(response.text, "html.parser")

container = soup.find("div", id="TabContent")
results = []

if container:
    # Each competitor is a div with class "row" (adjust if needed)
    competitors = container.find_all("div", class_="row")  

    for comp in competitors:
        try:
            rank = comp.find("div", class_="pl").get_text(strip=True)
            name = comp.find("div", class_="name").get_text(strip=True)
            # Extract FX, TU, TR scores
            fx = comp.find("div", class_="FX").get_text(strip=True)
            tu = comp.find("div", class_="TU").get_text(strip=True)
            tr = comp.find("div", class_="TR").get_text(strip=True)
            total = comp.find("div", class_="total").get_text(strip=True)

            # Optional: extract D, E, C per event if needed
            # This may require more parsing of the nested text

            results.append({
                "rank": rank,
                "name": name,
                "fx": fx,
                "tu": tu,
                "tr": tr,
                "total": total
            })
        except AttributeError:
            continue  # skip divs that don't match

# Write JSON
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(json.dumps(results, ensure_ascii=False, indent=2))
