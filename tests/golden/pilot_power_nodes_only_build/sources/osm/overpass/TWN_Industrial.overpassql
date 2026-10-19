// inferred from landed tags, query text not saved: the landed file's features carry landuse=industrial.
[out:json][timeout:300];
(
  nwr["landuse"="industrial"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.3013759 -48.9033340 -123.3013759");
);
out geom;
