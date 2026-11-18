// Fetches rankings, players and metrics from the JSON API and renders the page.
(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const f = (v, d = 1) => (v == null ? "–" : Number(v).toFixed(d));
  const pct = (v) => (v == null ? "–" : Math.round(v * 100) + "%");
  const sgn = (v, d = 2) => (v == null ? "–" : (v > 0 ? "+" : "") + Number(v).toFixed(d));
  let kind = "batters";

  async function api(path) {
    const r = await fetch("/api/" + path);
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.statusText);
    return r.json();
  }
  const fail = (el, msg) => { el.innerHTML = `<div class="state">${esc(msg)}</div>`; };

  function card(p) {
    const rows = kind === "batters"
      ? [["Strike rate", f(p.strikeRate)], ["Runs above expected / 100", f(p.rae100)], ["Elevation", sgn(p.elevation)], ["Pressure balls", p.pressureBalls]]
      : [["Economy", f(p.economy, 2)], ["Dot balls", f(p.dotPct) + "%"], ["Runs saved / over", sgn(p.rsePerOver)], ["Pressure balls", p.pressureBalls]];
    const bar = p.pTop10 == null ? "" :
      `<div class="meter">Top 10 chance ${pct(p.pTop10)}<span class="bar"><i style="width:${Math.round(p.pTop10 * 100)}%"></i></span></div>`;
    return `<article class="pc${p.rank <= 3 ? " podium" : ""}"><span class="rk" aria-hidden="true">${p.rank}</span><h3>${esc(p.name)}</h3>
      <dl>${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>${bar}
      </article>`;
  }

  async function loadTop() {
    const grid = $("#topGrid");
    grid.innerHTML = '<div class="state">Loading…</div>';
    try {
      const d = await api("rankings/" + kind + "?limit=10");
      grid.innerHTML = d.players.map(card).join("");
      $("#topNote").textContent = (kind === "batters"
        ? "Elevation is runs above expected on pressure balls minus normal balls, per 100 balls."
        : "Elevation is runs saved above expected per over, pressure minus normal.") + " Rank is the consensus order. Top 10 chance is how often a player stays in the top 10 across 500 resamples, so close ranks can differ.";
    } catch (e) { fail(grid, "Could not load rankings: " + e.message); }
  }

  let timer;
  async function loadAll() {
    const t = $("#allTable");
    try {
      const d = await api(`players/${kind}?q=${encodeURIComponent($("#q").value)}&sort=${$("#sort").value}&limit=200`);
      const head = kind === "batters"
        ? ["#", "Player", "Pressure balls", "Strike rate", "RAE / 100", "Elevation", "Top 10 chance"]
        : ["#", "Player", "Pressure balls", "Economy", "Dot %", "Runs saved / over", "Top 10 chance"];
      const body = d.players.map((p, i) => kind === "batters"
        ? [i + 1, p.name, p.pressureBalls, f(p.strikeRate), f(p.rae100), sgn(p.elevation), pct(p.pTop10)]
        : [i + 1, p.name, p.pressureBalls, f(p.economy, 2), f(p.dotPct), sgn(p.rsePerOver), pct(p.pTop10)]);
      t.innerHTML = "<tr>" + head.map((h, i) => `<th class="${i > 1 ? "r" : ""}">${h}</th>`).join("") + "</tr>" +
        (body.length ? body.map((r) => "<tr>" + r.map((c, i) => `<td class="${i === 0 ? "rk" : i === 1 ? "nm" : "r"}">${esc(c)}</td>`).join("") + "</tr>").join("")
          : `<tr><td colspan="7" class="state">No player matches that search.</td></tr>`);
      $("#allNote").textContent = `${d.count} players shown.`;
    } catch (e) { t.innerHTML = `<tr><td class="state">Could not load players: ${esc(e.message)}</td></tr>`; }
  }

  async function loadMetrics() {
    try {
      const m = await api("metrics");
      const stats = [[m.matches.toLocaleString(), "matches analysed"], [(Math.round(m.deliveries / 1000)) + "k", "deliveries scored"],
        [Math.round(m.pressureShare * 100) + "%", "of balls flagged as pressure"], [m.bootstrapResamples, "bootstrap resamples"]];
      $("#heroStats").innerHTML = stats.map(([b, s]) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join("");
      const ratio = m.swing.pressure / m.swing.normal;
      $("#tiles").innerHTML = [
        [ratio.toFixed(1) + "x", `larger average win-probability swing (${m.swing.pressure.toFixed(3)} against ${m.swing.normal.toFixed(3)})`],
        [pct(m.profile.closeContest[1]), `of pressure balls are in contests between 25% and 75% win probability (${pct(m.profile.closeContest[0])} for ordinary balls)`],
        [pct(m.profile.deathOvers[1]), `of pressure balls fall in overs 16 to 20 (${pct(m.profile.deathOvers[0])} for ordinary balls)`],
      ].map(([b, p]) => `<div class="card tile"><b>${b}</b><p>${p}</p></div>`).join("");
      const r = m.reliability;
      $("#reliab").innerHTML = [["Batter strike rate", r.batterStrikeRate], ["Batter WPA / 100", r.batterWpa], ["Bowler economy", r.bowlerEconomy]]
        .map(([n, v]) => `<div class="rel"><span>${n}</span><span class="bar"><i style="width:${Math.max(0, Math.min(1, v)) * 100}%"></i></span><b>${v.toFixed(2)}</b></div>`).join("");
    } catch (e) { fail($("#tiles"), "Could not load metrics: " + e.message); }
  }

  async function loadMethod() {
    try {
      const d = await api("method");
      const face = (title, text, hint) => `<h3>${esc(title)}</h3><p>${esc(text)}</p><span class="hint">${hint}</span>`;
      const back = (x) => `<b>Why we do this</b><p>${esc(x.why || "")}</p><ul>${(x.evidence || []).map((e) => `<li>${esc(e)}</li>`).join("")}</ul><span class="hint">Back ↻</span>`;
      const flip = (cls, x, n) => `<${cls.tag} class="${cls.cls} flip" tabindex="0" role="button" aria-pressed="false">
        <div class="flip-inner"><div class="face front"><span class="num">${n}</span>${face(x.title, x.text, "Why? ↻")}</div>
        <div class="face back" aria-hidden="true">${back(x)}</div></div></${cls.tag}>`;
      $("#steps").innerHTML = (d.steps || []).map((s, i) => flip({ tag: "li", cls: "step" }, s, i + 1)).join("");
      $("#uniqueGrid").innerHTML = (d.unique || []).map((u) => `<article class="uc"><span class="chip">${esc(u.concept ?? "")}</span><h3>${esc(u.title ?? "")}</h3><p>${esc(u.text ?? "")}</p>${u.detail ? `<p class="more">${esc(u.detail)}</p>` : ""}</article>`).join("");
      document.querySelectorAll(".flip").forEach((el) => {
        const toggle = () => {
          const on = el.classList.toggle("flipped");
          el.setAttribute("aria-pressed", on);
          el.querySelector(".back").setAttribute("aria-hidden", !on);
          el.querySelector(".front").setAttribute("aria-hidden", on);
        };
        el.addEventListener("click", toggle);
        el.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggle(); } });
      });
    } catch (e) { fail($("#steps"), "Could not load method: " + e.message); }
  }

  document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
    kind = b.dataset.kind;
    document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-selected", x === b));
    loadTop(); loadAll();
  }));
  $("#q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(loadAll, 200); });
  $("#sort").addEventListener("change", loadAll);
  // highlight the nav link of the section currently in view
  const links = [...document.querySelectorAll(".links a")];
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + en.target.id));
    }), { rootMargin: "-45% 0px -50% 0px" });
    document.querySelectorAll("main section").forEach((sec) => io.observe(sec));
  }
  loadTop(); loadAll(); loadMetrics(); loadMethod();
})();
