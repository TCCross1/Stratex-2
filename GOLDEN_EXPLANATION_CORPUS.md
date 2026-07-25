# GOLDEN EXPLANATION CORPUS
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Overview & Core Structural Requirements

This corpus serves as the authoritative verification dataset for the **Stratex-2 Intelligence Explainer Engine™**. It spans all **12 analytical domains** and defines **10 verification case archetypes** per domain, yielding exactly 120 highly controlled test scenarios. 

Every case is designed to test the limits of the engine’s parser, trace verification, confidence calculation, and multi-level tone guardrails.

---

## 2. The 10 Verification Case Archetypes

To ensure standardized testing across all systems, each case maps directly to one of the following 10 structural archetypes:

1. **Fully Verified (FV):** 100% complete scans by certified inspectors and fresh telemetry sensors with zero conflicts. Expected confidence: `95% - 100%`.
2. **Strong but Incomplete (SI):** High-reliability sources but incomplete physical coverage (e.g. spot checks). Expected confidence: `75% - 85%`.
3. **Conflicting Evidence (CE):** Multi-source contradiction (e.g., active sensors disagreeing with human visual logs). Expected confidence: `40% - 60%`.
4. **Stale Evidence (SE):** High-quality older data that has decayed based on domain-specific half-life $\lambda$. Expected confidence: `30% - 60%`.
5. **Low-Quality Evidence (LQ):** Unverified, self-reported, or low-resolution crowd-sourced data. Expected confidence: `35% - 45%`.
6. **Missing Evidence (ME):** Zero physical records or empty ingestion fields. Must fail safely, falling back to `UNKNOWN` with `0%` confidence.
7. **Revoked Evidence (RE):** Data that was formally deleted or marked as revoked by a reviewer. Must fail safely, excluding revoked evidence from the trace.
8. **Duplicate Evidence (DE):** Redundant, overlapping records from the same source. Must deduplicate gracefully without artificially inflating confidence.
9. **Cross-System Relationship (CS):** Complex causal links across multiple domains (e.g. roof leak causing water intrusion and electrical fault).
10. **Human Reviewer Override (HO):** A manual correction to a conclusion or rating. Must append the reviewer ID, timestamp, and audit justification.

---

## 3. The 12 Supported Domains & Validation Scenarios

Below is the dense, high-density matrix detailing the golden validation parameters for all 12 domains across the 10 archetypes.

---

### DOMAIN 1: ROOF (ROOF)
*   **Decay Constant ($\lambda$):** `0.00095` (Medium)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RF-01** | **FV** | Localized shingle delamination; 5 cracked asphalt tabs on north slope. | 95% - 100% | `msn_1001` (UAV Scan), `ev_9001` (img_4021.jpg), `pe_1201` (Passport) | CDX 1/2-inch deck; typical weathering. | Decking underlayment moisture state. | "Confirmed tab delamination", "verified" | "No damage found", "guaranteed leak-proof" |
| **RF-02** | **SI** | Suspected shingle wear on south slope based on localized camera spot checks. | 75% - 85% | `msn_1002`, `ev_9002` (localized photos), `pe_1202` | Rafter structural pitch is 6:12. | Unchecked north/east slope slopes. | "Spot-checks indicate", "partial capture" | "Complete roof verified", "100% clear" |
| **RF-03** | **CE** | North slope condition disputed: Homeowner reports dry, but drone shows asphalt loss. | 40% - 60% | `msn_1003`, `ev_9003` (homeowner text), `ev_9004` (UAV IR) | Both observations represent current month. | Attic dry-rot presence under deck. | "Contradictory inputs", "minor conflict" | "Homeowner confirmed", "fully resolved" |
| **RF-04** | **SE** | Roof shingles weathered; assessment based on 3-year-old certified inspection. | 30% - 50% | `msn_1004` (2023-01), `ev_9005` (historic pdf), `pe_1204` | No major wind storms occurred since 2023. | Intervening weathering rate. | "Decayed historic records", "past state" | "Current condition verified", "active" |
| **RF-05** | **LQ** | Possible damage; photo uploaded by resident showing fallen shingle pieces. | 35% - 45% | `ev_9006` (unverified resident photo) | Shingles are standard 3-tab organic. | Origin slope, current deck state. | "Unverified homeowner upload", "possible" | "Inspector verified", "certified" |
| **RF-06** | **ME** | No physical roofing data available. Fallback engaged. | 0% | Empty trace array. | Base building structure is intact. | Complete roof state. | "UNKNOWN", "inspection required" | "Good condition", "adequate roof health" |
| **RF-07** | **RE** | Assessment excludes revoked inspector log due to camera lens scratch distortion. | 0% (Fallback) | Excluded `ev_9007` (revoked flag in DB) | Remaining secondary data is null. | Current shingle status. | "Evidence revoked", "no active telemetry" | "Based on photo RF_9007", "inspected" |
| **RF-08** | **DE** | Localized shingle delamination; duplicate images merged. | 95% | Merged `ev_9008a` and `ev_9008b` | Images show the same 5 shingle tabs. | Exact age of shingles. | "Deduplicated", "validated course 14" | "10 independent failures", "increased wear" |
| **RF-09** | **CS** | Asphalt damage on north slope creating active moisture intrusion path to attic. | 85% - 90% | `msn_1009`, `ev_9009`, `kg_path_772` (ROOF $\rightarrow$ WATER) | Water leaks match the physical defect. | Under-deck dry rot propagation. | "Causal linkage confirmed", "leak path" | "Isolated roofing wear", "unrelated" |
| **RF-10** | **HO** | Reviewer upgraded roof rating from POOR to FAIR; mastic patch completed but not in UAV. | 90% | `pe_1210` with override block, `user_104` (Atlas) | Repair complies with ASTM D3462. | Lifetime of localized patch. | "Reviewer override", " Atlas manual edit" | "Automated calculation", "unchanged" |

