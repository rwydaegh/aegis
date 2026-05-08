import * as pdfjsLib from "/pdfjs/build/pdf.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdfjs/build/pdf.worker.mjs";

const annotations = new Map();
let serverInstanceId = null;
let lastSeq = 0;
let currentPass = 1;
let inFlight = false;
let currentTool = "pen";
let ws = null;

const PENDING_KEY = "circa_pending_v1";
function savePending() {
  const out = [...annotations.values()].filter((a) => a.status === "pending" && a.text);
  try { localStorage.setItem(PENDING_KEY, JSON.stringify(out)); } catch (_) {}
}
function loadPendingFromStorage() {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (_) { return []; }
}

async function fetchStateAndConnect() {
  const r = await fetch("/state");
  const data = await r.json();
  if (serverInstanceId !== data.server_instance_id) {
    serverInstanceId = data.server_instance_id;
    lastSeq = 0;
  } else {
    lastSeq = data.last_seq;
  }
  currentPass = data.pass;
  inFlight = data.in_flight;
  setBuildStatus(data.build_status?.ok !== false, data.build_status?.error_tail || "");
  document.getElementById("pass-label").textContent = `pass ${currentPass}`;
  document.getElementById("diff-content").textContent = data.current_diff || "";
  // Render the PDF before annotations so the page-wrap divs exist for renderAnnotation.
  if (!document.querySelector(".page-wrap")) {
    await loadAndRender();
  }
  for (const a of data.annotations) {
    annotations.set(a.id, a);
    renderAnnotation(a);
  }
  // Restore client-only pending annotations (drawn but never reached the server).
  const serverIds = new Set(data.annotations.map((a) => a.id));
  for (const a of loadPendingFromStorage()) {
    if (!serverIds.has(a.id)) {
      annotations.set(a.id, a);
      renderAnnotation(a);
    }
  }
  updateQueueBadge();
  ws = new WebSocket(`ws://${location.host}/stream`);
  ws.onmessage = (ev) => handleWsMessage(JSON.parse(ev.data));
  ws.onopen = () => setWsStatus("up");
  ws.onclose = () => {
    setWsStatus("down");
    setTimeout(fetchStateAndConnect, 1000);
  };
  ws.onerror = () => setWsStatus("down");
}

function setWsStatus(s) {
  const el = document.getElementById("status-ws");
  if (!el) return;
  el.classList.remove("ws-up", "ws-down", "ws-unknown");
  el.classList.add(s === "up" ? "ws-up" : s === "down" ? "ws-down" : "ws-unknown");
  el.textContent = s === "up" ? "ws: ok" : s === "down" ? "ws: DISCONNECTED" : "ws: ...";
}

