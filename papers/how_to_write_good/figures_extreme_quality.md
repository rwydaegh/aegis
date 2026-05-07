1. On a high high level (do this first): Does the figure contain the strictly minimum amount of necessary information in it corresponding to the text and what is necessary to convey?
2. Is the information that does need to be conveyed of the absolute highest quality, clarity and perfection? 
3. Is there ANY text, non-trivial symbol or line that overlaps with
4. Is the design language (from colors to dash choices to the way the legend is shown) the same with other figures?
5. Is the figure highly minimalistic, dry, simple, academic and to the point?
6. Is it color-blind friendly? Line shape variations
7. Is the fontsize the same as the fontsize in the text? If not, it MAY be acceptable in cases where we're really struggling to put things while also not breaking rule 3
8. Is there a better way to change the figure's canvas? Should we go to a two column figure? Could we benefit from eeating up more vertical space in the IEEE column? On the flip side: did we take up unnecessarily too much place? When is it just small enough that it is totally legible and clear while remaining 100% efficient with the space given?
9. Are we preferring PDF as much as possible, unless raster in unavoidable?
10. Does the font family match that of the classic LaTeX one in the IEEE paper?
11. Do all the axes have units, even if unitless? Pick ( ) [ ] or ', ..' and stick with it across axes and other figures. Unitless needs two \, in latex
12. Is the log scale useful? Should the lin scale be log scale? Can one of them be lin the other log? What is the best option?
13. Is the axis extent exactly fitted to the data extend plus around 5% of breathing room? Are there any points waaay off that make some part of the data illegible? How should we deal with them (omit, broken axes, etc).
14. Tick density: enough to read values, not so many they collide. Minor ticks only if they're actually useful.
15. Is the legend encircled by a basic black rectangle at 1 pt no rounded corners ? WHere should we place this legend so it overlaps with at least as possible data? If this is too tricky, should we move it out of the figure entirely (do so cleanly, needs many iterations)? If that on the other hands creates issues, what will our solution be?
16. Is the (a) (b) (c) captions the minimum amount of subcaption that just differentiate a b and c, such that the main caption carries all the common explanations? 
17. Does the main caption start with a relatively short, hyper clear sentence that explains wtf im looking at on a high level. Does it then explain the key elements without repeating too much of the text (can be lenient though) and becoming a whole book (tip: count lines or think of max word counts journals like to use)?
18. Is the fig referenced before it appears in text?
19. If possible, is it at the top or bottom of the column, not floating?
20. Are the markers unfilled so we can look inside them to see what the actual value is? Not too thick nor too thin. 
21. No blunders like stray _ or ^ that isn't rendered? mathrm for things that should be mathrm
22. Would the figure benefit from an arrow with a pointer to a really key point in it to immediately draw attention to something? Especially if it's not that obvious? Does it deserve an annotation? How can such a thing be made without overlapping with anything? 
23. IMPORTANT, also a Wout pet-peeve. Every Figure has to be introduced properly. Preferably quite early in the relevant section (especially the famous flowchart and/or the configuration figures). Flowchart figure has to be named flowchart. Configuration figure has to be named configuration. Sections should start with a stupid simple sentence like "The <> is shown in Figure 1. <More simple sentences about it, careful not too overstep the caption too much>. "