---

### DOMAIN 2: FOUNDATION (FOUNDATION)
*   **Decay Constant ($\lambda$):** `0.00038` (Slow)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FD-01** | **FV** | Hairline cosmetic concrete shrinkage crack; width < 1.0mm in garage slab. | 95% - 100% | `msn_1011` (Laser levelling), `ev_9011`, `pe_1211` | Soil moisture is currently stable. | Deep sub-slab soil density. | "Cosmetic shrinkage", "non-structural" | "Structural failure", "perfectly level" |
| **FD-02** | **SI** | Crawlspace piers structurally stable based on main girder spot checks. | 75% - 85% | `msn_1012`, `ev_9012` (pier spot checks) | Remaining uninspected piers are similar. | Outer stem wall footing. | "Localized pier checks", "representative" | "100% inspected", "no defects exist" |
| **FD-03** | **CE** | Slab level conflict; homeowner reports sloping floors but laser level reads < 0.25". | 50% - 60% | `msn_1013`, `ev_9013` (Homeowner), `ev_9014` (Laser) | Flooring material is hardwood. | Sub-floor wood frame joist deflection. | "Conflicting inputs", "slope not confirmed" | "Slab is failing", "leveling is perfect" |
| **FD-04** | **SE** | Foundation structural review stable based on 6-year-old engineering stamp. | 45% - 55% | `msn_1014` (2020-03), `ev_9015` (PE stamp) | No seismic or sinkhole events occurred. | Clay soil swelling index. | "Stable historic stamp", "slow decay" | "Active structural check", "current" |
| **FD-05** | **LQ** | Possible settlement crack; unverified homeowner photo of exterior brick joint. | 35% - 45% | `ev_9016` (homeowner photo) | Brick veneer is non-structural. | Active movement of footing. | "Unverified veneer separation", "possible" | "Verified foundation settlement" |
| **FD-06** | **ME** | No foundation data available. Fallback engaged. | 0% | Empty trace array. | Home is built on a concrete slab. | Retaining wall integrity. | "UNKNOWN", "foundation review required" | "Slab is robust", "solid foundation" |
| **FD-07** | **RE** | Excludes uncalibrated laser scanner files that reported false 3" tilt. | 0% (Fallback) | Excluded `ev_9017` (revoked tag) | No other foundation data. | Slab slope. | "Excluded uncalibrated scan", "UNKNOWN" | "Laster confirmed 3-inch slope" |
| **FD-08** | **DE** | Cosmetic shrinkage crack confirmed; duplicate logs merged. | 95% | Merged `ev_9018a` and `ev_9018b` | Crack is located on west stem wall. | Expansion joint depth. | "Merged redundant crack logs" | "Multiple crack lines", "severe decay" |
| **FD-09** | **CS** | Retaining wall soil swelling causing foundation stem wall lateral pressure. | 85% - 90% | `msn_1019`, `ev_9019`, `kg_path_773` (WALL $\rightarrow$ FD) | Soil is clay-heavy. | Drainage pipe blockage status. | "Lateral pressure linked", "soil swelling" | "Foundation acting independently" |
| **FD-10** | **HO** | Reviewer overrides structural risk rating to HIGH due to adjacent tree root. | 90% | `pe_1220` with override block, `user_104` (Atlas) | Root has penetrated structural footing. | Internal foundation steel damage. | "Atlas manual override", "structural risk" | "Calculated low risk", "safe" |

---

### DOMAIN 3: WINDOWS (WINDOWS)
*   **Decay Constant ($\lambda$):** `0.00095` (Medium)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WN-01** | **FV** | Broken double-pane gas seal in living room west window; moisture fogging. | 95% - 100% | `msn_1021`, `ev_9021` (Photo of fogged window), `pe_1221` | Window is double-hung vinyl. | Glass frame mold propagation. | "Broken thermal seal", "visible fogging" | "Perfect thermal performance" |
| **WN-02** | **SI** | Upper floor window screens missing based on ground-level visual scan. | 75% - 85% | `msn_1022`, `ev_9022` (ground camera) | Lower level windows have screens. | Interior latch functionality. | "Ground-level scan indicates", "missing" | "All window systems operational" |
| **WN-03** | **CE** | West window performance conflict; homeowner claims drafty, thermal camera reads normal. | 50% - 60% | `msn_1023`, `ev_9023` (Owner), `ev_9024` (FLIR) | Outdoor temperature is 65°F (low delta). | Weatherstripping mechanical compression. | "Direct conflict", "draft unverified" | "No leak exists", "air leak confirmed" |
| **WN-04** | **SE** | Double-pane wood windows stable; based on 4-year-old home inspection. | 40% - 50% | `msn_1024` (2022-05), `ev_9025`, `pe_1224` | Pine window frames have not rotted. | Current moisture seal rating. | "Decayed historic assessment", "older data" | "Active window seals verified" |
| **WN-05** | **LQ** | Broken latch reported by tenant via phone call with no photos. | 35% - 45% | `ev_9026` (tenant maintenance ticket) | Latch is plastic single-point. | Lock alignment. | "Tenant-reported unverified defect" | "Inspector certified broken latch" |
| **WN-06** | **ME** | No window performance data available. Fallback engaged. | 0% | Empty trace array. | Windows are double-hung. | Complete window seal status. | "UNKNOWN", "window scan required" | "Windows secure", "no air leakage" |
| **WN-07** | **RE** | Excludes retracted photo log showing living room window (wrong property). | 0% (Fallback) | Excluded `ev_9027` (revoked flag) | No other window files. | Glass pane integrity. | "Evidence revoked", "UNKNOWN" | "Living room window broken" |
| **WN-08** | **DE** | Broken double-pane seal; duplicate photo entries deduplicated. | 95% | Merged `ev_9028a` and `ev_9028b` | Photos represent same frame. | Seal repair cost. | "Deduplicated window seals" | "Multiple broken panes", "severe" |
| **WN-09** | **CS** | Window frame seal failure causing wall cavity moisture intrusion on east wall. | 85% - 90% | `msn_1029`, `ev_9029`, `kg_path_774` (WN $\rightarrow$ WATER) | Intrusion is active during rainfall. | Insulation mold status. | "Causal moisture pathway from frame" | "Dry wall cavity", "unrelated frame wear" |
| **WN-10** | **HO** | Reviewer overrides window status to CRITICAL; broken pane is a security hazard. | 90% | `pe_1230` override, `user_104` (Atlas) | Ground floor window, vacant property. | Intruders present in area. | "Atlas manual override", "immediate hazard" | "Low-priority cosmetic cosmetic" |

