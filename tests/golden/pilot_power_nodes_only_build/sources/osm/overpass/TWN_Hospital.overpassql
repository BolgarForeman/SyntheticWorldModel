// inferred from landed tags, query text not saved: every feature of the landed file carries amenity=hospital or healthcare=hospital.
[out:json][timeout:300];
(
  nwr["amenity"="hospital"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.3013759 -48.9033340 -123.3013759");
  nwr["healthcare"="hospital"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.3013759 -48.9033340 -123.3013759");
);
out geom;
