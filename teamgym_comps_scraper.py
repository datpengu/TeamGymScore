import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

BASE_URL = "https://live.sporteventsystems.se"
INDEX_URL = f"{BASE_URL}/Score/?country=swe"

def parse_score_block(block_text):
    """Extract D, E, C, and score values from a score string"""
    block_text = block_text.replace(",", ".")
    match_score = re.search(r"([\d]+\.[\d]{3})", block_text)
    D = re.search(r"D:\s*([\d.]+)", block_text)
    E = re.search(r"E:\s*([\d.]+)", block_text)
    C = re.search(r"C:\s*([\d.]+)", block_text)

    return {
        "score": float(match_score.group(1)) if match_score else None,
        "D": float(D.group(1)) if D else None,
        "E": float(E.group(1)) if E else None,
        "C": float(C.group(1)) if C else None
    }

def parse_competition_page(url):
    """Parse a competition's WebScore page"""
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    container = soup.find("div", id="TabContent")
    if not container:
        return []

    lines = [div.get_text(strip=True) for div in container.find_all("div") if div.get_text(strip=True)]
    results = []

    rank_counter = 1
    i = 0
    while i < len(lines):
        line = lines[i]
        try:
            rank_str = str(rank_counter)
            rest = line[len(rank_str):]
            start_pos_match = re.match(r"(\d+)", rest)
            if not start_pos_match:
                raise ValueError("No start position found")
            start_pos = int(start_pos_match.group(1))
            name = rest[start_pos_match.end():].strip()

            # Try to extract 3 apparatus + total
            fx_text = lines[i + 1] if i + 1 < len(lines) else ""
            tu_text = lines[i + 2] if i + 2 < len(lines) else ""
            tr_text = lines[i + 3] if i + 3 < len(lines) else ""

            total_match = re.search(r"([\d]+\.[\d]{3})", line)
            total = float(total_match.group(1)) if total_match else None

            gap = None
            if rank_counter > 1:
                gap_match = re.findall(r"([\d]+\.[\d]{3})", line)
                if len(gap_match) > 1:
                    gap = float(gap_match[-1])

            results.append({
                "rank": rank_counter,
                "start_position": start_pos,
                "name": name,
                "fx": parse_score_block(fx_text),
                "tu": parse_score_block(tu_text),
                "tr": parse_score_block(tr_text),
                "total": total,
                "gap": gap or 0.0
            })

            rank_counter += 1
            i += 1
        except Exception:
            i += 1

    return results

def scrape_all_competitions():
    """Scrape all TeamGym competitions and their results"""
    response = requests.get(INDEX_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    competitions = []

    # Find "Teamgym" section header
    header = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string="Teamgym")
    if not header:
        print("⚠️ No Teamgym section found.")
        return competitions

    # Loop through following rows until next header
    for row in header.find_all_next("div", class_="row"):
        # Stop if next section header appears
        next_header = row.find("div", class_="col fs-4 px-2 bg-dark-subtle")
        if next_header:
            break

        cols = row.find_all("div", class_="fs-6")
        if not cols:
            continue

        link = row.find("a", href=True)
        if not link or "WebScore" not in link["href"]:
            continue

        date_from = cols[0].get_text(strip=True) if len(cols) > 0 else ""
        date_to = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        place = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        title = link.get_text(strip=True)
        href = link["href"]
        full_url = href if href.startswith("http") else BASE_URL + href

        print(f"🧭 Parsing competition: {title} ({place})")

        teams = parse_competition_page(full_url)

        competitions.append({
            "title": title,
            "url": full_url,
            "date_from": date_from,
            "date_to": date_to,
            "place": place,
            "teams": teams
        })

    return competitions

if __name__ == "__main__":
    comps = scrape_all_competitions()
    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "competitions": comps
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(comps)} competitions with results to results.json")
