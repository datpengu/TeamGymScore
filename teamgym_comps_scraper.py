import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

BASE_URL = "https://live.sporteventsystems.se"
MAIN_URL = f"{BASE_URL}/Score/?country=swe"

# ---------------------------
# Utility Functions
# ---------------------------
def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def safe(lst, idx):
    return lst[idx] if idx < len(lst) else None


def num(s: str):
    try:
        return float(s.replace(",", "."))
    except:
        return None


# ---------------------------
# Discover TeamGym competitions
# ---------------------------
def discover_teamgym_comps():
    html = fetch_html(MAIN_URL)
    soup = BeautifulSoup(html, "html.parser")

    comps = []
    teamgym_header = soup.find("div", string=re.compile(r"Teamgym", re.I))
    if not teamgym_header:
        print("⚠️ No Teamgym header found")
        return comps

    # Start from the header row
    for row in teamgym_header.find_all_next("div", class_="row"):
        # Stop if we hit another sport header
        header_div = row.find("div", class_="col fs-4 px-2 bg-dark-subtle")
        if header_div:
            break  # new section → stop

        link = row.find("a", href=True)
        if not link:
            continue

        url = urljoin(BASE_URL, link["href"])
        title = clean_text(link.get_text())
        cols = row.select("div.col-12, div.col-md-6, div.col-xl-4, div.col-xxl-3")
        date_from = None
        date_to = None
        place = None

        text_parts = [c.get_text(strip=True) for c in cols if c.get_text(strip=True)]
        if len(text_parts) >= 1:
            date_from = text_parts[0]
        if len(text_parts) >= 2:
            date_to = text_parts[1]
        if len(text_parts) >= 3:
            place = text_parts[2]

        comps.append({
            "title": title,
            "url": url,
            "date_from": date_from,
            "date_to": date_to,
            "place": place
        })

    print(f"🔍 Found {len(comps)} TeamGym competitions.")
    return comps


# ---------------------------
# Class Picker + Tab IDs
# ---------------------------
def find_class_buttons(soup):
    container = soup.find("div", class_="d-none d-md-block mb-2")
    if not container:
        return []
    links = []
    for a in container.find_all("a", href=True):
        links.append({
            "name": clean_text(a.get_text()),
            "url": urljoin(BASE_URL, a["href"])
        })
    return links


def tab_ids_for(f):
    return (
        f"Allround-{f}",
        f"App1-{f}",
        f"App2-{f}",
        f"App3-{f}"
    )


def strip_tokens(div):
    return [s for s in div.stripped_strings]


def is_rank(tok):
    return re.fullmatch(r"\d{1,2}", tok)


def is_start(tok):
    return re.fullmatch(r"\d{1,2}", tok)


def is_score(tok):
    return re.fullmatch(r"\d+,\d{3}", tok)