function flashToast(msg, kind = "info") {
  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

function handleWsMessage(m) {
  if (m.seq && m.seq <= lastSeq) return;
  if (m.seq) lastSeq = m.seq;
  if (m.type === "annotation_status") {
    const a = annotations.get(m.id) || { id: m.id };
    a.status = m.status;
    if (m.one_liner) a.one_liner = m.one_liner;
    if (m.clarification) a.clarification = m.clarification;
    annotations.set(m.id, a);
    renderAnnotation(a);
    inFlight = [...annotations.values()].some((x) => x.status === "in_progress");
    updateQueueBadge();
    savePending();
  } else if (m.type === "diff_update") {
    document.getElementById("diff-content").textContent = m.hunk || "";
  } else if (m.type === "build_status") {
    setBuildStatus(m.ok, m.error_tail);
  } else if (m.type === "pdf_reloaded") {
    // Keep all annotations across rebuild — they remain visible (in their stale positions)
    // until the user explicitly clears them via the "Clear old" button.
    currentPass = m.pass;
    document.getElementById("pass-label").textContent = `pass ${currentPass}`;
    reloadPdfPages();
  } else if (m.type === "annotations_cleared") {
    for (const id of m.ids || []) {
      const g = document.querySelector(`g[data-id="${id}"]`);
      if (g) g.remove();
      annotations.delete(id);
    }
    updateQueueBadge();
  }
}

function setBuildStatus(ok, errorTail) {
  const el = document.getElementById("status-build");
  el.textContent = "build: " + (ok ? "ok" : "broken");
  el.className = ok ? "ok" : "fail";
  if (!ok && errorTail) el.title = errorTail;
}

async function reloadPdfPages() {
  document.getElementById("pdf-col").innerHTML = "";
  await loadAndRender();
  // Re-render any surviving annotations onto the new pages.
  for (const a of annotations.values()) renderAnnotation(a);
}

function renderAnnotation(a) {
  const wrap = document.querySelector(`.page-wrap[data-page-num="${a.page}"]`);
  if (!wrap) return;
  const svg = wrap.querySelector("svg.overlay");
  let g = svg.querySelector(`g[data-id="${a.id}"]`);
  if (!g) {
    g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("data-id", a.id);
    svg.appendChild(g);
  }
  g.innerHTML = "";
  const w = parseFloat(wrap.style.width), h = parseFloat(wrap.style.height);
  const colorClass = a.status === "done" ? "grey"
    : a.status === "in_progress" ? "amber"
    : a.status === "needs_clarification" ? "" : "";

  if (a.shape === "pen") {
    const poly = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    poly.setAttribute("class", `shape ${colorClass}`);
    poly.setAttribute("fill", "none");
    poly.setAttribute("stroke-width", "2");
    poly.setAttribute("points", a.points.map(([x, y]) => `${x * w},${y * h}`).join(" "));
    g.appendChild(poly);
  } else if (a.shape === "arrow") {
    const [s, e] = a.points;
    const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
    ln.setAttribute("class", `shape ${colorClass}`);
    ln.setAttribute("x1", s[0] * w); ln.setAttribute("y1", s[1] * h);
    ln.setAttribute("x2", e[0] * w); ln.setAttribute("y2", e[1] * h);
    ln.setAttribute("stroke-width", "2");
    ln.setAttribute("marker-end", "url(#arrowhead)");
    g.appendChild(ln);
  } else if (a.shape === "rect") {
    const [tl, br] = a.points;
    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("class", `shape ${colorClass}`);
    r.setAttribute("x", tl[0] * w); r.setAttribute("y", tl[1] * h);
    r.setAttribute("width", (br[0] - tl[0]) * w); r.setAttribute("height", (br[1] - tl[1]) * h);
    g.appendChild(r);
  } else if (a.shape === "text") {
    const [p] = a.points;
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("class", `shape ${colorClass}`);
    c.setAttribute("fill", "currentColor");
    c.setAttribute("cx", p[0] * w); c.setAttribute("cy", p[1] * h); c.setAttribute("r", "5");
    g.appendChild(c);
  }

  // Status pill at bbox top-right.
  const allPts = a.points;
  const px = allPts.map((p) => Array.isArray(p) ? p[0] : p);
  const py = allPts.map((p) => Array.isArray(p) ? p[1] : p);
  const px0 = Math.max(...px) * w, py0 = Math.min(...py) * h;
  const fo = document.createElementNS("http://www.w3.org/2000/svg", "foreignObject");
  fo.setAttribute("x", px0); fo.setAttribute("y", py0 - 18);
  fo.setAttribute("width", "120"); fo.setAttribute("height", "20");
  const div = document.createElement("div");
  div.className = `status-pill ${colorClass}`;
  div.textContent = a.one_liner ? `\u2713 ${a.one_liner.slice(0, 18)}` : (a.status === "needs_clarification" ? "?" : "\u2022");
  div.title = a.one_liner || a.clarification || a.text || "";
  div.addEventListener("click", () => openPillPopover(a));
  fo.appendChild(div);
  g.appendChild(fo);

  if (a.status === "needs_clarification" && a.clarification) {
    spawnSpeechBubble(wrap, a);
  }
}

function openPillPopover(a) {
  const action = window.prompt(
    `${a.text || "(no note)"}\n\nClaude: ${a.one_liner || a.clarification || ""}\n\nType: 'r' to reject, 'e' to re-edit text, anything else to close`,
    "",
  );
  if (action === "r") {
    fetch(`/reject/${a.id}`, { method: "POST" }).then((r) => {
      if (!r.ok) r.json().then((d) => alert(d.reason || "reject failed"));
    });
  } else if (action === "e") {
    const wrap = document.querySelector(`.page-wrap[data-page-num="${a.page}"]`);
    spawnTextbox(wrap.querySelector("svg.overlay"), wrap, a);
  }
}

function spawnSpeechBubble(wrap, a) {
  const existing = document.querySelector(`.bubble[data-for="${a.id}"]`);
  if (existing) existing.remove();
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.dataset.for = a.id;
  bubble.innerHTML = `<div><strong>Claude:</strong> ${escapeHtml(a.clarification)}</div>`;
  const reply = document.createElement("input");
  reply.type = "text";
  reply.placeholder = "reply (Enter to send, Esc to hide)";
  reply.style.marginTop = ".25rem";
  reply.style.width = "100%";
  bubble.appendChild(reply);
  const dismiss = document.createElement("button");
  dismiss.textContent = "Dismiss";
  dismiss.title = "Drop this question without replying. Claude won't be asked again.";
  dismiss.style.marginTop = ".25rem";
  dismiss.addEventListener("click", async () => {
    await fetch(`/dismiss/${a.id}`, { method: "POST" });
    bubble.remove();
  });
  bubble.appendChild(dismiss);
  const xs = a.points.flatMap((p) => Array.isArray(p) ? [p[0]] : [p]);
  const ys = a.points.flatMap((p) => Array.isArray(p) ? [p[1]] : [p]);
  const w = parseFloat(wrap.style.width), h = parseFloat(wrap.style.height);
  bubble.style.left = (wrap.offsetLeft + Math.max(...xs) * w + 8) + "px";
  bubble.style.top = (wrap.offsetTop + Math.min(...ys) * h) + "px";
  document.body.appendChild(bubble);
  reply.focus();
  reply.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { bubble.remove(); return; }
    if (e.key === "Enter" && reply.value.trim()) {
      ws.send(JSON.stringify({ type: "clarification_reply", annotation_id: a.id, reply: reply.value.trim() }));
      bubble.remove();
    }
  });
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}

