// Inferred from the landed file: masts and towers, telecommunication offices, any telecom=* and communication towers, written out center; no query text was saved.
[out:json][timeout:300];
(
  nwr["man_made"~"^(mast|tower|communications_tower)$"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.2998006 -48.9033340 -123.2998006");
  nwr["office"="telecommunication"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.2998006 -48.9033340 -123.2998006");
  nwr["telecom"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.2998006 -48.9033340 -123.2998006");
  nwr["tower:type"="communication"](poly:"-48.9033340 -123.5687505 -48.7460974 -123.5687505 -48.7460974 -123.2998006 -48.9033340 -123.2998006");
);
out center;
