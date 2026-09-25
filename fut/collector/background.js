// Polls FUT.GG for the current price of every card on the watch list and keeps
// each reading as {t, id, name, price}. Runs in the user's own browser on
// purpose: FUT.GG, FUTBIN and FUTWIZ all sit behind Cloudflare, which turns
// away servers and CI runners but lets a normal browser through.

const POLL_MINUTES = 20;
const PAUSE_MS = 1500; // between players — a handful of requests, never a burst

// Popular rare golds of EA FC 27 (FUT.GG ids = EA ids). Editable in the popup.
const DEFAULT_WATCHLIST = [
  [231747, "Kylian Mbappé"], [239085, "Erling Haaland"], [238794, "Vini Jr."],
  [252371, "Jude Bellingham"], [231866, "Rodri"], [202126, "Harry Kane"],
  [203376, "Virgil van Dijk"], [212622, "Joshua Kimmich"], [246669, "Bukayo Saka"],
  [256790, "Jamal Musiala"], [256630, "Florian Wirtz"], [192985, "Kevin De Bruyne"],
  [241721, "Rafael Leão"], [235243, "Matthijs de Ligt"],
].map(([id, name]) => ({ id, name }));

async function getConfig() {
  const c = await chrome.storage.local.get(["watchlist", "year"]);
  return { watchlist: c.watchlist ?? DEFAULT_WATCHLIST, year: c.year ?? 27 };
}

// FUT.GG's price endpoint is unofficial and its shape has shifted between game
// years, so read it defensively: the current price wherever it sits.
function currentPrice(body) {
  const d = body?.data ?? body;
  const candidates = [d?.currentPrice?.price, d?.currentPrice, d?.price, d?.lowestBin];
  for (const v of candidates) {
    const n = Number(v);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
}

// Any history the endpoint ships along is only worth keeping when it is at
// least hourly — daily points would blur the hour-of-day pattern.
function hourlyHistory(body) {
  const d = body?.data ?? body;
  const out = [];
  for (const key of ["history", "priceHistory", "hourly", "hourlyHistory"]) {
    const list = d?.[key];
    if (!Array.isArray(list)) continue;
    for (const p of list) {
      const t = Date.parse(p?.date ?? p?.timestamp ?? p?.t ?? "");
      const price = Number(p?.price ?? p?.value ?? p?.p);
      if (Number.isFinite(t) && Number.isFinite(price) && price > 0) out.push({ t, price });
    }
  }
  out.sort((a, b) => a.t - b.t);
  const gaps = out.slice(1).map((p, i) => p.t - out[i].t);
  const typical = gaps.sort((a, b) => a - b)[Math.floor(gaps.length / 2)];
  return typical && typical <= 90 * 60 * 1000 ? out : [];
}

async function fetchPlayer(year, id) {
  const res = await fetch(`https://www.fut.gg/api/fut/player-prices/${year}/${id}/`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function poll() {
  const { watchlist, year } = await getConfig();
  const { readings = [] } = await chrome.storage.local.get("readings");
  const seen = new Set(readings.map((r) => `${r.id}|${r.t}`));
  const errors = [];
  let added = 0;
  const now = Date.now();

  for (const { id, name } of watchlist) {
    try {
      const body = await fetchPlayer(year, id);
      const points = [...hourlyHistory(body)];
      const price = currentPrice(body);
      if (price) points.push({ t: now, price });
      if (!points.length) errors.push(`${name}: kein Preis in der Antwort`);
      for (const p of points) {
        const key = `${id}|${p.t}`;
        if (seen.has(key)) continue;
        seen.add(key);
        readings.push({ t: p.t, id, name, price: p.price });
        added++;
      }
    } catch (e) {
      errors.push(`${name}: ${e.message}`);
    }
    await new Promise((r) => setTimeout(r, PAUSE_MS));
  }

  await chrome.storage.local.set({
    readings,
    lastRun: { at: now, added, errors },
  });
  return { added, errors };
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("poll", { periodInMinutes: POLL_MINUTES, delayInMinutes: 1 });
});
chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("poll", { periodInMinutes: POLL_MINUTES, delayInMinutes: 1 });
});
chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === "poll") poll();
});
chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg === "poll") {
    poll().then(reply);
    return true; // keep the channel open for the async reply
  }
  if (msg === "defaults") reply(DEFAULT_WATCHLIST);
});
