# Frontend overhaul: agent prompts

These prompts describe UI/UX improvements for the AEGIS viewer frontend (`aegis-web/`). Each prompt is a self-contained task for an agent. They should be executed roughly in order, since later tasks build on earlier ones.

Context: the AEGIS viewer is a 3D dosimetry visualization tool. It has a React + Three.js frontend with a left sidebar containing 14 accordion sections, a toolbar, floating HUD overlays, and a full-viewport 3D scene. The current design is functional and visually solid (dark theme, glass morphism, good typography), but the information architecture needs work. The sidebar is a flat list of 14 equally-weighted sections with no hierarchy, no icons, and no grouping.

---

## 1. Sidebar section icons

Every accordion section in the sidebar currently has only a text label. Add an appropriate icon to each section header, placed to the left of the label text. Use lucide-react icons (already in the project) where a good match exists. For any section where no lucide icon fits well, design a simple SVG icon that matches the lucide style (24x24, 2px stroke, round caps/joins, no fill).

The 14 sections are: Parameters, Analysis, Environment, Scene, MIMO, Optimize, Base Stations, Phantom, Layers, Ray Tracing, Stochastic, Tissue, Antenna Patterns, Export.

Pick icons that are immediately recognizable and help users scan the sidebar faster. The icon should communicate what the section does, not just be decorative.

---

## 2. Sidebar grouping and navigation redesign

This is the most important task. The sidebar currently has 14 accordion sections in a flat list. This needs to be reorganized into a small number of major groups (3-4) that reflect how users actually think about their workflow.

Do NOT use "primary vs advanced" or "basic vs expert" grouping. Instead, think about functional categories along the workflow. For inspiration, think about how simulation tools organize around phases like setup, configure, run, analyze -- but find the grouping that actually fits AEGIS's specific workflow. Study the panels, understand what each one does, and figure out which ones belong together.

The visual treatment of these groups should be ambitious. This is a chance to improve the entire sidebar experience. Think about how the groups are presented, how users navigate between them, and how the sidebar feels to use. Consider tab-like navigation, segmented headers, or other patterns that make the groups feel like distinct workspaces rather than just labeled dividers.

The current sidebar is 320px wide and takes significant screen real estate. As part of this redesign, consider whether the sidebar can be made more compact or whether a collapsible icon-rail mode (around 48px) would work, where clicking an icon expands just that group's panel. The goal is to give more of the viewport back to the 3D scene when the user isn't actively changing settings.

Whatever you design, it should still work on mobile where the sidebar currently fills 100vw. Don't break that. Animations and transitions should feel polished.

---

## 3. Camera presets: move to 3D viewport

The camera preset buttons (Front, Side, Top, Focus, Follow, Globe) are currently in the main toolbar. They belong closer to the 3D scene since they directly control the viewport. Move them to a small floating widget positioned near or over the 3D canvas, similar to how 3D modeling tools place viewport controls as an overlay on the viewport itself.

The toolbar should NOT lose any functionality. Everything that is currently accessible must remain accessible. This task is about relocating camera controls, not removing features from the toolbar. After moving camera presets out, clean up the toolbar spacing so it looks intentional, not like something was removed.

---

## 4. Compliance panel styling

The CompliancePanel HUD overlay currently uses inline styles (`style={{...}}`) while every other component in the app uses Tailwind CSS. Convert it to use Tailwind classes consistent with the rest of the app's design system. The panel should look cohesive with the other HUD elements (StatusBar, ColorLegend, ServerInfoBadge) which all use the glass morphism pattern (`bg-card/80 backdrop-blur-md border border-border rounded-lg`).

Preserve all existing functionality: the compliance checks with progress bars, the PASS/WARN/FAIL color coding, the margin and max TX power readout, the clickable max-power action, and the shimmer animation during compute. The data should still be displayed in monospace for numeric alignment, but using the project's font-mono utility rather than inline fontFamily.

---

## 5. Antenna hint: slightly larger

The "Click to place antenna" hint at the bottom of the 3D viewport is a bit too subtle. Make the text slightly larger and ensure it's clearly visible against the 3D scene background. Don't overdo it -- it's not broken, just a touch too small. A modest increase in font size and perhaps slightly stronger contrast is all that's needed.

---

## 6. Guided tour (after UI overhaul)

**Run this AFTER tasks 1-5 are complete.** The app has a lot of features and no onboarding beyond the welcome overlay scenario picker. Design and implement a lightweight guided tour that walks first-time users through the core workflow:

1. Place an antenna (click the scene)
2. See the dosimetry heatmap appear on the body
3. Read the compliance panel
4. Move the phantom with WASD
5. Explore the sidebar sections

The tour should be dismissable, skippable, and should not appear on repeat visits. Use a small tooltip-style overlay that highlights relevant UI elements one at a time. There is an existing keyboard help modal (press ?) that shows shortcuts -- the tour should complement this, not duplicate it.

Before writing anything, explore the entire frontend thoroughly. There are many features, panels, and interactions that have been added over time. The tour should cover the most important workflow, not try to explain everything.

---

## General guidelines for all tasks

- The app uses Tailwind CSS v4, lucide-react for icons, @base-ui/react for primitives, and Zustand for state
- The dark theme is oklch-based, always dark, no light mode
- Glass morphism pattern: `bg-card/80 backdrop-blur-md border border-border`
- Font: Geist (sans), monospace for numeric data
- Run `npm run dev` from `aegis-web/` to test changes (proxies API to Flask on port 5000)
- Run the Flask backend with `python -m aegis.viewer --no-open` before testing
- Test at 1920x1080 desktop and 390x844 mobile viewports
- Don't break existing functionality. Every feature must remain accessible
- Don't add features beyond what's described. Keep changes focused
