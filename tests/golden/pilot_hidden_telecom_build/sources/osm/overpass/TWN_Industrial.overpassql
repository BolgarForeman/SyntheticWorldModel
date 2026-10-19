// inferred from landed tags, query text not saved: the landed file's features carry landuse=industrial.
[out:json][timeout:300];
(
  nwr["landuse"="industrial"](poly:"-48.9033340 -123.5067180 -48.8029087 -123.5067180 -48.8029087 -123.2998006 -48.9033340 -123.2998006");
);
out geom;
