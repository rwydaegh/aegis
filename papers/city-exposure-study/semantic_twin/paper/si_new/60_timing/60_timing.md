<!-- AUTO_BEGIN: assembled -->
\section{Timing boundary}
\label{sec:si-timing}

The repeated numerical campaigns start from a ready city scene. Their wall
times on one A6000 are 29.79 s for Korenmarkt, 69.02 s for Prague, 40.70 s for
Madrid, 30.92 s for Mexico City, and 50.11 s for Tokyo Hachiko. These times
include the 16 transport replicas and body coupling for the complete fixed
route. They exclude image and mesh acquisition, panorama registration,
semantic inference, depth processing, and atlas construction. Persistent
transport caches and exact conservative broad-phase screening reduce repeated
work with no change to the saved scientific arrays.

The cold scene path has no complete common timing ledger. Available 14-panorama
records give 21.3 to 26.6 min for the hybrid semantic pass and 5.3 to 13.6 min
for atlas construction. Acquisition, registration, depth, and fusion were not
all timed separately. One live A6000 parity check took 116.981 s for one
panorama with independent model sessions. A shared session processed two
panoramas in 199.228 s and reproduced every scientific panorama array, concept
cache array, prompt gate, and normalized metadata field exactly. These values
are implementation anchors. They do not define a universal time per panorama.
A single cold end-to-end time is therefore not reported.
<!-- AUTO_END: assembled -->


















## Aggregation notes (AI-owned)
