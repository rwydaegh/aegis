# The skyline as one function, and what it says

Almost everything in this study reduces to one curve. Write it `theta(phi)`: at
each compass direction `phi`, the elevation `theta` of the top edge where surface
meets sky. Base station sites sit on that curve. The direct term is a sum along
it. Registration is a fit of one version of it to another. The sky fraction is an
average over it.

It is worth looking at the curve itself rather than only at the numbers that come
out of it. `plot_skyline_function.py` draws it three ways at one standpoint in
each city and writes `outputs/skyline_function/`.

- **From the panorama.** The bottom edge of the sky in the segmented image, turned
  into world directions through the registered pose. This is the measurement.
- **From the mesh, by vertex.** The highest mesh vertex in each azimuth bin, which
  is what `align_skyline.mesh_skyline` computes and what the registration fits.
- **From the mesh, by ray.** The highest elevation along each azimuth that still
  hits something. This is what a camera at that point would see, and it is what
  the source construction reads.

## Is the curve well behaved

Yes, in a specific sense. It is not smooth and should not be, because a roofline
genuinely jumps at every building corner. About one neighbouring pair in two
hundred jumps by more than ten degrees. Between those jumps the curve is flat or
gently sloping for tens of degrees at a time. That is a curve you can sum along.

## What agrees

At Milan, Prague and Brussels the photograph and the ray cast sit within 3 to 4
degrees of each other across the whole circle.

The stronger statement is about the quantity that matters. Taking the direct term
as the mean over azimuth of `cos^2(theta)/d`, computed once with mesh elevations
and once with photograph elevations, both using mesh distances:

| site | mesh against photograph | photograph, buildings only |
|---|---|---|
| milan_duomo | +0.04 dB | +0.12 dB |
| prague_staromestske | -0.01 dB | +0.94 dB |
| tokyo_hachiko | +0.07 dB | +2.23 dB |
| brussels_grandplace | +0.11 dB | +0.14 dB |
| korenmarkt | -2.61 dB | -2.12 dB |
| mexico_zocalo | -3.89 dB | -3.52 dB |

At four sites in six the mesh and an independent photograph give the same direct
term to within 0.1 dB. That is a cross check of the whole geometry chain against
something that never entered it.

One caution on reading the table. The closed form it uses assumes one visible tip
per azimuth and a roofline square on to the view, and neither always holds, so
the absolute values are approximate. Both columns of a row share that
approximation at the same standpoint, so the ratio is the trustworthy part. One
standpoint per site, so this is a check and not a survey.

## What disagrees, and why

**Korenmarkt has a pole two metres from the camera.** The photogrammetry built it
as a blob about 1.5 m across, which from 2 m away covers 45 degrees of azimuth.
The ray cast reports the skyline at 82 degrees across that whole wedge. The
photograph sees a thin line with sky around it and reports 27. That one object is
the entire 18 degree rms at Korenmarkt and the whole of its -2.61 dB.

Note the sign. A pole raises `theta`, and a higher `theta` lowers
`cos^2(theta)/d`, so clutter **suppresses** the direct term rather than raising
it.

**Mexico has a large smooth surface overhead** covering azimuths 200 to 350, which
the ray cast reads as a skyline at up to 61 degrees while the photograph and the
vertex envelope both stay near 15.

**Madrid and New York picked a standpoint that is under a ceiling.** At Madrid, a
ray sent at 89 degrees, nearly straight up, hits something 25 m away in every one
of 360 azimuths. There is no skyline at that point.

That last one carries a warning worth stating plainly. **That Madrid standpoint has
the lowest registration residual of any pose in the study, 0.176 degrees.** The
fit is excellent and the standpoint is unusable, and nothing in the residual says
so. An independent route reached the same place: 25 of 83 registered poses have
essentially no sky escape and 7 of them pass the admission gate. If another gate
is wanted, gate on sky escape.

## What it means for the source set

Whether clutter can hold a base station is worth up to 2.23 dB, at Tokyo, where a
third of the sky boundary is screens, signs and poles rather than building. That
is the same size as everything else in this study, so it is not ignorable.

The natural fix is the segmentation, keeping only sky boundary the photograph
calls a building. Two measurements say it is not that simple.

**The image mask is the wrong shape.** It lives in image space, where the pole is
thin. At Korenmarkt it marks 6 percent of azimuth while the mesh blob occupies
12. Masking the picture does not remove the blob.

**The fishnet cannot label the silhouette yet.** It carries a class per face and a
`face_source_triangle`, which is the right tool, but at Korenmarkt it was cut from
the 130 m crop using four views of one camera. Matched against the 250 m
silhouette it covers 0.1 percent of it, 5 hits in 4320. A rebuild at 250 m across
the admitted cameras is what would make it usable.

## How much rests on things standing next to the pedestrian

The law divides by distance, so a tip a few metres away counts for a lot. That is
right for a facade and wrong for a lamp post. `measure_near_clutter.py` measures
the size of it over 16 standpoints of the walk at each square, dropping every
azimuth whose tip is nearer than a floor.

| site | direct term | share from within 5 m | azimuths within 5 m | term above 5 m |
|---|---|---|---|---|
| newyork_timessquare | 0.00968 | 0.45 | 0.049 | 0.00530 |
| tokyo_hachiko | 0.01897 | 0.40 | 0.224 | 0.01133 |
| korenmarkt | 0.03080 | 0.35 | 0.260 | 0.02001 |
| toulouse_capitole | 0.02132 | 0.19 | 0.044 | 0.01732 |
| prague_staromestske | 0.01641 | 0.15 | 0.000 | 0.01399 |
| krakow_rynek | 0.02288 | 0.12 | 0.000 | 0.02013 |
| brussels_grandplace | 0.01986 | 0.11 | 0.023 | 0.01775 |
| mexico_zocalo | 0.02147 | 0.06 | 0.000 | 0.02028 |
| london_trafalgar | 0.01967 | 0.05 | 0.011 | 0.01860 |
| madrid_plazamayor | 0.01870 | 0.05 | 0.000 | 0.01768 |
| milan_duomo | 0.01306 | 0.00 | 0.000 | 0.01306 |

Worth 2.61 dB at New York, 2.24 at Tokyo, 1.87 at Korenmarkt, and nothing at all
at Milan. It moves the ordering at the top: Korenmarkt is first of eleven with the
near tips in and third without them, and Tokyo goes seventh to tenth.

The blend render found the same thing at one standpoint per square and much
larger, 0.67 at Korenmarkt against 0.35 here. That is the difference between a
hero frame and the median over a walk, and the walk median is the one to quote.

**The 5 m cut is a bound, not a fix.** Someone standing in a narrow street can be
within 5 m of a real facade, so the cut removes some genuine roofline too. Two
things say that is the smaller part. The floor still bites at 8 and 12 m even at
Milan, which is the cut eating real facades and is why it should not be pushed
further. And a tall facade seen from 3 m sits at about 81 degrees, where
`cos^2(alpha)` is 0.024, so it contributes little whatever the distance does. What
dominates the near term is **low** objects close by, which is exactly what a pole
or an awning is.

## Reproducing

```bash
../../../.venv/bin/python plot_skyline_function.py --bins 1440
```

Writes one figure per city, an overview of all of them, and
`outputs/skyline_function/skyline_function.json` with the per curve statistics.
Krakow, London and Toulouse are skipped: two have no panorama directory and one
has a panorama that was never registered.
