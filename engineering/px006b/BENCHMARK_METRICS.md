# PX-006B Benchmark Metrics

Metrics are reported in separate performance groups. No single misleading composite score.

## Groups

| Group | Metrics |
|-------|---------|
| STRUCTURE_SEGMENTATION | IoU proxy, precision/recall/F1 proxy |
| ROOF_BOUNDARY | boundary IoU |
| ROOF_PLANES | plane count difference, false split, missed plane, merged planes |
| ROOF_EDGES | edge-length differences by class |
| ROOF_SLOPE | slope and azimuth angular differences |
| AREA_CANDIDATES | absolute and percentage area differences |
| LINEAR_MEASUREMENTS | ridge/hip/valley/eave/rake length differences |
| OPENINGS_AND_PENETRATIONS | penetration count difference |
| OCCLUSION_HANDLING | withheld measurement flags |

## Limitations

- External corpus benchmarks do not establish production tolerances
- Bounding-box IoU proxies are development aids, not survey-grade boundary metrics
- No universal contractor-grade tolerance is invented in PX-006B
