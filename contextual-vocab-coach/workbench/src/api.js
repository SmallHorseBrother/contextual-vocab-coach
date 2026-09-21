async function request(path, options = {}) {
  try {
    const response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const contentType = response.headers.get("content-type") || "";
    if (!response.ok || !contentType.includes("application/json")) return null;
    return await response.json();
  } catch {
    return null;
  }
}

export function fetchWorkbenchState() {
  return request("/api/state");
}

export function decideCandidate(itemId, decision) {
  return request("/api/decision", { method: "POST", body: JSON.stringify({ item_id: itemId, decision }) });
}

export function recordReview(itemId, mode, feedback, responseMs = null) {
  return request("/api/review", {
    method: "POST",
    body: JSON.stringify({ item_id: itemId, mode, feedback, response_ms: responseMs, strategy: "workbench-active-recall", personalized: true }),
  });
}

export function setSourceStatus(sourceId, status) {
  return request("/api/source-status", { method: "POST", body: JSON.stringify({ source_id: sourceId, status }) });
}

export function addLibraryEntry(entryId, decision = "learning") {
  return request("/api/library-decision", {
    method: "POST",
    body: JSON.stringify({ entry_id: entryId, decision }),
  });
}
