import * as pdfjsLib from "/pdfjs/build/pdf.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdfjs/build/pdf.worker.mjs";

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

loadAndRender().catch((e) => {
  document.body.innerHTML = `<pre>error: ${e.message}</pre>`;
});
