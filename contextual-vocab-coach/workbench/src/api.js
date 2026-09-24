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

export function scanCodexContext() {
  return request("/api/context-scan", { method: "POST", body: "{}" });
}

export function selectContextTopic(topicId) {
  return request("/api/context-topic", {
    method: "POST",
    body: JSON.stringify({ topic_id: topicId }),
  });
}

export function updateGraphRelation(edgeId, action, type = null) {
  return request("/api/graph/relation", {
    method: "POST",
    body: JSON.stringify({ edge_id: edgeId, action, type }),
  });
}

export function markGraphSeen(nodeIds = null) {
  return request("/api/graph/seen", {
    method: "POST",
    body: JSON.stringify({ node_ids: nodeIds }),
  });
}

export function addGraphExpression(term, meaning, topicId = "") {
  return request("/api/graph/add", {
    method: "POST",
    body: JSON.stringify({ term, meaning, topic_id: topicId }),
  });
}

export function appendPersonalContext(label, text) {
  return request("/api/personal-context", {
    method: "POST",
    body: JSON.stringify({ label, text }),
  });
}

export function setVocabularyTarget(target) {
  return request("/api/vocabulary-target", {
    method: "POST",
    body: JSON.stringify({ target }),
  });
}
