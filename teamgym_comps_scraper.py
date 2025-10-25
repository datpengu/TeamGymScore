import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://live.sporteventsystems.se"

# ---------- Utilities ----------
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
    try: return float(tok.replace(",", "."))
    except: return None

def safe(lst, idx): return lst[idx] if idx < len(lst) else None
def is_rank(tok): return re.fullmatch(r"\d{1,2}", tok) is not None
def is_start(tok): return re.fullmatch(r"\d{1,2}", tok) is not None
def is_score(tok): return re.fullmatch(r"\d+,\d{3}", tok) is not None
def strip_tokens(div): return [s for s in div.stripped_strings]

# ---------- Discover competitions ----------
def discover_teamgym_competitions():
    html = fetch_html(f"{BASE_URL}/Score/?country=swe")
    soup = BeautifulSoup(html, "html.parser")

    results = []
    header = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string=re.compile("Teamgym", re.I))
    if not header: return results

    row = header.find_parent("div", class_="row")
    for sibling in row.find_next_siblings("div"):
        if sibling.find("div", class_="col fs-4 px-2 bg-dark-subtle"): break
        a = sibling.find("a", href=True)
        if not a: continue
        cols = sibling.select(".col-12, .col-md-6, .col-xl-4, .col-xxl-3, .col-xxl-6")
        results.append({
            "competition": a.get_text(strip=True),
            "url": urljoin(BASE_URL, a["href"]),
            "date_from": cols[0].get_text(strip=True) if len(cols)>0 else None,
            "date_to": cols[1].get_text(strip=True) if len(cols)>1 else None,
            "place": cols[-1].get_text(strip=True) if len(cols)>2 else None
        })
    print(f"✅ Found {len(results)} TeamGym competitions.")
    return results

# ---------- Parse helpers ----------
def find_class_buttons(soup):
    div = soup.find("div", class_="d-none d-md-block mb-2")
    if not div: return []
    return [{"name": a.get_text(strip=True), "url": urljoin(BASE_URL, a["href"])} for a in div.find_all("a", href=True)]

def tab_ids(f_val): return (f"Allround-{f_val}", f"App1-{f_val}", f"App2-{f_val}", f"App3-{f_val}")

def parse_allround_tokens(tokens):
    teams, i = [], 0
    while i < len(tokens):
        if i+2 < len(tokens) and is_rank(tokens[i]) and is_start(tokens[i+1]):
            rank, start, name = int(tokens[i]), int(tokens[i+1]), tokens[i+2]
            j, scores, decs = i+3, [], []
            while j < len(tokens):
                if j+1 < len(tokens) and is_rank(tokens[j]) and is_start(tokens[j+1]): break
                tok = tokens[j]
                if is_score(tok): scores.append(number_from(tok)); j += 1; continue
                m = re.match(r"^(D|E|C)[:\-]?\s*(\d+,\d{3})$", tok)
                if m: decs.append(number_from(m.group(2))); j += 1; continue
                if tok in ("D","E","C","D:","E:","C:") and j+1<len(tokens) and is_score(tokens[j+1]):
                    decs.append(number_from(tokens[j+1])); j += 2; continue
                j += 1
                if j-i > 200: break
            fx = {"score": safe(scores,0),"D":safe(decs,0),"E":safe(decs,1),"C":safe(decs,2),"HJ":None}
            tu = {"score": safe(scores,1),"D":safe(decs,3),"E":safe(decs,4),"C":safe(decs,5),"HJ":None}
            tr = {"score": safe(scores,2),"D":safe(decs,6),"E":safe(decs,7),"C":safe(decs,8),"HJ":None}
            total, gap = safe(scores,3), 0.0 if rank==1 else safe(scores,4)
            teams.append({"rank":rank,"start_position":start,"name":name,"fx":fx,"tu":tu,"tr":tr,"total":total,"gap":gap})
            i = j
        else: i += 1
    return teams