let idleTimer = null;
const FLUSH_MS = 5000;

function noteActivity() {
  if (idleTimer) clearTimeout(idleTimer);
  idleTimer = setTimeout(maybeFlush, FLUSH_MS);
}

async function compositePage(wrap) {
  const canvas = wrap.querySelector("canvas");
  const svg = wrap.querySelector("svg.overlay");
  const out = document.createElement("canvas");
  out.width = canvas.width;
  out.height = canvas.height;
  const ctx = out.getContext("2d");
  ctx.drawImage(canvas, 0, 0);
  if (svg) {
    const svgClone = svg.cloneNode(true);
    svgClone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    svgClone.setAttribute("width", canvas.width);
    svgClone.setAttribute("height", canvas.height);
    const xml = new XMLSerializer().serializeToString(svgClone);
    const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
    await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => { ctx.drawImage(img, 0, 0, canvas.width, canvas.height); resolve(); };
      img.onerror = reject;
      img.src = url;
    });
  }
  return out.toDataURL("image/png").split(",")[1];
}

async function maybeFlush({ force = false } = {}) {
  const pending = [...annotations.values()].filter((a) => a.status === "pending" && a.text);
  if (pending.length === 0) return;
  if (!force && inFlight) return;
  if (!ws || ws.readyState !== 1) {
    if (force) flashToast("WebSocket is down — annotations saved locally. Refresh to reconnect.", "warn");
    return;
  }
  pending.forEach((a) => (a.status = "in_progress"));
  const pages = new Set(pending.map((a) => a.page));
  const page_pngs = {};
  for (const p of pages) {
    const wrap = document.querySelector(`.page-wrap[data-page-num="${p}"]`);
    if (!wrap) continue;
    page_pngs[p] = await compositePage(wrap);
  }
  ws.send(JSON.stringify({
    type: "batch_flush",
    batch_id: crypto.randomUUID(),
    annotations: pending.map(({ ...a }) => ({ ...a, status: "pending" })),
    page_pngs,
  }));
  inFlight = true;
  updateQueueBadge();
}

function setTool(t) {
  currentTool = t;
  document.querySelectorAll("#tools button").forEach((b) =>
    b.classList.toggle("active", b.dataset.tool === t),
  );
}
document.querySelectorAll("#tools button").forEach((btn) => {
  btn.addEventListener("click", () => setTool(btn.dataset.tool));
});
document.getElementById("rebuild-btn").addEventListener("click", triggerRebuild);
document.getElementById("send-now-btn").addEventListener("click", () => {
  if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
  maybeFlush({ force: true });
});
document.getElementById("clear-old-btn").addEventListener("click", async () => {
  await fetch("/clear-old-comments", { method: "POST" });
});

