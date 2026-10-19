// inferred from landed tags, query text not saved: the landed file holds masts and towers, telecommunication offices, any telecom=* and communication towers, written out center.
[out:json][timeout:300];
(
  nwr["man_made"~"^(mast|tower|communications_tower)$"](poly:"-48.9033340 -123.5067180 -48.8029087 -123.5067180 -48.8029087 -123.2998006 -48.9033340 -123.2998006");
  nwr["office"="telecommunication"](poly:"-48.9033340 -123.5067180 -48.8029087 -123.5067180 -48.8029087 -123.2998006 -48.9033340 -123.2998006");
  nwr["telecom"](poly:"-48.9033340 -123.5067180 -48.8029087 -123.5067180 -48.8029087 -123.2998006 -48.9033340 -123.2998006");
  nwr["tower:type"="communication"](poly:"-48.9033340 -123.5067180 -48.8029087 -123.5067180 -48.8029087 -123.2998006 -48.9033340 -123.2998006");
);
out center;
