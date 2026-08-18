% PREV: The repeated numerical campaigns start from a ready city scene. Their wall
% PREV: times on one A6000 are 29.79 s for Korenmarkt, 69.02 s for Prague, 40.70 s for
% PREV: Madrid, 30.92 s for Mexico City, and 50.11 s for Tokyo Hachiko. These times
% PREV: include the 16 transport replicas and body coupling for the complete fixed
% PREV: route. They exclude image and mesh acquisition, image-to-mesh alignment,
% PREV: image labeling, depth processing, and material-map construction. Persistent
% PREV: transport caches and exact conservative broad-phase screening reduce repeated
% PREV: work with no change to the saved scientific arrays.
The full scene-preparation path has no complete timing record. Available 14-image
records give 21.3 to 26.6 min for the hybrid semantic pass and 5.3 to 13.6 min
for material-map construction. Acquisition, alignment, depth, and combination were not
all timed separately. One live A6000 parity check took 116.981 s for one
image with independent model sessions. A shared session processed two
images in 199.228 s and reproduced every scientific image array, concept
cache array, prompt gate, and normalized metadata field exactly. These values
are implementation checks. They do not define a universal time per image.
A single cold end-to-end time is therefore not reported.

## AI notes

- Prevents ready-scene timing from being read as acquisition-to-result timing.