document.addEventListener("keydown", (e) => {
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") return;
  if (e.key === "1") setTool("pen");
  else if (e.key === "2") setTool("arrow");
  else if (e.key === "3") setTool("rect");
  else if (e.key === "4") setTool("text");
  else if (e.key === "r" || e.key === "R") triggerRebuild();
  else if (e.key === "z" || e.key === "Z") confirmUndoLastBatch();
});

async function triggerRebuild() {
  await fetch("/rebuild", { method: "POST" });
}

function confirmUndoLastBatch() {
  alert("Z = undo last batch (not yet wired; use status pill 'reject' on individual annotations)");
}

const PEN_HANDLERS = (svg, wrap) => {
  let drawing = null;
  svg.addEventListener("pointerdown", (e) => {
    if (currentTool !== "pen") return;
    const r = svg.getBoundingClientRect();
    drawing = {
      points: [[(e.clientX - r.left), (e.clientY - r.top)]],
      el: document.createElementNS("http://www.w3.org/2000/svg", "polyline"),
    };
    drawing.el.setAttribute("class", "shape");
    drawing.el.setAttribute("fill", "none");
    drawing.el.setAttribute("stroke", "red");
    drawing.el.setAttribute("stroke-width", "2");
    svg.appendChild(drawing.el);
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener("pointermove", (e) => {
    if (!drawing) return;
    noteActivity();
    const r = svg.getBoundingClientRect();
    drawing.points.push([(e.clientX - r.left), (e.clientY - r.top)]);
    drawing.el.setAttribute("points", drawing.points.map((p) => p.join(",")).join(" "));
  });
  svg.addEventListener("pointerup", (e) => {
    if (!drawing) return;
    finalizeShape(svg, wrap, "pen", drawing.points);
    drawing = null;
  });
};

function finalizeShape(svg, wrap, shape, pixelPoints) {
  const w = parseFloat(wrap.style.width), h = parseFloat(wrap.style.height);
  const points = pixelPoints.map(([x, y]) => [x / w, y / h]);
  const id = crypto.randomUUID();
  const ann = {
    id, page: parseInt(wrap.dataset.pageNum), shape, points,
    text: "", mode: "edit", status: "pending",
    pass: currentPass, created_at: Date.now(),
  };
  annotations.set(id, ann);
  spawnTextbox(svg, wrap, ann);
  noteActivity();
}

function spawnTextbox(svg, wrap, ann) {
  const xs = ann.points.map((p) => p[0]);
  const ys = ann.points.map((p) => p[1]);
  const w = parseFloat(wrap.style.width);
  const h = parseFloat(wrap.style.height);
  const tx = Math.max(...xs) * w + 4;
  const ty = Math.min(...ys) * h;
  const box = document.createElement("textarea");
  box.className = "textbox";
  box.style.left = (wrap.offsetLeft + tx) + "px";
  box.style.top = (wrap.offsetTop + ty) + "px";
  box.placeholder = "note (Enter submits edit, Shift+Enter asks, Ctrl+Enter newline, Esc visual-only)";
  document.body.appendChild(box);
  box.focus();
  box.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { box.remove(); return; }
    if (e.key === "Enter") {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      e.preventDefault();
      ann.text = box.value;
      ann.mode = e.shiftKey ? "ask" : "edit";
      box.remove();
      updateQueueBadge();
      savePending();
      noteActivity();
    }
  });
}

function updateQueueBadge() {
  const pending = [...annotations.values()].filter((a) => a.status === "pending").length;
  document.getElementById("queue-badge").textContent = `${pending} pending`;
}

