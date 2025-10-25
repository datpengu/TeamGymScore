import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://live.sporteventsystems.se"

# ---------------------------
# UTILITIES
# ---------------------------
def fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return ""

def number_from(tok: str):
    try:
        return float(tok.replace(",", "."))
    except:
        return None

def safe(lst, idx):
    return lst[idx] if idx < len(lst) else None

def is_rank(tok: str) -> bool:
    return re.fullmatch(r"\d{1,2}", tok) is not None

def is_start(tok: str) -> bool:
    return re.fullmatch(r"\d{1,2}", tok) is not None

def is_score(tok: str) -> bool:
    return re.fullmatch(r"\d+,\d{3}", tok) is not None

def strip_tokens(div: BeautifulSoup):
    return [s for s in div.stripped_strings]

# ---------------------------
# DISCOVER ALL TEAMGYM COMPETITIONS
# ---------------------------
def discover_teamgym_competitions():
    html = fetch_html(f"{BASE_URL}/Score/?country=swe")
    soup = BeautifulSoup(html, "html.parser")

    results = []
    teamgym_header = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string=re.compile("Teamgym", re.I))
    if not teamgym_header:
        print("❌ No TeamGym section found.")
        return results

    row = teamgym_header.find_parent("div", class_="row")
    for sibling in row.find_next_siblings("div"):
        header = sibling.find("div", class_="col fs-4 px-2 bg-dark-subtle")
        if header:
            print("🛑 Reached next section — stopping discovery.")
            break

        a = sibling.find("a", href=True)
        if not a:
            continue

        link = urljoin(BASE_URL, a["href"])
        name = a.get_text(strip=True)
        cols = sibling.select(".col-12, .col-md-6, .col-xl-4, .col-xxl-3, .col-xxl-6")
        date_from = cols[0].get_text(strip=True) if len(cols) > 0 else None
        date_to = cols[1].get_text(strip=True) if len(cols) > 1 else None
        place = cols[-1].get_text(strip=True) if len(cols) > 2 else None

        results.append({
            "competition": name,
            "url": link,
            "date_from": date_from,
            "date_to": date_to,
            "place": place
        })

    print(f"✅ Found {len(results)} TeamGym competitions.")
    return results

# ---------------------------
# PARSE CLASS BUTTONS
# ---------------------------
def find_class_buttons(soup: BeautifulSoup):
    container = soup.find("div", class_="d-none d-md-block mb-2")
    if not container:
        return []
    links = []
    for a in container.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = urljoin(BASE_URL, a["href"])
        links.append({"name": text, "url": href})
    return links

# ---------------------------
# TAB IDS
# ---------------------------
def tab_ids(f_value: str):
    return (f"Allround-{f_value}", f"App1-{f_value}", f"App2-{f_value}", f"App3-{f_value}")

# ---------------------------
# PARSING HELPERS
# ---------------------------
def parse_allround_tokens(tokens):
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
                    scores.append(number_from(tok))
                    j += 1
                    continue
                m = re.match(r"^(D|E|C)[:\-]?\s*(\d+,\d{3})$", tok)
                if m:
                    decs.append(number_from(m.group(2)))
                    j += 1
                    continue
                if tok in ("D", "D:", "E", "E:", "C", "C:") and j + 1 < len(tokens) and is_score(tokens[j+1]):
                    decs.append(number_from(tokens[j+1]))
                    j += 2
                    continue
                j += 1
                if j - i > 200:
                    break

            fx = {"score": safe(scores, 0), "D": safe(decs, 0), "E": safe(decs, 1), "C": safe(decs, 2), "HJ": None}
            tu = {"score": safe(scores, 1), "D": safe(decs, 3), "E": safe(decs, 4), "C": safe(decs, 5), "HJ": None}
            tr = {"score": safe(scores, 2), "D": safe(decs, 6), "E": safe(decs, 7), "C": safe(decs, 8), "HJ": None}
            total = safe(scores, 3)
            gap = 0.0 if rank == 1 else safe(scores, 4)

            teams.append({
                "rank": rank, "start_position": start, "name": name,
                "fx": fx, "tu": tu, "tr": tr,
                "total": total, "gap": gap
            })
            i = j
        else:
            i += 1
    return teams