---

### DOMAIN 4: HVAC (HVAC)
*   **Decay Constant ($\lambda$):** `0.0038` (Fast)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HV-01** | **FV** | Furnace heating cycle functional; temperature rise of 32°F across heat exchanger. | 95% - 100% | `msn_1031`, `ev_9031` (Anemometer/Temp), `pe_1231` | Filter is clean and air flow is normal. | Heat exchanger micro-cracking. | "Heat rise within limits", "functional" | "Furnace as-new", "zero carbon monoxide" |
| **HV-02** | **SI** | AC condenser functional based on localized suction line temperature checks. | 75% - 85% | `msn_1032`, `ev_9032` (spot checks) | Air duct distribution is equal. | Compressor motor winding wear. | "Localized condenser check", "functional" | "Complete HVAC system certified" |
| **HV-03** | **CE** | Condenser motor dispute; sensor triggers over-current but tech says normal. | 45% - 55% | `msn_1033`, `ev_9033` (Sensor), `ev_9034` (Contractor) | Sensor is calibrated within last 90 days. | Start capacitor degradation. | "Current draw conflict", "monitoring required" | "Motor is fine", "compressor failed" |
| **HV-04** | **SE** | HVAC gas valve certified; based on 1.5-year-old municipal permit ticket. | 30% - 40% | `msn_1034` (2025-01), `ev_9035`, `pe_1234` | Valve mechanical springs remain stable. | Internal corrosion of valve. | "Decayed historic permit", "fast decay" | "Active gas flow certified", "current" |
| **HV-05** | **LQ** | Poor air flow reported by homeowner on phone log with no telemetry. | 35% - 45% | `ev_9036` (homeowner call log) | Duct dampers are in open position. | Fan blower motor speed. | "Unverified homeowner report", "poor flow" | "Certified restricted duct flow" |
| **HV-06** | **ME** | No HVAC performance data available. Fallback engaged. | 0% | Empty trace array. | System is split central air. | Heat exchanger integrity. | "UNKNOWN", "HVAC service recommended" | "HVAC is in excellent operating state" |
| **HV-07** | **RE** | Excludes technician log with invalid probe placement on wrong duct. | 0% (Fallback) | Excluded `ev_9037` (revoked tag) | Secondary HVAC data is null. | True duct temperature. | "Technician log excluded", "UNKNOWN" | "Duct output measured at 45°F" |
| **HV-08** | **DE** | Blower fan vibration within tolerance; duplicate sensor records merged. | 95% | Merged `ev_9038a` and `ev_9038b` | Both records represent same run. | Bearing wear coefficient. | "Blower vibration deduplicated" | "Double vibration detected", "failure" |
| **HV-09** | **CS** | AC condensate drain backup causing ceiling drywall water damage in hallway. | 85% - 90% | `msn_1039`, `ev_9039`, `kg_path_775` (HVAC $\rightarrow$ WATER) | Float safety switch failed to trigger. | Secondary drain pan state. | "Condensate backup linked", "leak path" | "Isolated drywall damage", "unrelated" |
| **HV-10** | **HO** | Reviewer overrides HVAC status to UNSTABLE; furnace flame roll-out noticed. | 95% | `pe_1240` override, `user_104` (Atlas) | Roll-out presents immediate fire hazard. | Burner manifold alignment. | "Atlas manual override", "roll-out risk" | "Calculated functional status" |

---

