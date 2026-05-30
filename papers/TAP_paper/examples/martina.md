# Notes on the Huygens Box input file in Sim4Life

Hello Martina

This is a longer write-up of the Huygens Box file format question from your email. The short version is that there are two file routes into the Huygens Source, and the one that fits your case (data from a different simulator) is the ASCII text format that Sim4Life documents in its reference guide. The binary .h5 file you noticed is a seperate, proprietary format that is not really meant for external generation. The rest of this note covers both routes in some detail, lists a few practical things to watch out for, and points at the python files and figures I bundled with this note.

## What Sim4Life accepts as a Huygens Box input

The Huygens Source in Sim4Life has three options for the Input Type setting, as described in the Reference Guide v7.2, Section 5.3, pages 171 to 174. The first option is Simulation, where you link a Field Sensor from another Sim4Life simulation in the same project, by dragging the Field Sensor Settings folder into the Huygens Settings folder. This is the path of least resistance when both the source and the target simulation live in Sim4Life. The second option is a binary .h5 file produced by the Sim4Life Huygens Exporter. The manual states explicitly that this format is proprietary and that the file is intended to be used again inside Sim4Life, so in practice it works well only for Sim4Life-to-Sim4Life transfer. The third option is an ASCII .txt file that follows a documented format, and the manual labels it as the route to use where the input comes from third-party simulation software or measured data. That third one is yours.

The .h5 you have been looking at is most likely what the second route reads. As mentioned, that format is not specified in the manual, so anything I can say about it I learned by inspecting files in h5py. I worked it out during a research stay at the IT'IS Foundation in Zurich in May 2023, because at 28 GHz the ASCII file grew to 5-6 GB and we needed something faster. At your low frequency that performance argument does not really apply, so the ASCII route is the one I would start with. I describe both routes here anyway, because you may end up wanting the binary one if you script things further down the line, or if your external grid is strongly non-uniform.

## Low-frequency case

Your email mentions "vector potential and magnetic field," and that phrasing actually matches the language of the Sim4Life low-frequency solvers (M-EM-QS and P-EM-QS), where A and B are the natural variables, not the harmonic FDTD Huygens Source described above, which works in E and H. If you are running the harmonic FDTD solver at a low frequency, then the format in this note is the right one, and the grid will have very few cells so the ASCII file will be tiny. A one-line summary of which solver you are using would let me sharpen the answer.

## A few things to keep an eye on

The coordinates in the axes block are in metres, not millimetres, which is easy to get wrong when you are coming from a CAD tool that defaults to mm. The grid step has to be exactly uniform per axis, because the format encodes only a single step per direction, so any per-cell variation in your external grid has to be resolved by choosing a fine enough common step before you write the file. For sanity checks, I write the file, load it in Sim4Life, run a short simulation, and compare the field that Sim4Life reads back through a Field Sensor against the input I provided. If the two agree near the centre of the box and roll off correctly near the boundary, the file is good.

If anything is unclear, or if you would prefer that I have a look at one of your input files to confirm what solver and what format it actually corresponds to, just send it over and I will take a look.

Best,
Robin