# ---------------------------
# Parsers
# ---------------------------
def parse_allround(tokens):
    teams = []
    i = 0
    while i < len(tokens):
        if i + 2 < len(tokens) and is_rank(tokens[i]) and is_start(tokens[i+1]):
            rank = int(tokens[i])
            start = int(tokens[i+1])
            name = tokens[i+2]
            j = i + 3
            scores, decs = [], []

            while j < len(tokens):
                if j + 1 < len(tokens) and is_rank(tokens[j]) and is_start(tokens[j+1]):
                    break

                tok = tokens[j]
                if is_score(tok):
                    scores.append(num(tok))
                else:
                    m = re.match(r"(D|E|C)\s*[:\-]?\s*(\d+,\d{3})", tok)
                    if m:
                        decs.append(num(m.group(2)))
                j += 1

            fx = {"score": safe(scores, 0), "D": safe(decs, 0), "E": safe(decs, 1), "C": safe(decs, 2), "HJ": None}
            tu = {"score": safe(scores, 1), "D": safe(decs, 3), "E": safe(decs, 4), "C": safe(decs, 5), "HJ": None}
            tr = {"score": safe(scores, 2), "D": safe(decs, 6), "E": safe(decs, 7), "C": safe(decs, 8), "HJ": None}

            total = safe(scores, 3)
            gap = 0.0 if rank == 1 else safe(scores, 4)

            teams.append({
                "rank": rank,
                "start_position": start,
                "name": name,
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


def parse_apparatus(tokens):
    teams = []
    i = 0
    while i < len(tokens):
        if i + 2 < len(tokens) and is_rank(tokens[i]) and is_start(tokens[i+1]):
            rank = int(tokens[i])
            start = int(tokens[i+1])
            name = tokens[i+2]
            j = i + 3
            D = E = C = HJ = score = gap = None

            while j < len(tokens):
                if j + 1 < len(tokens) and is_rank(tokens[j]) and is_start(tokens[j+1]):
                    break

                tok = tokens[j]
                m = re.match(r"(D|E|C|HJ)\s*[:\-]?\s*(\d+,\d{3})", tok)
                if m:
                    if m.group(1) == "D": D = num(m.group(2))
                    elif m.group(1) == "E": E = num(m.group(2))
                    elif m.group(1) == "C": C = num(m.group(2))
                    elif m.group(1) == "HJ": HJ = num(m.group(2))
                elif is_score(tok):
                    if score is None:
                        score = num(tok)
                    elif gap is None:
                        gap = num(tok)
                j += 1

            teams.append({
                "rank": rank,
                "start_position": start,
                "name": name,
                "D": D,
                "E": E,
                "C": C,
                "HJ": HJ,
                "score": score,
                "gap": 0.0 if rank == 1 else gap
            })
            i = j
        else:
            i += 1
    return teams


# ---------------------------
# Parse a single class page
# ---------------------------
def parse_class_page(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    f_val = parse_qs(urlparse(url).query).get("f", [None])[0]
    if not f_val:
        return {"teams": [], "apparatus": {"fx": [], "tu": [], "tr": []}}

    allround_id, app1_id, app2_id, app3_id = tab_ids_for(f_val)
    result = {"teams": [], "apparatus": {"fx": [], "tu": [], "tr": []}}

    def parse_tab(tab_id, parser):
        div = soup.find("div", id=tab_id)
        if not div:
            return []
        tokens = strip_tokens(div)
        return parser(tokens)

    result["teams"] = parse_tab(allround_id, parse_allround)
    result["apparatus"]["fx"] = parse_tab(app1_id, parse_apparatus)
    result["apparatus"]["tu"] = parse_tab(app2_id, parse_apparatus)
    result["apparatus"]["tr"] = parse_tab(app3_id, parse_apparatus)
    return result


# ---------------------------
# Parse an entire competition
# ---------------------------
def parse_competition(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    title = clean_text(soup.select_one("h1, h2, .fs-4").get_text()) if soup.select_one("h1, h2, .fs-4") else "Competition"
    classes = find_class_buttons(soup)

    print(f"\n🎯 Competition: {title}")
    print(f"   ➜ Found {len(classes)} classes")

    out = {"competition": title, "classes": []}
    for cls in classes:
        print(f"     🏁 Parsing class: {cls['name']}")
        parsed = parse_class_page(cls["url"])
        print(f"        • Allround teams: {len(parsed['teams'])}")
        out["classes"].append({
            "class_name": cls["name"],
            "url": cls["url"],
            "teams": parsed["teams"],
            "apparatus": parsed["apparatus"]
        })
    return out


# ---------------------------
# MAIN
# ---------------------------
def main():
    comps = discover_teamgym_comps()
    results = []

    for comp in comps:
        parsed = parse_competition(comp["url"])
        parsed.update({
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "date_from": comp["date_from"],
            "date_to": comp["date_to"],
            "place": comp["place"]
        })
        results.append(parsed)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Wrote {len(results)} competitions to results.json")


if __name__ == "__main__":
    main()
