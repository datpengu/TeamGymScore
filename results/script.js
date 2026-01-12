const RESULTS_URL = "https://datpengu.github.io/TeamGymScore/results.json";

async function fetchAndRender() {
  const root = document.getElementById("tables");
  root.textContent = "Loading…";

  try {
    const res = await fetch(RESULTS_URL, { cache: "no-store" });
    const data = await res.json();
    root.innerHTML = "";

    data.competitions.forEach(comp => {
      const compSection = document.createElement("section");

      compSection.innerHTML = `
        <h2>${comp.competition}</h2>
        <p class="meta">${[comp.date_from, comp.date_to, comp.place].filter(Boolean).join(" • ")}</p>
      `;

      comp.classes.forEach(cls => {
        const clsSection = document.createElement("section");
        clsSection.innerHTML = `<h3>${cls.class_name}</h3>`;

        const tabs = ["Mångkamp", "FX", "TU", "TR"];
        const tabRow = document.createElement("div");
        tabRow.className = "tabs";

        const contents = [];

        tabs.forEach((label, i) => {
          const btn = document.createElement("button");
          btn.className = "tab" + (i === 0 ? " active" : "");
          btn.textContent = label;

          btn.onclick = () => {
            tabRow.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            contents[i].classList.add("active");
          };

          tabRow.appendChild(btn);
        });

        clsSection.appendChild(tabRow);

        // ---- TAB CONTENTS ----
        contents.push(renderAllround(cls.teams));
        contents.push(renderApp(cls.fx_app));
        contents.push(renderApp(cls.tu_app));
        contents.push(renderApp(cls.tr_app));

        contents.forEach((c, i) => {
          c.className = "tab-content" + (i === 0 ? " active" : "");
          clsSection.appendChild(c);
        });

        compSection.appendChild(clsSection);
      });

      root.appendChild(compSection);
    });

  } catch (e) {
    console.error(e);
    root.textContent = "Failed to load data.";
  }
}

function renderAllround(teams) {
  if (!teams || teams.length === 0) return empty("No teams yet");

  return table(`
    <tr><th>Rank</th><th>Team</th><th>FX</th><th>TU</th><th>TR</th><th>Total</th><th>Gap</th></tr>
  `, teams.map(t => `
    <tr>
      <td>${t.rank}</td>
      <td>${t.name}</td>
      <td>${fmt(t.fx?.score)}</td>
      <td>${fmt(t.tu?.score)}</td>
      <td>${fmt(t.tr?.score)}</td>
      <td>${fmt(t.total)}</td>
      <td>${fmt(t.gap)}</td>
    </tr>
  `));
}

function renderApp(rows) {
  if (!rows || rows.length === 0) return empty("No scores yet");

  return table(`
    <tr><th>Rank</th><th>Team</th><th>D</th><th>E</th><th>C</th><th>HJ</th><th>Score</th><th>Gap</th></tr>
  `, rows.map(r => `
    <tr>
      <td>${r.rank}</td>
      <td>${r.name}</td>
      <td>${fmt(r.D)}</td>
      <td>${fmt(r.E)}</td>
      <td>${fmt(r.C)}</td>
      <td>${fmt(r.HJ)}</td>
      <td>${fmt(r.score)}</td>
      <td>${fmt(r.gap)}</td>
    </tr>
  `));
}

function table(head, rows) {
  const d = document.createElement("div");
  d.innerHTML = `<table><thead>${head}</thead><tbody>${rows.join("")}</tbody></table>`;
  return d.firstChild;
}

function empty(text) {
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = text;
  return p;
}

function fmt(v) {
  return typeof v === "number" ? v.toFixed(3) : "";
}

fetchAndRender();
