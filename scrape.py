import requests
from bs4 import BeautifulSoup
import json

# Use your raw HTML file URL
URL = "https://raw.githubusercontent.com/datpengu/TeamGymScore/refs/heads/main/site.html"
response = requests.get(URL)
soup = BeautifulSoup(response.text, "html.parser")

container = soup.find("div", id="TabContent")
results = []

if container:
    children = container.find_all("div", recursive=False)
    i = 0
    while i < len(children):
        try:
            rank = children[i].get_text(strip=True)
            name = children[i+1].get_text(strip=True)
            club = children[i+2].get_text(strip=True)

            # FX, TU, TR scores
            fx = children[i+3].get_text(strip=True)
            tu = children[i+4].get_text(strip=True)
            tr = children[i+5].get_text(strip=True)

            # Total score
            total = children[i+6].get_text(strip=True)

            results.append({
                "rank": rank,
                "name": name,
                "club": club,
                "fx": fx,
                "tu": tu,
                "tr": tr,
                "total": total
            })

            # Move to the next competitor block
            i += 7

        except IndexError:
            break  # end of container

# Save JSON
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(json.dumps(results, ensure_ascii=False, indent=2))
