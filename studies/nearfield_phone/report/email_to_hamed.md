Subject: Distance dependence and uncertainty for the normalized SAR values

Dear Hamed,

Thanks for the clear questions at the dose model meeting. Both of the things you
asked for, a distance correction and an uncertainty estimate for each normalized
SAR value, are now ready. We switched the dosimetry over to a new computational
method we have been developing, which lets us run very large numbers of exposure
configurations quickly, so instead of a single number per scenario we can give
you the whole picture: how the value changes with distance, and how much it
varies. A few highlights below, and everything is in the attached Excel file and
two plots.

1. Distance correction

For a phone near the body the absorbed dose follows a simple inverse-square law
with a small offset:

    SAR(d) = SAR(d_ref) x ( (d_ref + delta) / (d + delta) )^2

Here d is the phone-to-body distance, d_ref is the distance the value was
computed at (200 mm in front of the eyes), and delta is a small near-field
offset of about 6 mm. For any distance beyond a few centimetres this is
essentially the familiar inverse-square rule: halve the distance and the dose
goes up roughly four times. The fit to our simulations is excellent (R^2 = 0.9999).

As a worked example, your brain value of 2.62 W/kg per W for Duke in the
front_of_eyes scenario becomes, at other distances:

    100 mm  ->  ~9.9 W/kg/W   (about 3.8x higher)
    150 mm  ->  ~4.6 W/kg/W
    200 mm  ->   2.62 W/kg/W  (reference)
    300 mm  ->  ~1.2 W/kg/W
    400 mm  ->  ~0.68 W/kg/W

The "fig_distance_factor" plot shows this curve with the reference point marked,
and the full table is in the Excel sheet "brain_2.62_adjusted".

2. Uncertainty

For each normalized value we now also give the mean, standard deviation, minimum,
maximum and 5th/95th percentiles. For a fixed body model, the main source of
variability is how the phone is held (its orientation). For the Duke brain value
that comes out at about +/- 27% (one standard deviation), so

    2.62 W/kg/W  ->  roughly 2.6 +/- 0.7 W/kg/W,

with the full range over phone orientations running from about 2.0 to 3.8 W/kg/W.
On top of that, differences between body models (adult vs child) add a further
spread of roughly 30 to 40%: smaller bodies absorb more per kilogram, so a child
model can sit noticeably above the adult value. The per-scenario and
per-frequency uncertainty tables are in the Excel sheets named "unc_...".

What is in the attachment

- nearfield_dose_results.xlsx: distance-correction coefficients and uncertainty
  statistics for every scenario and frequency band, plus the worked brain example.
- fig_distance_factor.png: the distance curve for the brain value with its
  uncertainty band.
- fig_uncertainty.png: how much each scenario varies with phone orientation.

Happy to walk through any of it, or to produce the same distance-and-uncertainty
treatment for any other tissue, scenario or frequency you need. We can turn these
around quickly now.

Best regards,
Robin
