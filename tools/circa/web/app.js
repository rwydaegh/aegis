import * as pdfjsLib from "/pdfjs/build/pdf.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdfjs/build/pdf.worker.mjs";

const annotations = new Map();
let serverInstanceId = null;
let lastSeq = 0;
let currentPass = 1;
let inFlight = false;
let currentTool = "pen";
let ws = null;

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
  for (const a of data.annotations) {
    annotations.set(a.id, a);
    renderAnnotation(a);
  }
  ws = new WebSocket(`ws://${location.host}/stream`);
  ws.onmessage = (ev) => handleWsMessage(JSON.parse(ev.data));
  ws.onclose = () => setTimeout(fetchStateAndConnect, 1000);
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
  } else if (m.type === "diff_update") {
    document.getElementById("diff-content").textContent = m.hunk || "";
  } else if (m.type === "build_status") {
    setBuildStatus(m.ok, m.error_tail);
  } else if (m.type === "pdf_reloaded") {
    // Drop annotations from earlier passes; reload PDF without losing pending ones.
    for (const [id, a] of [...annotations]) {
      if (a.pass < m.pass) {
        const g = document.querySelector(`g[data-id="${id}"]`);
        if (g) g.remove();
        annotations.delete(id);
      }
    }
    currentPass = m.pass;
    document.getElementById("pass-label").textContent = `pass ${currentPass}`;
    reloadPdfPages();  // implementation below
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

function renderAnnotation(_a) { /* implemented in Task 17 */ }

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
  const box = document.createElement("input");
  box.type = "text";
  box.className = "textbox";
  box.style.left = (wrap.offsetLeft + tx) + "px";
  box.style.top = (wrap.offsetTop + ty) + "px";
  box.placeholder = "note (Enter to submit, Esc visual-only, Shift+Enter to ask)";
  document.body.appendChild(box);
  box.focus();
  box.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { box.remove(); return; }
    if (e.key === "Enter") {
      ann.text = box.value;
      ann.mode = e.shiftKey ? "ask" : "edit";
      box.remove();
      updateQueueBadge();
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
  const pdf = await pdfjsLib.getDocument("/pdf").promise;
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
