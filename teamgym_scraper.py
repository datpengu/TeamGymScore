import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time

INDEX_URL = "https://live.sporteventsystems.se/Score/?country=swe"

# --------------------------
#  STEP 1: Get TeamGym pages
# --------------------------
def fetch_teamgym_urls():
    resp = requests.get(INDEX_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    urls = []
    header = soup.find("div", class_="col fs-4 px-2 bg-dark-subtle", string=lambda t: t and "Teamgym" in t)
    if not header:
        print("⚠️ Teamgym header not found")
        return urls

    for sib in header.parent.find_next_siblings():
        if sib.name == "br":
            break
        link = sib.find("a")
        if link and "href" in link.attrs:
            urls.append({
                "name": link.get_text(strip=True),
                "url": link["href"]
            })
    print(f"🔗 Found {len(urls)} TeamGym competitions.")
    return urls

# --------------------------
#  STEP 2: Parse competition
# --------------------------
def fetch_html(url):
    resp = requests.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text

def find_competition_title(soup):
    possible = soup.select("h1, h2")
    for tag in possible:
        text = tag.get_text(strip=True)
        if len(text) > 3 and not text.lower().startswith("pl"):
            return text
    nav = soup.select_one("ul.nav li.active a")
    if nav:
        return nav.get_text(strip=True)
    return "Competition"

def get_active_mangkamp_div(soup):
    div = soup.find("div", class_=lambda c: c and "show active" in c)
    return div or soup.find("div", class_=lambda c: c and "tab-pane" in c)

def tokenize_div(div):
    return [s for s in div.stripped_strings]

def is_rank_token(tok):
    return re.fullmatch(r"\\d{1,2}", tok) is not None

def is_startpos_token(tok):
    return re.fullmatch(r"\\d{1,2}", tok) is not None

def is_score_token(tok):
    return re.fullmatch(r"\\d+,\\d{3}", tok) is not None

def is_dec_token(tok):
    return re.fullmatch(r"[DEC]:\\s*\\d+,\\d{3}", tok) is not None

def parse_tokens(tokens):
    teams = []
    i = 0
    while i < len(tokens):
        if i + 2 < len(tokens) and is_rank_token(tokens[i]) and is_startpos_token(tokens[i+1]):
            rank = int(tokens[i])
            start_position = int(tokens[i+1])
            name = tokens[i+2].strip()
            j = i + 3
            scores, decs = [], []
            while j < len(tokens):
                tok = tokens[j]
                if j + 1 < len(tokens) and is_rank_token(tokens[j]) and is_startpos_token(tokens[j+1]):
                    break
                if is_score_token(tok):
                    scores.append(float(tok.replace(",", ".")))
                    j += 1
                    continue
                if is_dec_token(tok):
                    m = re.search(r"(\\d+,\\d{3})", tok)
                    if m:
                        decs.append(float(m.group(1).replace(",", ".")))
                    j += 1
                    continue
                if tok in ("D:", "E:", "C:") and j + 1 < len(tokens) and is_score_token(tokens[j+1]):
                    decs.append(float(tokens[j+1].replace(",", ".")))
                    j += 2
                    continue
                j += 1
                if j - i > 200:
                    break

            def dec_at(idx): return decs[idx] if idx < len(decs) else None

            fx = {"score": scores[0] if len(scores) > 0 else None, "D": dec_at(0), "E": dec_at(1), "C": dec_at(2)}
            tu = {"score": scores[1] if len(scores) > 1 else None, "D": dec_at(3), "E": dec_at(4), "C": dec_at(5)}
            tr = {"score": scores[2] if len(scores) > 2 else None, "D": dec_at(6), "E": dec_at(7), "C": dec_at(8)}
            total = scores[3] if len(scores) > 3 else None
            gap = scores[4] if len(scores) > 4 and rank != 1 else 0.0

            teams.append({
                "rank": rank,
                "start_position": start_position,
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

# --------------------------
#  STEP 3: Loop through all
# --------------------------
def main():
    competitions = fetch_teamgym_urls()
    results = []

    for comp in competitions:
        try:
            print(f"⏳ Scraping {comp['name']} ...")
            html = fetch_html(comp["url"])
            soup = BeautifulSoup(html, "html.parser")
            title = find_competition_title(soup)
            div = get_active_mangkamp_div(soup)
            if not div:
                print(f"⚠️ Skipped {title} (no div found)")
                continue
            tokens = tokenize_div(div)
            teams = parse_tokens(tokens)
            results.append({
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "competition": title,
                "url": comp["url"],
                "teams": teams
            })
            print(f"✅ Parsed {len(teams)} teams for {title}")
            time.sleep(2)  # be polite
        except Exception as e:
            print(f"❌ Error with {comp['name']}: {e}")

    with open("all_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"🎉 Done! Scraped {len(results)} competitions.")

if __name__ == "__main__":
    main()