def parse_apparatus_tokens(tokens):
    out = []
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

                if tok.startswith("D") and j+1 < len(tokens) and is_score(tokens[j+1]):
                    D = number_from(tokens[j+1]); j += 2; continue
                if tok.startswith("E") and j+1 < len(tokens) and is_score(tokens[j+1]):
                    E = number_from(tokens[j+1]); j += 2; continue
                if tok.startswith("C") and j+1 < len(tokens) and is_score(tokens[j+1]):
                    C = number_from(tokens[j+1]); j += 2; continue
                if tok.startswith("HJ") and j+1 < len(tokens) and is_score(tokens[j+1]):
                    HJ = number_from(tokens[j+1]); j += 2; continue
                if is_score(tok):
                    if score is None:
                        score = number_from(tok)
                    elif gap is None:
                        gap = number_from(tok)
                    j += 1
                    continue
                j += 1
                if j - i > 200:
                    break

            out.append({
                "rank": rank, "start_position": start, "name": name,
                "D": D, "E": E, "C": C, "HJ": HJ,
                "score": score, "gap": 0.0 if rank == 1 else gap
            })
            i = j
        else:
            i += 1
    return out

# ---------------------------
# DETERMINE STATUS
# ---------------------------
def determine_status(teams):
    if not teams:
        return "upcoming"
    scored = sum(1 for t in teams if t.get("total") or t.get("fx", {}).get("score"))
    if scored == 0:
        return "upcoming"
    if scored < len(teams):
        return "ongoing"
    return "finished"

# ---------------------------
# PARSE CLASS PAGE
# ---------------------------
def parse_class_page(cls):
    url = cls["url"]
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    f_val = parse_qs(urlparse(url).query).get("f", [None])[0]
    if not f_val:
        print(f"⚠️ Skipping class (no f param): {url}")
        return {"class_name": cls["name"], "status": "upcoming", "teams": [], "apparatus": {}}

    allround_id, fx_id, tu_id, tr_id = tab_ids(f_val)

    def get_tokens(tab_id):
        div = soup.find("div", id=tab_id)
        return strip_tokens(div) if div else []

    allround = parse_allround_tokens(get_tokens(allround_id))
    fx = parse_apparatus_tokens(get_tokens(fx_id))
    tu = parse_apparatus_tokens(get_tokens(tu_id))
    tr = parse_apparatus_tokens(get_tokens(tr_id))

    status = determine_status(allround)
    print(f"   ✅ {cls['name']}: {len(allround)} allround, {len(fx)} FX, {len(tu)} TU, {len(tr)} TR → {status}")
    return {
        "class_name": cls["name"],
        "url": url,
        "status": status,
        "teams": allround,
        "apparatus": {"fx": fx, "tu": tu, "tr": tr}
    }

# ---------------------------
# PARSE FULL COMPETITION
# ---------------------------
def parse_full_competition(url, meta):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    classes = find_class_buttons(soup)
    print(f"\n🎯 {meta['competition']} — {len(classes)} class(es)")

    comp_out = {
        "competition": meta["competition"],
        "date_from": meta["date_from"],
        "date_to": meta["date_to"],
        "place": meta["place"],
        "classes": []
    }

    # Use threading for class parsing (keep order)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(parse_class_page, cls): idx for idx, cls in enumerate(classes)}
        results = [None] * len(classes)
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                print(f"❌ Error parsing class: {e}")
                results[idx] = {"class_name": classes[idx]["name"], "teams": [], "apparatus": {}, "status": "upcoming"}

    comp_out["classes"] = [r for r in results if r]
    return comp_out

# ---------------------------
# MAIN
# ---------------------------
def main():
    comps = discover_teamgym_competitions()
    results = []

    for comp in comps:
        try:
            parsed = parse_full_competition(comp["url"], comp)
            results.append(parsed)
        except Exception as e:
            print(f"❌ Failed {comp['competition']}: {e}")

    final = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "competitions": results
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Wrote {len(results)} competitions to results.json")


if __name__ == "__main__":
    main()
