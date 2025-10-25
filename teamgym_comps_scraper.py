import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

BASE_URL = "https://live.sporteventsystems.se"

def fetch_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text

def parse_score_tokens(tokens):
    teams = []
    i = 0
    while i < len(tokens):
        # detect start of a team: rank + startpos + name
        if (
            i + 2 < len(tokens)
            and re.fullmatch(r"\d{1,2}", tokens[i])
            and re.fullmatch(r"\d{1,2}", tokens[i + 1])
        ):
            rank = int(tokens[i])
            start_position = int(tokens[i + 1])
            name = tokens[i + 2]
            j = i + 3
            scores = []
            decs = []
            hj = []
            while j < len(tokens):
                tok = tokens[j]
                # stop if we hit the next rank
                if (
                    j + 1 < len(tokens)
                    and re.fullmatch(r"\d{1,2}", tokens[j])
                    and re.fullmatch(r"\d{1,2}", tokens[j + 1])
                ):
                    break
                # capture scores with 3 decimals
                if re.fullmatch(r"\d+,\d{3}", tok):
                    scores.append(float(tok.replace(",", ".")))
                    j += 1
                    continue
                # capture D/E/C/HJ values
                m = re.search(r"(D|E|C|HJ)[\s:-]*([\d,]+)", tok)
                if m:
                    val = float(m.group(2).replace(",", "."))
                    if m.group(1) == "HJ":
                        hj.append(val)
                    else:
                        decs.append(val)
                    j += 1
                    continue
                j += 1
                if j - i > 200:
                    break

            def safe(lst, idx):
                return lst[idx] if idx < len(lst) else None

            fx = {"score": safe(scores, 0), "D": safe(decs, 0), "E": safe(decs, 1), "C": safe(decs, 2), "HJ": safe(hj, 0)}
            tu = {"score": safe(scores, 1), "D": safe(decs, 3), "E": safe(decs, 4), "C": safe(decs, 5), "HJ": safe(hj, 1)}
            tr = {"score": safe(scores, 2), "D": safe(decs, 6), "E": safe(decs, 7), "C": safe(decs, 8), "HJ": safe(hj, 2)}
            total = safe(scores, 3)
            gap = 0.0 if rank == 1 else safe(scores, 4)

            teams.append({
                "rank": rank,
                "start_position": start_position,
                "name": name.strip(),
                "fx": fx,
                "tu": tu,
                "tr": tr,
                "total": total,
                "gap": gap
            })
            i = j
        else:
            i += 1
    return teams

def parse_class_page(url):
    """Parse a single class page (Mångkamp or FX/TU/TR)."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # Prefer active tab with scores
    div = soup.select_one("div.tab-pane.active.show") or soup.select_one("div.tab-pane")
    if not div:
        print(f"   ⚠️ No active score tab found for {url}")
        return []

    tokens = [s for s in div.stripped_strings]
    teams = parse_score_tokens(tokens)

    print(f"      ➜ Parsed {len(teams)} teams from this page")
    return teams

def parse_competition_classes(main_url):
    """Extract all competition classes from the class picker."""
    html = fetch_html(main_url)
    soup = BeautifulSoup(html, "html.parser")

    class_div = soup.find("div", class_="d-none d-md-block mb-2")
    if not class_div:
        return []

    classes = []
    for a in class_div.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(BASE_URL, href)
        classes.append({
            "name": a.get_text(strip=True),
            "url": full_url
        })
    return classes

def parse_full_competition(main_url, title):
    classes = parse_competition_classes(main_url)
    result = {
        "competition": title,
        "classes": []
    }

    print(f"\n🎯 Competition: {title}")
    print(f"   ➜ Found {len(classes)} class{'es' if len(classes) != 1 else ''}")

    if not classes:
        print(f"   ⚠️ No classes found at {main_url}")
        return result

    for cls in classes:
        print(f"\n🏁 Parsing class: {cls['name']}")
        mangkamp_teams = parse_class_page(cls["url"])

        # Extract base “f” param to build apparatus URLs
        parsed_url = urlparse(cls["url"])
        base_f = parse_qs(parsed_url.query).get("f", [""])[0]

        apparatus_urls = {
            "fx": cls["url"].replace(f"f={base_f}", f"f={int(base_f)}"),
            "tu": cls["url"].replace(f"f={base_f}", f"f={int(base_f)+1}"),
            "tr": cls["url"].replace(f"f={base_f}", f"f={int(base_f)+2}")
        }

        apparatus_data = {}
        for key, app_url in apparatus_urls.items():
            print(f"   🔹 {key.upper()} page: {app_url}")
            apparatus_data[key] = parse_class_page(app_url)

        print(f"   ✅ Parsed {len(mangkamp_teams)} teams in '{cls['name']}'")

        result["classes"].append({
            "class_name": cls["name"],
            "url": cls["url"],
            "teams": mangkamp_teams,
            "apparatus": apparatus_data
        })

    print(f"\n🏆 Finished '{title}' with {len(result['classes'])} total classes.\n")
    return result

def main():
    # Example competition URL
    comp_url = "https://live.sporteventsystems.se/Score/WebScore/3419?country=swe"
    comp_title = "Riksfyran"  # fallback if we can’t parse title
    output = []

    full_comp = parse_full_competition(comp_url, comp_title)
    full_comp["last_updated"] = datetime.utcnow().isoformat() + "Z"
    output.append(full_comp)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Scraped {len(output)} competitions with classes")

if __name__ == "__main__":
    main()