### DOMAIN 5: ELECTRICAL (ELECTRICAL)
*   **Decay Constant ($\lambda$):** `0.00038` (Slow)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EL-01** | **FV** | Double-pole 50A breaker has minor oxidation on lug connector. | 95% - 100% | `msn_1041`, `ev_9041` (macro photo), `pe_1241` | Breaker feeds the central AC. | Torque on terminal screws. | "lug oxidation verified", "minor" | "Complete panel fire hazard", "as-new" |
| **EL-02** | **SI** | Panel circuits operational based on spot-check volt testing of 5 main breakers. | 75% - 85% | `msn_1042`, `ev_9042` (multimeter logs) | Other breakers share the same bus bar. | Branch circuit wire insulation. | "circuit spot checks", "no active faults" | "100% branch wires certified" |
| **EL-03** | **CE** | Breaker temperature conflict; sensor reads 140°F, inspector writes "cool to touch". | 45% - 55% | `msn_1043`, `ev_9043` (thermal sensor), `ev_9044` (inspector) | Thermal sensor is directly attached. | Inspector contact point location. | "thermal anomaly conflict", "check required" | "lug is safe", "immediate breaker melt" |
| **EL-04** | **SE** | Aluminum wiring branch circuit stable; based on 5-year-old inspect stamp. | 40% - 50% | `msn_1044` (2021-02), `ev_9045`, `pe_1244` | Copalum crimp connectors were used. | Connection creep deformation. | "historic inspect stamp", "slow decay" | "Active wire splice verified" |
| **EL-05** | **LQ** | GFI outlet in kitchen ungrounded; reported by resident via app. | 35% - 45% | `ev_9046` (resident photo of tester) | Tester is standard 3-light yellow. | Upstream line daisy-chain. | "Resident-reported ungrounded GFI" | "Certified NEC electrical fault" |
| **EL-06** | **ME** | No electrical panel data available. Fallback engaged. | 0% | Empty trace array. | Panel is 200A service. | Sub-panel connections. | "UNKNOWN", "electrical safety review needed" | "Electrical panel is code compliant" |
| **EL-07** | **RE** | Excludes infrared scan with incorrect emissivity setting for copper lugs. | 0% (Fallback) | Excluded `ev_9047` (revoked tag) | Secondary electrical files are null. | Real breaker lug temperatures. | "IR scan excluded", "UNKNOWN" | "Breaker measured at 180 degrees" |
| **EL-08** | **DE** | Lug terminal torque confirmed; duplicate wrench logs merged. | 95% | Merged `ev_9048a` and `ev_9048b` | Torque wrench is calibrated to 45 in-lb. | Screw thread oxidation. | "Deduplicated torque measurements" | "Double torque applied", "over-torque" |
| **EL-09** | **CS** | Water intrusion on basement wall dripping onto subpanel enclosure. | 85% - 90% | `msn_1049`, `ev_9049`, `kg_path_776` (WATER $\rightarrow$ EL) | Water is actively conducting. | Ground fault loop impedance. | "Moisture path linked to enclosure" | "dry electrical cabinet", "unrelated" |
| **EL-10** | **HO** | Reviewer overrides panel status to FAIL; multi-wire branch circuit on single-pole. | 95% | `pe_1250` override, `user_104` (Atlas) | Breakers are not common-trip tied. | Shared neutral load balance. | "Atlas override", "shared neutral hazard" | " NEC compliant panelboard" |

---

### DOMAIN 6: PLUMBING (PLUMBING)
*   **Decay Constant ($\lambda$):** `0.00095` (Medium)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PL-01** | **FV** | Slow drain in master shower; 2.5 gpm restriction caused by hair buildup. | 95% - 100% | `msn_1051`, `ev_9051` (drain camera), `pe_1251` | Pipe is standard 2-inch PVC. | Deep main stack blockage. | "Confirmed drain restriction", "hair clog" | "Main sewer pipe collapsed" |
| **PL-02** | **SI** | Water pressure normal based on static pressure checks at hose bibb only. | 75% - 85% | `msn_1052`, `ev_9052` (pressure log) | Dynamic pressure drop is low. | Second floor master bath flow. | "pressure static check", "satisfactory" | "100% piping flow certified" |
| **PL-03** | **CE** | Under-sink leak conflict; moisture sensor reads wet but contractor reports dry. | 45% - 55% | `msn_1053`, `ev_9053` (sensor), `ev_9054` (tech text) | Sensor is placed under trap joint. | Condensation accumulation rate. | "wet alert conflict", "under-sink review" | "Pipe is leaking", "joint is secure" |
| **PL-04** | **SE** | PEX repipe certified; based on 3-year-old contractor invoice and closeout. | 40% - 50% | `msn_1054` (2023-05), `ev_9055`, `pe_1254` | Brass crimp rings are ASTM F1807. | Scale buildup inside water heater. | "historic repipe documentation" | "Active joint pressure verified" |
| **PL-05** | **LQ** | Dripping faucet in guest half-bath reported by resident with no video. | 35% - 45% | `ev_9056` (resident app ticket) | Faucet is single-handle cartridge. | Valve seat wear profile. | "Resident-reported dripping valve" | "Certified plumbing failure" |
| **PL-06** | **ME** | No plumbing system data available. Fallback engaged. | 0% | Empty trace array. | Water supply is municipal. | Main waste pipe slope. | "UNKNOWN", "plumbing assessment needed" | "Plumbing systems are operating normally" |
| **PL-07** | **RE** | Excludes hydro-test log due to uncalibrated pressure gauge. | 0% (Fallback) | Excluded `ev_9057` (revoked tag) | No other plumbing records. | Line pressure state. | "Pressure log excluded", "UNKNOWN" | "Pipes passed 15 psi hydro-test" |
| **PL-08** | **DE** | Shower drain velocity measured; duplicate flow logs merged. | 95% | Merged `ev_9058a` and `ev_9058b` | Both tests were run at same faucet rate. | Secondary venting air flow. | "Deduplicated drain flow rate" | "Double restriction detected" |
| **PL-09** | **CS** | Shower pan grout cracked, leaking water into kitchen ceiling below. | 85% - 90% | `msn_1059`, `ev_9059`, `kg_path_777` (PL $\rightarrow$ WATER) | Water path is gravity-driven. | Ceiling framing decay. | "Shower pan leak linked", "ceiling stain" | "Kitchen ceiling drywall leak unrelated" |
| **PL-10** | **HO** | Reviewer overrides plumbing status to FAIL; corroded cast iron sewer main seen on stack. | 95% | `pe_1260` override, `user_104` (Atlas) | Corrosion has compromised wall thickness. | Below-slab pipe collapse status. | "Atlas override", "cast iron decay" | "Low-risk localized rust" |

