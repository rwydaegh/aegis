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
    col.appendChild(wrap);
    await page.render({ canvasContext: ctx, viewport }).promise;
  }
}

fetchStateAndConnect().catch((e) => {
  document.body.innerHTML = `<pre>error: ${e.message}</pre>`;
});