def parse_apparatus_tokens(tokens):
    out, i = [], 0
    while i < len(tokens):
        if i+2 < len(tokens) and is_rank(tokens[i]) and is_start(tokens[i+1]):
            rank, start, name = int(tokens[i]), int(tokens[i+1]), tokens[i+2]
            j, D, E, C, HJ, score, gap = i+3, None, None, None, None, None, None
            while j < len(tokens):
                if j+1<len(tokens) and is_rank(tokens[j]) and is_start(tokens[j+1]): break
                tok = tokens[j]
                if tok.startswith("D") and j+1<len(tokens) and is_score(tokens[j+1]): D=number_from(tokens[j+1]); j+=2; continue
                if tok.startswith("E") and j+1<len(tokens) and is_score(tokens[j+1]): E=number_from(tokens[j+1]); j+=2; continue
                if tok.startswith("C") and j+1<len(tokens) and is_score(tokens[j+1]): C=number_from(tokens[j+1]); j+=2; continue
                if tok.startswith("HJ") and j+1<len(tokens) and is_score(tokens[j+1]): HJ=number_from(tokens[j+1]); j+=2; continue
                if is_score(tok):
                    if score is None: score=number_from(tok)
                    elif gap is None: gap=number_from(tok)
                    j+=1; continue
                j += 1
                if j-i > 200: break
            out.append({"rank":rank,"start_position":start,"name":name,
                        "D":D,"E":E,"C":C,"HJ":HJ,"score":score,"gap":0.0 if rank==1 else gap})
            i = j
        else: i += 1
    return out

def determine_status(teams):
    if not teams: return "upcoming"
    scored = sum(1 for t in teams if t.get("total") or t.get("fx",{}).get("score"))
    if scored == 0: return "upcoming"
    if scored < len(teams): return "ongoing"
    return "finished"

# ---------- Parse a single class ----------
def parse_class_page(cls):
    url, name = cls["url"], cls["name"]
    html = fetch_html(url)
    if not html: return {"class_name": name, "status": "upcoming", "teams": [], "apparatus": {}}
    soup = BeautifulSoup(html, "html.parser")
    f_val = parse_qs(urlparse(url).query).get("f", [None])[0]
    if not f_val: return {"class_name": name, "status": "upcoming", "teams": [], "apparatus": {}}
    ids = tab_ids(f_val)
    def toks(tab_id): 
        div = soup.find("div", id=tab_id)
        return strip_tokens(div) if div else []
    allround, fx, tu, tr = parse_allround_tokens(toks(ids[0])), parse_apparatus_tokens(toks(ids[1])), parse_apparatus_tokens(toks(ids[2])), parse_apparatus_tokens(toks(ids[3]))
    status = determine_status(allround)
    print(f"   ✅ {name}: {len(allround)} allround, {len(fx)} FX, {len(tu)} TU, {len(tr)} TR → {status}")
    return {"class_name": name, "url": url, "status": status, "teams": allround, "apparatus": {"fx": fx, "tu": tu, "tr": tr}}

# ---------- Parse full competition ----------
def parse_full_competition(comp):
    html = fetch_html(comp["url"])
    if not html: return None
    soup = BeautifulSoup(html, "html.parser")
    classes = find_class_buttons(soup)
    print(f"\n🎯 {comp['competition']} — {len(classes)} class(es)")
    out = {"competition": comp["competition"], "date_from": comp["date_from"], "date_to": comp["date_to"], "place": comp["place"], "classes": []}

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(parse_class_page, cls) for cls in classes]
        for fut in as_completed(futures):
            try: out["classes"].append(fut.result())
            except Exception as e: print(f"   ❌ Class parse failed: {e}")

    return out

# ---------- MAIN ----------
def main():
    comps = discover_teamgym_competitions()
    results = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(parse_full_competition, c) for c in comps]
        for fut in as_completed(futures):
            res = fut.result()
            if res: results.append(res)

    final = {"last_updated": datetime.utcnow().isoformat() + "Z", "competitions": results}
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Wrote {len(results)} competitions to results.json")

if __name__ == "__main__":
    main()
