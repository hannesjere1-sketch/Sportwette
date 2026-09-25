function el(id) {
  return document.getElementById(id);
}

function setStatus(text, kind) {
  const s = el("status");
  s.textContent = text;
  s.className = kind ?? "";
}

function parseWatchlist(text) {
  return text
    .split("\n")
    .map((l) => l.trim().match(/^(\d+)\s*(.*)$/))
    .filter(Boolean)
    .map((m) => ({ id: Number(m[1]), name: m[2] || m[1] }));
}

async function render() {
  const c = await chrome.storage.local.get(["watchlist", "year", "readings", "lastRun"]);
  const watchlist = c.watchlist ?? (await chrome.runtime.sendMessage("defaults"));
  el("watchlist").value = watchlist.map((p) => `${p.id} ${p.name}`).join("\n");
  el("year").value = c.year ?? 27;

  const readings = c.readings ?? [];
  const first = readings.length ? readings.reduce((m, r) => Math.min(m, r.t), Infinity) : null;
  el("summary").textContent = readings.length
    ? `${readings.length} Preise seit ${new Date(first).toLocaleString("de-DE")}`
    : "Noch keine Preise gesammelt.";

  if (c.lastRun) {
    const when = new Date(c.lastRun.at).toLocaleString("de-DE");
    const errs = c.lastRun.errors ?? [];
    setStatus(
      `Letzter Abruf ${when}: ${c.lastRun.added} neue Preise` +
        (errs.length ? `\n${errs.length} Fehler, z. B. ${errs[0]}` +
          (errs.some((e) => e.includes("403")) ? "\n→ fut.gg einmal normal im Browser öffnen (Cloudflare-Check), dann erneut abrufen." : "")
          : ""),
      errs.length ? "error" : "",
    );
  }
}

el("save").addEventListener("click", async () => {
  const watchlist = parseWatchlist(el("watchlist").value);
  await chrome.storage.local.set({ watchlist, year: Number(el("year").value) || 27 });
  setStatus(`${watchlist.length} Karten gespeichert.`);
});

el("poll").addEventListener("click", async () => {
  setStatus("Rufe Preise ab …");
  await chrome.runtime.sendMessage("poll");
  await render();
});

el("export").addEventListener("click", async () => {
  const { readings = [] } = await chrome.storage.local.get("readings");
  const esc = (s) => `"${String(s).replace(/"/g, '""')}"`;
  const lines = ["timestamp,player_id,name,price"].concat(
    readings
      .slice()
      .sort((a, b) => a.t - b.t)
      .map((r) => [new Date(r.t).toISOString(), r.id, esc(r.name), r.price].join(",")),
  );
  const url = URL.createObjectURL(new Blob([lines.join("\n") + "\n"], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `fut-preise-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

el("clear").addEventListener("click", async () => {
  if (!confirm("Alle gesammelten Preise löschen?")) return;
  await chrome.storage.local.remove(["readings", "lastRun"]);
  await render();
});

render();