---

### DOMAIN 7: WATER INTRUSION (WATER_INTRUSION)
*   **Decay Constant ($\lambda$):** `0.0038` (Fast)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WI-01** | **FV** | Active ceiling leak; 22% moisture reading in master bedroom drywall. | 95% - 100% | `msn_1061`, `ev_9061` (Moisture pin), `pe_1261` | Source is roof leak. | Plaster lath mold propagation. | "Active moisture detected", "22% wet" | "Dry ceiling structure" |
| **WI-02** | **SI** | Crawlspace mud sill dampness based on spot check around front corner. | 75% - 85% | `msn_1062`, `ev_9062` (spot pin log) | Rear sill plate shares grading slope. | Concrete foundation pore suction. | "Spot-checks indicate dampness" | "Crawlspace moisture-free" |
| **WI-03** | **CE** | Attic rafters water state conflict; thermal shows wet, pin meter reads 12% (dry). | 45% - 55% | `msn_1063`, `ev_9063` (FLIR), `ev_9064` (Pin meter) | Thermal camera is measuring surface cold. | Air draft temperature cooling rafters. | "Moisture evaluation conflict", "verify" | "Rafters are soaked", "rafters are dry" |
| **WI-04** | **SE** | Basement leak resolved; based on 1-year-old waterproofing completion invoice. | 30% - 40% | `msn_1064` (2025-07), `ev_9065`, `pe_1264` | Waterproofing membrane holds under hydrostatic pressure. | Sump pump check valve lifetime. | "Historic waterproofing documentation" | "Active dry soil certified" |
| **WI-05** | **LQ** | Wet carpet under window reported by homeowner during rainstorm. | 35% - 45% | `ev_9066` (homeowner text file) | Window frame was fully latched. | Subfloor plywood rot. | "Unverified homeowner leak report" | "Certified structural water leak" |
| **WI-06** | **ME** | No water intrusion data available. Fallback engaged. | 0% | Empty trace array. | Home is currently dry. | Framing wall cavity moisture state. | "UNKNOWN", "moisture inspection recommended" | "No active water leaks exist" |
| **WI-07** | **RE** | Excludes thermal image with incorrect temperature tuning. | 0% (Fallback) | Excluded `ev_9067` (revoked tag) | No other moisture telemetry. | Actual surface humidity. | "IR image excluded", "UNKNOWN" | "FLIR confirmed active moisture" |
| **WI-08** | **DE** | Wall cavity relative humidity stable; duplicate sensor readings merged. | 95% | Merged `ev_9068a` and `ev_9068b` | Both sensors sit in same stud cavity. | Wood framing fungus activation point. | "Deduplicated cavity humidity" | "Double water entry point" |
| **WI-09** | **CS** | Wall cavity water intrusion causing mold blooming on adjacent drywall. | 85% - 90% | `msn_1069`, `ev_9069`, `kg_path_778` (WATER $\rightarrow$ MOLD) | Relative humidity is > 70% in wall. | Spore concentration count. | "Water leak linked to mold growth" | "Dry wall cavity", "unrelated surface mold" |
| **WI-10** | **HO** | Reviewer overrides water status to CRITICAL; water pooling on furnace control board. | 95% | `pe_1270` override, `user_104` (Atlas) | Water represents electrocution/fire risk. | Internal transformer damage. | "Atlas override", "hazardous water pooling" | "Low-priority HVAC drip" |

---

