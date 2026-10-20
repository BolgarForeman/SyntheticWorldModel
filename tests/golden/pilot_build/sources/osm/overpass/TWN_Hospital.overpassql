// inferred from landed tags, query text not saved: every feature of the landed file carries amenity=hospital or healthcare=hospital.
[out:json][timeout:300];
(
  nwr["amenity"="hospital"](poly:"-49.0304644 -123.6274826 -48.7224721 -123.6274826 -48.7224721 -123.1605361 -49.0304644 -123.1605361");
  nwr["healthcare"="hospital"](poly:"-49.0304644 -123.6274826 -48.7224721 -123.6274826 -48.7224721 -123.1605361 -49.0304644 -123.1605361");
);
out geom;
