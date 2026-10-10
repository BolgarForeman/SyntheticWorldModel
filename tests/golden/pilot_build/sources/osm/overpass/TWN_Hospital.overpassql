// Inferred from the landed file: every feature carries amenity=hospital or healthcare=hospital; no query text was saved.
[out:json][timeout:300];
(
  nwr["amenity"="hospital"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.2998006 -48.9033340 -123.2998006");
  nwr["healthcare"="hospital"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.2998006 -48.9033340 -123.2998006");
);
out geom;
