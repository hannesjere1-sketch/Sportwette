const portalUrlInput = document.getElementById("portalUrl");
const apiKeyInput = document.getElementById("apiKey");
const statusEl = document.getElementById("status");

function normalizeUrl(url) {
  return url.trim().replace(/\/+$/, "");
}

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind ?? "";
}

async function load() {
  const { portalUrl, apiKey } = await chrome.storage.sync.get(["portalUrl", "apiKey"]);
  if (portalUrl) portalUrlInput.value = portalUrl;
  if (apiKey) apiKeyInput.value = apiKey;
}

document.getElementById("save").addEventListener("click", async () => {
  const portalUrl = normalizeUrl(portalUrlInput.value);
  const apiKey = apiKeyInput.value.trim();

  if (!portalUrl || !apiKey) {
    setStatus("Bitte Portal-URL und API-Key ausfüllen.", "error");
    return;
  }

  try {
    const granted = await chrome.permissions.request({ origins: [`${portalUrl}/*`] });
    if (!granted) {
      setStatus("Berechtigung für die Portal-URL wurde nicht erteilt.", "error");
      return;
    }
  } catch {
    setStatus("Ungültige Portal-URL.", "error");
    return;
  }

  await chrome.storage.sync.set({ portalUrl, apiKey });
  setStatus("Gespeichert.", "ok");
});

document.getElementById("test").addEventListener("click", async () => {
  const portalUrl = normalizeUrl(portalUrlInput.value);
  const apiKey = apiKeyInput.value.trim();

  if (!portalUrl || !apiKey) {
    setStatus("Bitte Portal-URL und API-Key ausfüllen.", "error");
    return;
  }

  setStatus("Teste Verbindung…", null);
  try {
    const res = await fetch(`${portalUrl}/api/bets/import`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (res.ok) {
      setStatus("Verbindung erfolgreich.", "ok");
    } else {
      const body = await res.json().catch(() => ({}));
      setStatus(`Fehler: ${body.error ?? res.status}`, "error");
    }
  } catch (err) {
    setStatus(`Verbindung fehlgeschlagen: ${err instanceof Error ? err.message : String(err)}`, "error");
  }
});

load();
