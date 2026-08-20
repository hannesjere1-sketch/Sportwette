function el(id) {
  return document.getElementById(id);
}

function setStatus(text, kind) {
  const s = el("status");
  s.textContent = text;
  s.className = kind ?? "";
}

function defaultMatchDate() {
  const d = new Date(Date.now() + 2 * 60 * 60 * 1000); // best-effort default: kickoff in ~2h
  d.setSeconds(0, 0);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fillForm(data) {
  if (data.league) el("league").value = data.league;
  if (data.homeTeam) el("homeTeam").value = data.homeTeam;
  if (data.awayTeam) el("awayTeam").value = data.awayTeam;
  if (data.market) el("market").value = data.market;
  if (data.selection) el("selection").value = data.selection;
  if (data.odds) el("odds").value = data.odds;
  if (data.stake) el("stake").value = data.stake;
  if (!el("matchDate").value) el("matchDate").value = defaultMatchDate();
}

/**
 * Runs inside the Tipico tab via chrome.scripting.executeScript.
 * Best-effort heuristic extraction — Tipico's DOM/labels aren't verified here,
 * so results are pre-filled but always meant to be reviewed before sending.
 * Must be fully self-contained (no closures over outer scope).
 */
function extractBetSlip() {
  function text(elm) {
    return (elm && elm.innerText ? elm.innerText : "").trim();
  }

  const bodyText = document.body.innerText || "";
  const result = { league: "", homeTeam: "", awayTeam: "", market: "", selection: "", odds: "", stake: "" };

  const oddsMatch = bodyText.match(/Quote[^\d]{0,12}(\d+[.,]\d{2})/i);
  if (oddsMatch) result.odds = oddsMatch[1].replace(",", ".");

  const stakeMatch = bodyText.match(/Einsatz[^\d]{0,12}(\d+[.,]\d{2})/i);
  if (stakeMatch) {
    result.stake = stakeMatch[1].replace(",", ".");
  } else {
    const stakeInput = document.querySelector(
      'input[name*="stake" i], input[name*="einsatz" i], input[id*="stake" i], input[id*="einsatz" i]',
    );
    if (stakeInput && stakeInput.value) result.stake = String(stakeInput.value).replace(",", ".");
  }

  const lines = bodyText
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  const vsLine = lines.find((l) => (/ - | vs\.? /i.test(l)) && l.length < 80 && !/€|Quote|Einsatz/i.test(l));
  if (vsLine) {
    const parts = vsLine.split(/ - | vs\.? /i);
    if (parts.length === 2) {
      result.homeTeam = parts[0].trim();
      result.awayTeam = parts[1].trim();
    }
  }

  const selectedEl = document.querySelector(
    '[class*="selected" i], [class*="active" i][class*="outcome" i], [class*="active" i][class*="pick" i]',
  );
  if (selectedEl) result.selection = text(selectedEl);

  const breadcrumb = document.querySelector('[class*="breadcrumb" i], [class*="competition" i], [class*="league" i]');
  if (breadcrumb) result.league = text(breadcrumb);

  return result;
}

async function tryAutoFill() {
  setStatus("Lese Wettschein…", null);
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      setStatus("Kein aktiver Tab gefunden. Bitte Felder manuell ausfüllen.", "error");
      return;
    }
    const [{ result }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: extractBetSlip });
    fillForm(result || {});
    setStatus("Automatisch erkannte Felder bitte prüfen.", null);
  } catch {
    setStatus("Konnte Seite nicht automatisch auslesen — bitte Felder manuell ausfüllen.", "error");
  }
  if (!el("matchDate").value) el("matchDate").value = defaultMatchDate();
}

async function send() {
  const { portalUrl, apiKey } = await chrome.storage.sync.get(["portalUrl", "apiKey"]);
  if (!portalUrl || !apiKey) {
    setStatus("Bitte zuerst Portal-URL und API-Key in den Erweiterungs-Einstellungen hinterlegen.", "error");
    return;
  }

  const payload = {
    league: el("league").value.trim(),
    homeTeam: el("homeTeam").value.trim(),
    awayTeam: el("awayTeam").value.trim(),
    matchDate: el("matchDate").value ? new Date(el("matchDate").value).toISOString() : "",
    market: el("market").value.trim(),
    selection: el("selection").value.trim(),
    odds: Number(el("odds").value),
    stake: Number(el("stake").value),
    notes: el("notes").value.trim() || undefined,
  };

  for (const required of ["league", "homeTeam", "awayTeam", "matchDate", "market", "selection"]) {
    if (!payload[required]) {
      setStatus(`Bitte "${required}" ausfüllen.`, "error");
      return;
    }
  }
  if (!(payload.odds > 1)) {
    setStatus("Quote muss größer als 1 sein.", "error");
    return;
  }
  if (!(payload.stake > 0)) {
    setStatus("Einsatz muss größer als 0 sein.", "error");
    return;
  }

  setStatus("Sende…", null);
  try {
    const res = await fetch(`${portalUrl}/api/bets/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(payload),
    });
    const body = await res.json().catch(() => ({}));
    if (res.ok && body.ok) {
      setStatus("Wette im Portal angelegt.", "ok");
    } else {
      setStatus(`Fehler: ${body.error ?? res.status}`, "error");
    }
  } catch (err) {
    setStatus(`Senden fehlgeschlagen: ${err instanceof Error ? err.message : String(err)}`, "error");
  }
}

async function init() {
  const { portalUrl, apiKey } = await chrome.storage.sync.get(["portalUrl", "apiKey"]);
  if (!portalUrl || !apiKey) {
    el("setup-notice").style.display = "block";
    el("form-area").classList.add("hidden");
    el("open-options").addEventListener("click", (e) => {
      e.preventDefault();
      chrome.runtime.openOptionsPage();
    });
    return;
  }

  el("send").addEventListener("click", send);
  el("rescan").addEventListener("click", tryAutoFill);
  await tryAutoFill();
}

init();
