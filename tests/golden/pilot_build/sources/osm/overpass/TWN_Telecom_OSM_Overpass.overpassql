// inferred from landed tags, query text not saved: the landed file holds masts and towers, telecommunication offices, any telecom=* and communication towers, written out center.
[out:json][timeout:300];
(
  nwr["man_made"~"^(mast|tower|communications_tower)$"](poly:"-49.0304644 -123.6274826 -48.7224721 -123.6274826 -48.7224721 -123.1605361 -49.0304644 -123.1605361");
  nwr["office"="telecommunication"](poly:"-49.0304644 -123.6274826 -48.7224721 -123.6274826 -48.7224721 -123.1605361 -49.0304644 -123.1605361");
  nwr["telecom"](poly:"-49.0304644 -123.6274826 -48.7224721 -123.6274826 -48.7224721 -123.1605361 -49.0304644 -123.1605361");
  nwr["tower:type"="communication"](poly:"-49.0304644 -123.6274826 -48.7224721 -123.6274826 -48.7224721 -123.1605361 -49.0304644 -123.1605361");
);
out center;
