const RESULTS_URL = "https://datpengu.github.io/TeamGymScore/results.json";

async function fetchAndRender() {
  const container = document.getElementById("tables");
  container.innerHTML = "Loading…";

  try {
    const res = await fetch(RESULTS_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    container.innerHTML = "";

    data.competitions.forEach(comp => {
      // =========================
      // Competition header
      // =========================
      const compHeader = document.createElement("section");

      const title = document.createElement("h2");
      title.textContent = comp.competition;
      compHeader.appendChild(title);

      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = [
        comp.date_from,
        comp.date_to,
        comp.place
      ].filter(Boolean).join(" • ");
      compHeader.appendChild(meta);

      container.appendChild(compHeader);

      // =========================
      // Classes
      // =========================
      comp.classes.forEach(cls => {
        const classSection = document.createElement("section");

        const classTitle = document.createElement("h3");
        classTitle.textContent = cls.class_name;
        classSection.appendChild(classTitle);

        // -------------------------
        // ALLROUND (Mångkamp)
        // -------------------------
        if (cls.teams && cls.teams.length > 0) {
          classSection.appendChild(renderAllroundTable(cls.teams));
        } else {
          classSection.appendChild(emptyNote("No teams yet"));
        }

        // -------------------------
        // APPARATUS TABLES
        // -------------------------
        renderApparatus(classSection, "FX", cls.fx_app);
        renderApparatus(classSection, "TU", cls.tu_app);
        renderApparatus(classSection, "TR", cls.tr_app);

        container.appendChild(classSection);
      });
    });

  } catch (err) {
    console.error(err);
    container.textContent = "Failed to load data.";
  }
}

/* =========================
   HELPERS
========================= */

function renderAllroundTable(teams) {
  const table = document.createElement("table");
  table.className = "allround";

  table.innerHTML = `
    <thead>
      <tr>
        <th>Rank</th>
        <th>Team</th>
        <th>FX</th>
        <th>TU</th>
        <th>TR</th>
        <th>Total</th>
        <th>Gap</th>
      </tr>
    </thead>
    <tbody>
      ${teams.map(t => `
        <tr>
          <td>${t.rank ?? ""}</td>
          <td>${t.name}</td>
          <td>${fmt(t.fx?.score)}</td>
          <td>${fmt(t.tu?.score)}</td>
          <td>${fmt(t.tr?.score)}</td>
          <td>${fmt(t.total)}</td>
          <td>${fmt(t.gap)}</td>
        </tr>
      `).join("")}
    </tbody>
  `;
  return table;
}

function renderApparatus(parent, label, rows) {
  if (!rows || rows.length === 0) return;

  const title = document.createElement("h4");
  title.textContent = label;
  parent.appendChild(title);

  const table = document.createElement("table");
  table.className = "apparatus";

  table.innerHTML = `
    <thead>
      <tr>
        <th>Rank</th>
        <th>Team</th>
        <th>D</th>
        <th>E</th>
        <th>C</th>
        <th>HJ</th>
        <th>Score</th>
        <th>Gap</th>
      </tr>
    </thead>
    <tbody>
      ${rows.map(r => `
        <tr>
          <td>${r.rank ?? ""}</td>
          <td>${r.name}</td>
          <td>${fmt(r.D)}</td>
          <td>${fmt(r.E)}</td>
          <td>${fmt(r.C)}</td>
          <td>${fmt(r.HJ)}</td>
          <td>${fmt(r.score)}</td>
          <td>${fmt(r.gap)}</td>
        </tr>
      `).join("")}
    </tbody>
  `;
  parent.appendChild(table);
}

function emptyNote(text) {
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = text;
  return p;
}

function fmt(v) {
  return typeof v === "number" ? v.toFixed(3) : "";
}

/* ========================= */

fetchAndRender();
