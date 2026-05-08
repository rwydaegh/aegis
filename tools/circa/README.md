# Circa

Circa is a browser-based PDF annotation tool for academic papers. Open a compiled PDF in the browser, click anywhere on the page to leave a comment, and circa streams the annotation to a Claude agent that reads the surrounding LaTeX source and suggests edits. All annotations and snapshots are stored locally in a `.circa/` directory next to your paper.

## Usage

```bash
pip install -e ".[dev]"
circa serve <paper_dir>
```