const ARROW_HANDLERS = (svg, wrap) => {
  let start = null, line = null;
  svg.addEventListener("pointerdown", (e) => {
    if (currentTool !== "arrow") return;
    const r = svg.getBoundingClientRect();
    start = [e.clientX - r.left, e.clientY - r.top];
    line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("class", "shape");
    line.setAttribute("stroke", "red");
    line.setAttribute("stroke-width", "2");
    line.setAttribute("marker-end", "url(#arrowhead)");
    line.setAttribute("x1", start[0]);
    line.setAttribute("y1", start[1]);
    line.setAttribute("x2", start[0]);
    line.setAttribute("y2", start[1]);
    svg.appendChild(line);
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener("pointermove", (e) => {
    if (!line) return;
    noteActivity();
    const r = svg.getBoundingClientRect();
    line.setAttribute("x2", e.clientX - r.left);
    line.setAttribute("y2", e.clientY - r.top);
  });
  svg.addEventListener("pointerup", (e) => {
    if (!start) return;
    const r = svg.getBoundingClientRect();
    const end = [e.clientX - r.left, e.clientY - r.top];
    finalizeShape(svg, wrap, "arrow", [start, end]);
    start = null;
    line = null;
  });
};

const RECT_HANDLERS = (svg, wrap) => {
  let start = null, rect = null;
  svg.addEventListener("pointerdown", (e) => {
    if (currentTool !== "rect") return;
    const r = svg.getBoundingClientRect();
    start = [e.clientX - r.left, e.clientY - r.top];
    rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("class", "shape");
    rect.setAttribute("stroke", "red");
    rect.setAttribute("stroke-width", "2");
    rect.setAttribute("fill", "none");
    rect.setAttribute("x", start[0]);
    rect.setAttribute("y", start[1]);
    rect.setAttribute("width", "0");
    rect.setAttribute("height", "0");
    svg.appendChild(rect);
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener("pointermove", (e) => {
    if (!rect) return;
    noteActivity();
    const r = svg.getBoundingClientRect();
    const x = Math.min(start[0], e.clientX - r.left);
    const y = Math.min(start[1], e.clientY - r.top);
    const w = Math.abs(e.clientX - r.left - start[0]);
    const h = Math.abs(e.clientY - r.top - start[1]);
    rect.setAttribute("x", x);
    rect.setAttribute("y", y);
    rect.setAttribute("width", w);
    rect.setAttribute("height", h);
  });
  svg.addEventListener("pointerup", (e) => {
    if (!start) return;
    const r = svg.getBoundingClientRect();
    finalizeShape(svg, wrap, "rect", [start, [e.clientX - r.left, e.clientY - r.top]]);
    start = null;
    rect = null;
  });
};

const TEXT_HANDLERS = (svg, wrap) => {
  svg.addEventListener("pointerdown", (e) => {
    if (currentTool !== "text") return;
    const r = svg.getBoundingClientRect();
    const pt = [e.clientX - r.left, e.clientY - r.top];
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("class", "shape");
    dot.setAttribute("fill", "red");
    dot.setAttribute("cx", pt[0]);
    dot.setAttribute("cy", pt[1]);
    dot.setAttribute("r", "5");
    svg.appendChild(dot);
    finalizeShape(svg, wrap, "text", [pt]);
  });
};

async function loadAndRender() {
  const pdf = await pdfjsLib.getDocument(`/pdf?v=${currentPass}`).promise;
  const col = document.getElementById("pdf-col");
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const viewport = page.getViewport({ scale: 1.5 });
    const wrap = document.createElement("div");
    wrap.className = "page-wrap";
    wrap.style.width = viewport.width + "px";
    wrap.style.height = viewport.height + "px";
    wrap.dataset.pageNum = String(i);
    const canvas = document.createElement("canvas");
    canvas.width = viewport.width; canvas.height = viewport.height;
    const ctx = canvas.getContext("2d");
    wrap.appendChild(canvas);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "overlay");
    svg.setAttribute("viewBox", `0 0 ${viewport.width} ${viewport.height}`);
    wrap.appendChild(svg);
    // Arrowhead marker for the arrow tool.
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `<marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="red"/></marker>`;
    svg.appendChild(defs);
    PEN_HANDLERS(svg, wrap);
    ARROW_HANDLERS(svg, wrap);
    RECT_HANDLERS(svg, wrap);
    TEXT_HANDLERS(svg, wrap);
    col.appendChild(wrap);
    await page.render({ canvasContext: ctx, viewport }).promise;
  }
}

fetchStateAndConnect().catch((e) => {
  document.body.innerHTML = `<pre>error: ${e.message}</pre>`;
});