### DOMAIN 8: THERMAL FINDINGS (THERMAL_FINDINGS)
*   **Decay Constant ($\lambda$):** `0.0038` (Fast)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TF-01** | **FV** | Ceiling insulation void; 5°F thermal delta in living room corner. | 95% - 100% | `msn_1071` (FLIR flyover), `ev_9071` (FLIR image), `pe_1271` | Delta is due to missing fiberglass. | Attic rafters structural load. | "Thermal anomaly void", "insulation gap" | "Complete ceiling thermal seal" |
| **TF-02** | **SI** | Wall insulation voids present based on front facade thermal camera spot checks. | 75% - 85% | `msn_1072`, `ev_9072` (wall FLIR) | Rear walls have similar construction. | Internal wall draft currents. | "Wall spot thermal scan indicates" | "Facade thermal signature 100% clear" |
| **TF-03** | **CE** | Attic temperature anomaly dispute; drone FLIR reads hot spot, tech says dry. | 45% - 55% | `msn_1073`, `ev_9073` (Drone FLIR), `ev_9074` (Physical probe) | Drone was flown during direct solar loading. | Rafter radiant heat retention. | "Thermal signature mismatch", "verify" | "Attic is burning", "attic is cool" |
| **TF-04** | **SE** | Wall thermal envelope stable; based on 2-year-old winter energy audit report. | 30% - 40% | `msn_1074` (2024-01), `ev_9075`, `pe_1274` | Envelope has not been modified since 2024. | Settling rate of loose-fill cellulose. | "Historic thermal envelope audit" | "Active thermal performance verified" |
| **TF-05** | **LQ** | Drafty corner reported by resident with phone thermal camera snapshot. | 35% - 45% | `ev_9076` (resident phone FLIR) | Phone camera resolution is 80x60. | Real surface temperature. | "Unverified consumer thermal photo" | "Certified infrared engineering void" |
| **TF-06** | **ME** | No thermal data available. Fallback engaged. | 0% | Empty trace array. | Home is insulated. | Real-time thermal envelope efficiency. | "UNKNOWN", "thermal imaging scan recommended" | "Thermal barrier in excellent state" |
| **TF-07** | **RE** | Excludes drone thermal scan with sun glare reflection artifacts. | 0% (Fallback) | Excluded `ev_9077` (revoked tag) | No other thermal telemetry. | Attic heat signature. | "Solar glint scan excluded", "UNKNOWN" | "UAV confirmed hot spot on roof" |
| **TF-08** | **DE** | Window header thermal leakage; duplicate FLIR images merged. | 95% | Merged `ev_9078a` and `ev_9078b` | Both images represent same window. | Header structural framing. | "Deduplicated window thermal leaks" | "Double thermal header failure" |
| **TF-09** | **CS** | Ceiling thermal void linked to active roof leak water saturation of batting. | 85% - 90% | `msn_1079`, `ev_9079`, `kg_path_779` (TF $\rightarrow$ ROOF) | Saturated insulation loses 90% R-value. | Dry batting recovery time. | "Insulation thermal loss linked to roof leak" | "Simple insulation void", "unrelated" |
| **TF-10** | **HO** | Reviewer overrides thermal rating to FAILING; extreme heat signature on electrical breaker. | 95% | `pe_1280` override, `user_104` (Atlas) | Breaker temp is > 160°F, fire risk. | Breaker torque specifications. | "Atlas override", "extreme electrical heat" | "Minor thermal wear on panel" |

---

### DOMAIN 9: ENERGY PERFORMANCE (ENERGY_PERFORMANCE)
*   **Decay Constant ($\lambda$):** `0.00095` (Medium)

| Case ID | Archetype | Expected Conclusion | Expected Conclusion | Expected Confidence | Evidence Trace | Key Assumptions | Unknowns | Allowed Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EP-01** | **FV** | Energy score is 68/100; HVAC blower draws 420W over nominal standard. | 95% - 100% | `msn_1081`, `ev_9081` (CT clamp logs), `pe_1281` | Home heated by gas, cooled by electricity. | Duct joint air leakage. | "Calculated performance score 68", "excess load" | "Energy Star certified green" |
| **EP-02** | **SI** | Attic insulation performance is R-30 based on 3 localized ruler depth spot checks. | 75% - 85% | `msn_1082`, `ev_9082` (ruler photos) | Cellulose density is 1.5 lb/cu ft. | R-value around eaves. | "Spot depth measurements indicate" | "R-30 verified across 100% attic" |
| **EP-03** | **CE** | Envelope leak rate conflict; blower door tech writes 4.2 ACH50, utility bill says normal. | 45% - 55% | `msn_1083`, `ev_9083` (Blower Door), `ev_9084` (Bill) | Homeowner occupancy count is 2. | Wind infiltration velocity. | "Envelope leakage mismatch", "verify" | "Air infiltration 100% sealed" |
| **EP-04** | **SE** | Annual energy score stable; based on 3-year-old Energy Auditor stamp. | 40% - 50% | `msn_1084` (2023-04), `ev_9085`, `pe_1284` | Air sealing spray foam has not degraded. | HVAC compressor decay rate. | "Historic energy audit", "medium decay" | "Active energy efficiency certified" |
| **EP-05** | **LQ** | Drafty windows reported by homeowner with high winter heating bill scan. | 35% - 45% | `ev_9086` (homeowner utility bill) | Thermostat schedule is set to 72°F. | Internal heat source count. | "Unverified homeowner bill upload" | "Certified HVAC failure" |
| **EP-06** | **ME** | No energy performance telemetry available. Fallback engaged. | 0% | Empty trace array. | Home uses standard split heat pump. | Wall cavity R-value. | "UNKNOWN", "energy audit recommended" | "Highly energy efficient dwelling" |
| **EP-07** | **RE** | Excludes utility billing logs with missing gas data. | 0% (Fallback) | Excluded `ev_9087` (revoked tag) | No other billing files. | True baseline load. | "Billing logs excluded", "UNKNOWN" | "Power draw confirmed stable" |
| **EP-08** | **DE** | Heat pump COP validated; duplicate compressor sensor logs merged. | 95% | Merged `ev_9088a` and `ev_9088b` | Air flow is 1200 CFM. | Crankcase heater duty cycle. | "Deduplicated compressor current draw" | "Double compressor load detected" |
| **EP-09** | **CS** | Inadequate crawlspace floor insulation causing drafty floors and high heat pump draw. | 85% - 90% | `msn_1089`, `ev_9089`, `kg_path_780` (EP $\rightarrow$ HVAC) | Crawlspace vents are open. | Duct air sealing rate. | "Heat pump power draw linked to floor void" | "HVAC unit decay", "unrelated" |
| **EP-10** | **HO** | Reviewer overrides energy score to 40 due to single-pane window frames found on site. | 95% | `pe_1290` override, `user_104` (Atlas) | Single-pane windows lower total R-value. | Wall framing cavity thermal bridges. | "Atlas override", "single-pane window draft" | "Calculated high efficiency score" |

