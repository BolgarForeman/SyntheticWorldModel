// inferred from landed tags, query text not saved: the landed file's features carry landuse=industrial.
[out:json][timeout:300];
(
  nwr["landuse"="industrial"](poly:"-49.0304644 -123.6274826 -48.7224721 -123.6274826 -48.7224721 -123.1605361 -49.0304644 -123.1605361");
);
out geom;
