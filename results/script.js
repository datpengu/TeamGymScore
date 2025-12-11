const RESULTS_URL = "https://datpengu.github.io/TeamGymScore/results.json"

async function fetchAndRender() {
  try {
    const res = await fetch(RESULTS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const container = document.getElementById("tables");
    container.innerHTML = "";

    data.competitions.forEach(comp => {
      // Competition header
      const compTitle = document.createElement("h2");
      compTitle.textContent = comp.competition;
      container.appendChild(compTitle);

      comp.classes.forEach(cls => {
        // Class banner
        const classBanner = document.createElement("h3");
        classBanner.textContent = cls.class_name;
        container.appendChild(classBanner);

        // All-round table (mångkamp)
        const mkTable = document.createElement("table");
        mkTable.innerHTML = `
          <thead>
            <tr class="competition">
              <th>Rank</th><th>Team</th><th>FX</th><th>TU</th><th>TR</th><th>Total</th><th>Gap</th>
            </tr>
          </thead>
          <tbody>
            ${cls.teams
              .map(t => `
                <tr>
                  <td>${t.rank ?? ""}</td>
                  <td>${t.name}</td>
                  <td>${t.fx.score ?? ""}</td>
                  <td>${t.tu.score ?? ""}</td>
                  <td>${t.tr.score ?? ""}</td>
                  <td>${t.total ?? ""}</td>
                  <td>${t.gap ?? ""}</td>
                </tr>
              `).join("")}
          </tbody>
        `;
        container.appendChild(mkTable);

        // Apparatus sections
        const apps = cls.apparatus;
        ["fx","tu","tr"].forEach(appType => {
          if (!apps[appType] || apps[appType].length === 0) return;

          const appTable = document.createElement("table");
          appTable.innerHTML = `
            <thead>
              <tr class="apparatus-header">
                <th colspan="6">${appType.toUpperCase()} Scores</th>
              </tr>
              <tr>
                <th>Rank</th><th>Team</th><th>D</th><th>E</th><th>C</th><th>HJ</th><th>Score</th><th>Gap</th>
              </tr>
            </thead>
            <tbody>
              ${apps[appType]
                .map(t => `
                  <tr>
                    <td>${t.rank ?? ""}</td>
                    <td>${t.name}</td>
                    <td>${t.D ?? ""}</td>
                    <td>${t.E ?? ""}</td>
                    <td>${t.C ?? ""}</td>
                    <td>${t.HJ ?? ""}</td>
                    <td>${t.score ?? ""}</td>
                    <td>${t.gap ?? ""}</td>
                  </tr>
                `).join("")}
            </tbody>
          `;
          container.appendChild(appTable);
        });
      });
    });
    
  } catch (err) {
    console.error("Error fetching or rendering:", err);
    document.getElementById("tables").textContent = "Failed to load data.";
  }
}

fetchAndRender();