---

### DOMAIN 10: INSURANCE CLAIMS (INSURANCE_CLAIMS)
*   **Decay Constant ($\lambda$):** `0.00095` (Medium)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IC-01** | **FV** | Hail damage claim; 12 circular impacts per square on south roof pitch. | 95% - 100% | `msn_1091` (tactile grid), `ev_9091` (gauge photo), `pe_1291` | Hail diameter exceeded 1.5 inches. | Micro-fracturing of roof deck. | "Verified hail impacts", "gauge photos" | "Certain roof failure", "no wear exists" |
| **IC-02** | **SI** | Siding damage claim open; based on photo spot checks of front facade only. | 75% - 85% | `msn_1092`, `ev_9092` (siding photos) | Damage is localized to front slope. | Back wall cladding integrity. | "Facade spot check", "siding cracks" | "Complete cladding coverage certified" |
| **IC-03** | **CE** | Storm damage dispute; contractor files hail log, insurance adjuster writes "wear". | 45% - 55% | `msn_1093`, `ev_9093` (Contractor), `ev_9094` (Adjuster) | Both reports represent same roof slope. | Pre-existing shingle weathering rate. | "Direct claim evaluation conflict" | "Hail damage confirmed", "no storm" |
| **IC-04** | **SE** | Storm damage claim finalized; based on 2-year-old closed insurance adjustment. | 40% - 50% | `msn_1094` (2024-05), `ev_9095`, `pe_1294` | Repair work was performed after claim. | Latent structural fatigue. | "Historic finalized claim records" | "Active insurance claim", "open status" |
| **IC-05** | **LQ** | Possible wind damage; resident uploads photo of a tree limb on driveway. | 35% - 45% | `ev_9096` (homeowner photo) | Limb fell from adjacent property. | Damage to roof under limb. | "Resident photo of fallen limb" | "Certified structural storm damage" |
| **IC-06** | **ME** | No insurance claim records found. Fallback engaged. | 0% | Empty trace array. | Property is currently insured. | Outstanding private claims. | "UNKNOWN", "no claim history recorded" | "Property holds clear claim history" |
| **IC-07** | **RE** | Excludes adjuster report due to incorrect property address on face. | 0% (Fallback) | Excluded `ev_9097` (revoked tag) | No other adjuster records. | Adjuster valuation amount. | "Adjuster file excluded", "UNKNOWN" | "Adjuster confirmed $5,000 damage" |
| **IC-08** | **DE** | Siding puncture confirmed; duplicate impact logs merged. | 95% | Merged `ev_9098a` and `ev_9098b` | Both logs represent same siding panel. | Sub-sheathing puncture. | "Deduplicated siding puncture records" | "Multiple siding punctures detected" |
| **IC-09** | **CS** | Siding storm damage linked to wet wall cavity insulation on north facade. | 85% - 90% | `msn_1099`, `ev_9099`, `kg_path_781` (IC $\rightarrow$ WATER) | Rain penetrated through punctured cladding. | Cavity wood rot propagation. | "Cladding storm damage linked to leak" | "Cosmetic vinyl damage only", "dry" |
| **IC-10** | **HO** | Reviewer overrides claim status to IN REWORK; adjuster missed attic water stain. | 95% | `pe_1300` override, `user_104` (Atlas) | Attic stain represents active damage. | Leak path through shingles. | "Atlas override", "rework for missed stain" | "Adjuster calculation final" |

---

### DOMAIN 11: MAINTENANCE (MAINTENANCE)
*   **Decay Constant ($\lambda$):** `0.00095` (Medium)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MN-01** | **FV** | HVAC air filter replacement overdue; filter has 120-day accumulation. | 95% - 100% | `msn_1101`, `ev_9101` (Filter photo), `pe_1301` | MERV rating is 8; run time is standard. | Dust mite concentrations. | "Overdue filter replacement", "clogged" | "Air filter clean", "HVAC fully serviced" |
| **MN-02** | **SI** | Gutter cleaning required based on front downspout blockage spot checks. | 75% - 85% | `msn_1102`, `ev_9102` (downspout photo) | Back gutter runs have similar debris. | Pitch slope angle of back gutters. | "Spot-checks indicate debris blockage" | "All gutters clean", "100% flow clear" |
| **MN-03** | **CE** | Water heater flushing conflict; homeowner says "done", tech writes "heavy scale". | 45% - 55% | `msn_1103`, `ev_9103` (Owner), `ev_9104` (Tech text) | Water hardness is 15 grains per gallon. | Heating element scale thickness. | "Flushing status mismatch", "verify" | "Heater flushed", "tank corroded" |
| **MN-04** | **SE** | Deck sealing stable; based on 3-year-old contractor invoice and photos. | 40% - 50% | `msn_1104` (2023-06), `ev_9105`, `pe_1304` | Sealant was premium oil-based. | Splintering rate of wood boards. | "Historic sealing records", "medium decay" | "Active deck sealing verified" |
| **MN-05** | **LQ** | Squeaking garage door reported by resident with no maintenance log. | 35% - 45% | `ev_9106` (tenant app log) | Door has steel rollers and torsion spring. | Roller track alignment. | "Resident-reported squeaking door" | "Certified mechanical spring failure" |
| **MN-06** | **ME** | No maintenance log available. Fallback engaged. | 0% | Empty trace array. | Home has standard maintenance schedules. | Mechanical motor lifetimes. | "UNKNOWN", "maintenance review suggested" | "Maintenance schedules fully current" |
| **MN-07** | **RE** | Excludes maintenance log with wrong equipment serial number. | 0% (Fallback) | Excluded `ev_9107` (revoked tag) | No other maintenance logs. | True filter age. | "Maintenance file excluded", "UNKNOWN" | "Filter changed 10 days ago" |
| **MN-08** | **DE** | Gutter debris confirmed; duplicate photo logs merged. | 95% | Merged `ev_9108a` and `ev_9108b` | Photos show the same north corner gutter. | Gutter bracket load rating. | "Deduplicated gutter debris logs" | "Multiple gutter blockages", "severe" |
| **MN-09** | **CS** | Overdue gutter cleaning causing water overflow onto fascia wood rot. | 85% - 90% | `msn_1109`, `ev_9109`, `kg_path_782` (MN $\rightarrow$ ROOF) | Overflow is due to leaf blockage. | Fascia board wood rot depth. | "Gutter overflow linked to fascia rot" | "Normal roof runoff", "dry fascia" |
| **MN-10** | **HO** | Reviewer overrides maintenance status to CRITICAL; chimney cap mortar cracked. | 95% | `pe_1310` override, `user_104` (Atlas) | Cracked cap allows direct rain path. | Brick flue internal flue blockages. | "Atlas override", "chimney cap crack" | "Cosmetic brick weathering" |

