import re

raw_data = """<your_raw_json_snippet_here>"""  # paste the snippet here

teams = []
rank_counter = 1
previous_total = None

# Pattern to find a team block: numeric prefix + team name + scores
pattern = re.compile(r'(\d+)([A-Za-zÅÄÖåäö\s]+)(.*)')

# Pattern to extract scores for each apparatus
score_pattern = re.compile(r'(\d+,\d+)D: (\d+,\d+)E: (\d+,\d+)C: (\d+,\d+)')

for line in raw_data.splitlines():
    match = pattern.match(line.strip())
    if match:
        num_prefix = match.group(1)
        team_name = match.group(2).strip()
        scores_str = match.group(3).strip()

        # Calculate start_position
        start_position = int(num_prefix) - rank_counter

        # Extract scores for fx, tu, tr
        scores = score_pattern.findall(scores_str)
        fx = tu = tr = {"score": None, "D": None, "E": None, "C": None}
        if len(scores) >= 1:
            fx = {
                "score": float(scores[0][0].replace(',', '.')),
                "D": float(scores[0][1].replace(',', '.')),
                "E": float(scores[0][2].replace(',', '.')),
                "C": float(scores[0][3].replace(',', '.'))
            }
        if len(scores) >= 2:
            tu = {
                "score": float(scores[1][0].replace(',', '.')),
                "D": float(scores[1][1].replace(',', '.')),
                "E": float(scores[1][2].replace(',', '.')),
                "C": float(scores[1][3].replace(',', '.'))
            }
        if len(scores) >= 3:
            tr = {
                "score": float(scores[2][0].replace(',', '.')),
                "D": float(scores[2][1].replace(',', '.')),
                "E": float(scores[2][2].replace(',', '.')),
                "C": float(scores[2][3].replace(',', '.'))
            }

        # Total is the last numeric value in scores_str
        total_match = re.findall(r'(\d+,\d+)$', scores_str)
        total = float(total_match[0].replace(',', '.')) if total_match else None

        # Gap calculation
        gap = None if rank_counter == 1 else round(total - previous_total, 2) if total is not None and previous_total is not None else None
        previous_total = total if total is not None else previous_total

        team_data = {
            "rank": rank_counter,
            "start_position": start_position,
            "name": team_name,
            "fx": fx,
            "tu": tu,
            "tr": tr,
            "total": total,
            "gap": gap
        }

        teams.append(team_data)
        rank_counter += 1

# Example output
import json
print(json.dumps(teams, indent=2, ensure_ascii=False))