---

### DOMAIN 12: PROJECT OPPORTUNITIES (PROJECT_OPPORTUNITIES)
*   **Decay Constant ($\lambda$):** `0.00095` (Medium)

| Case ID | Archetype | Expected Conclusion | Expected Confidence | Evidence Trace Elements | Key Assumptions | Unknowns | Allowed Language | Prohibited Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PO-01** | **FV** | Heat pump conversion opportunity; gas furnace is 18 years old. | 95% - 100% | `msn_1111`, `ev_9111` (Plate photo), `pe_1311` | Home is in an active utility rebate zone. | Panel capacity for 240V circuit. | "Furnace age confirmed", "retrofit viable" | "Conversion guaranteed", "no cost" |
| **PO-02** | **SI** | Solar retrofit potential high based on south roof pitch angle spot check. | 75% - 85% | `msn_1112`, `ev_9112` (roof slope photos) | Shading coefficient is less than 15%. | Utility net metering tariff caps. | "Solar potential indicated by slope" | "Solar viability 100% verified" |
| **PO-03** | **CE** | Solar viability dispute; aerial scan says "ideal", local utility says "grid full". | 45% - 55% | `msn_1113`, `ev_9113` (Drone), `ev_9114` (Utility letter) | Inverter output matches main service. | Interconnection transformer limits. | "Solar connection mismatch", "verify" | "Solar ready", "grid connection blocked" |
| **PO-04** | **SE** | Heat pump water heater retrofit potential; based on 2-year-old energy audit. | 40% - 50% | `msn_1114` (2024-05), `ev_9115`, `pe_1314` | Floor space in garage is still 4x4 ft. | Current electrical panel loads. | "Historic retrofit energy audit" | "Active retrofit viability certified" |
| **PO-05** | **LQ** | EV charger retrofit opportunity reported by resident via inquiry ticket. | 35% - 45% | `ev_9116` (resident support ticket) | Panel is located in garage. | Service lateral wire gauge size. | "Unverified resident charger request" | "NEC certified EV charging retrofit" |
| **PO-06** | **ME** | No project opportunities data available. Fallback engaged. | 0% | Empty trace array. | Homeowner has budget for upgrades. | Local rebate code updates. | "UNKNOWN", "energy audit needed" | "No energy retrofits are possible" |
| **PO-07** | **RE** | Excludes solar potential report with incorrect shading model. | 0% (Fallback) | Excluded `ev_9117` (revoked tag) | No other project files. | Roof irradiance profile. | "Solar model excluded", "UNKNOWN" | "Model confirmed 9.5 kW output" |
| **PO-08** | **DE** | Heat pump upgrade potential; duplicate model plates merged. | 95% | Merged `ev_9118a` and `ev_9118b` | Both plates match the same Lennox furnace. | Blower cabinet width. | "Deduplicated furnace specifications" | "Multiple furnaces found", "failure" |
| **PO-09** | **CS** | Old single-pane wood windows present opportunity for low-E vinyl replacement. | 85% - 90% | `msn_1119`, `ev_9119`, `kg_path_783` (PO $\rightarrow$ WN) | Wall structure can support standard frames. | Local historic preservation codes. | "Window replacement opportunity" | "Structural framing decay", "unrelated" |
| **PO-10** | **HO** | Reviewer overrides solar potential; nearby pine trees block roof shading. | 95% | `pe_1320` override, `user_104` (Atlas) | Pine trees represent permanent shading. | Tree removal municipal codes. | "Atlas override", "solar potential low" | "Calculated high solar index" |

---

## 4. Corpus Maintenance & Verification Protocol

1. **Monotonic Progression Check:** Under no circumstances should duplicate evidence entries (`RF-08`, `FD-08`, etc.) inflate the overall confidence score above that of the single verified evidence source.
2. **Revocation Assertion:** If `is_revoked: true` is flagged on any evidence node in the Mongo database, the system must exclude that node from the trace, recalculate weights, and lower confidence or fall back to `UNKNOWN`.
3. **Trace Execution:** For every case, the trace payload must include the cryptographic signature verifying that no data was modified post-ingestion.
