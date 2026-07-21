# EXPLANATION TEMPLATES SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 013 · OPERATION INTELLIGENCE EXPLAINER
**Status:** STANDARD COMPILATION COMPLETE  
**Scope:** Canonical narrative and formatting templates for all 12 core building systems and analytical domains.

---

## 1. Overview of Template Registry

This specification establishes the standardized templates for the 12 critical structural, mechanical, and logical systems of the Stratex-2 platform. The templates define how variables and structures are merged to output Level 1 (Homeowner), Level 2 (Contractor), and Level 3 (Engineering) narratives.

Each template defines:
*   **System Focus:** The domain or building subsystem being analyzed.
*   **Required Ingestion Nodes:** The physical evidence and DNA data needed to activate the template.
*   **Structured Templates & Real-World Examples:** Comprehensive, populated narrative configurations showing how the standard 8 elements (Conclusion, Supporting Evidence, Confidence, Why this Matters, Next Steps, Related Systems, Assumptions, Unknowns) are written for each level.

---

## 2. The 12 Canonical Templates & Examples

---

### TEMPLATE 1: ROOF
*   **System Focus:** Shingles, underlayment, valleys, flashing, decking, and drainage gutters.
*   **Required Ingestion Nodes:** High-res orthomosaic flight pictures, moisture sensor arrays, inspector tactile surveys.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your roof has a minor section of shingle damage on the north slope.
    *   **Supporting Evidence:** High-resolution photos from our recent drone survey showed exactly 5 cracked asphalt shingles.
    *   **Confidence:** High (95%). This is based on clear optical proof taken under direct sunlight yesterday.
    *   **Why this Matters:** Cracked shingles let rainwater seep beneath your roof. Over time, this leads to attic ceiling leaks, mold, and wood rot.
    *   **Recommended Next Steps:** Have a licensed roofing contractor replace the 5 damaged shingles before winter.
    *   **Related Systems:** Attic ceiling drywall, home insulation layers.
    *   **Assumptions:** The shingles are 12-year-old standard asphalt shingles with typical weathering.
    *   **Unknowns:** We cannot see the wood boards directly beneath the shingles without removing them.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Localized mechanical fracture of 5 asphalt shingle tabs on the northeast quadrant, course 14.
    *   **Supporting Evidence:** Flight ID `msn_1001`, high-res image `img_4021` showing tab delamination and hairline cracking.
    *   **Confidence:** 95% based on visual observation with zero obstructions or shadows.
    *   **Why this Matters:** Exposed underlayment creates a point of entry for rain, lowering water-tightness and threatening structural decking beneath.
    *   **Recommended Next Steps:** Remove affected courses, replace with matching ASTM D3462 shingles, and reseal adjacent tabs with asphalt mastic.
    *   **Related Systems:** Ridge cap vents, starter strip course, gutter run-off.
    *   **Assumptions:** Plywood sheathing is standard 1/2-inch CDX.
    *   **Unknowns:** Integrity of organic felt layer under the broken shingle tabs.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Localized failure of asphalt shingles on the northeast slope due to thermal splitting and wind-shear delamination of tab adhesive layers.
    *   **Supporting Evidence:** Photogrammetry telemetry (`img_4021`) indicating crack apertures of 1.5mm and loss of granular mineral layer.
    *   **Confidence:** 95% calculated from dual-pass aerial optical capture at 2cm per-pixel resolution.
    *   **Why this Matters:** The split tabs expose the asphalt-saturated organic felt layer. The decay rate of felt under UV exposure exceeds 0.5mm per month, leading to rapid moisture-barrier degradation.
    *   **Recommended Next Steps:** Repair shingles to maintain wind uplift resistance of 110mph under ASCE 7-22 structural wind load standards.
    *   **Related Systems:** Roof membrane, under-roof ventilation draft envelope.
    *   **Assumptions:** Roof pitch is 6:12; structural dead load rating is 15 lbs/sq ft.
    *   **Unknowns:** Dynamic load bearing capacity of structural rafters around the northeast slope interface.

---

### TEMPLATE 2: FOUNDATION
*   **System Focus:** Concrete slab, crawlspace joists, basement retaining walls, soil grading.
*   **Required Ingestion Nodes:** Laser levelling scans, soil moisture telemetry, visual crack logs.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your foundation is stable, but we found a small hairline crack in the crawlspace wall.
    *   **Supporting Evidence:** Visual inspection photos of the crawlspace concrete wall showing a tiny crack less than 1/16 inch wide.
    *   **Confidence:** Moderate (85%). The crack is visible but has only been inspected once.
    *   **Why this Matters:** Small cracks are normal as a house settles. However, if water gets inside, it can freeze, expand, and widen the crack.
    *   **Recommended Next Steps:** Monitor the crack over the next 6 months to see if it grows or leaks water.
    *   **Related Systems:** Basement flooring, crawlspace moisture barrier.
    *   **Assumptions:** The house is settling normally on standard sandy-clay soil.
    *   **Unknowns:** We do not know if this crack is actively widening without future measurements.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Vertical shrinkage crack, approx 1mm wide, in concrete foundation stem wall, grid section D-4.
    *   **Supporting Evidence:** Inspector report `ins_820` and photograph `img_1192` showing localized dry shrinkage. No efflorescence present.
    *   **Confidence:** 85% based on single-point visual and mechanical width-gauge measurement.
    *   **Why this Matters:** Stem-wall cracking can allow insect entry and slow moisture migration. Currently structural integrity is unaffected.
    *   **Recommended Next Steps:** Clean joint and seal with polyurethane expanding crack injector.
    *   **Related Systems:** Perimeter drainage lines, crawlspace sub-floor.
    *   **Assumptions:** Cast-in-place concrete compressive strength is 3,000 PSI.
    *   **Unknowns:** Rebar placement depth inside the concrete core at the cracking location.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Non-structural vertical shrinkage crack (1.0mm) in cast-in-place concrete stem wall due to normal cementitious hydration decay.
    *   **Supporting Evidence:** Width-gauge logging (`img_1192`) indicating zero shear displacement or out-of-plane rotation.
    *   **Confidence:** 85% calculated from calibrated digital optical comparison.
    *   **Why this Matters:** Under ACI 318 standards, non-structural cracks under 1.5mm are classified as acceptable weathering. However, capillary action can draw sub-grade water, risking rebar oxidation.
    *   **Recommended Next Steps:** Inject low-viscosity structural epoxy to reinstate full tensile capacity and moisture barrier.
    *   **Related Systems:** Retaining walls, concrete footers.
    *   **Assumptions:** Stem wall is non-retaining; soil grading has a positive 5% slope away from the cracking zone.
    *   **Unknowns:** Tensile load margins of the steel reinforcing matrix inside the wall core.

---

### TEMPLATE 3: WINDOWS
*   **System Focus:** Window frames, glazing seals, flashing joints, sash operations.
*   **Required Ingestion Nodes:** Thermal imaging, vacuum leak detection, operational friction logs.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** The double-pane window seal in your master bedroom has failed, causing foggy glass.
    *   **Supporting Evidence:** Photos showing persistent condensation trapped between the glass panes of the master bedroom window.
    *   **Confidence:** High (90%). Condensation between panes is a guaranteed sign of seal failure.
    *   **Why this Matters:** Failed seals let the insulating gas leak out, making the window less energy efficient. This raises your heating and cooling bills.
    *   **Recommended Next Steps:** Contact a window technician to replace the insulated glass unit (IGU) in that window frame.
    *   **Related Systems:** Bedroom heating and cooling.
    *   **Assumptions:** The window frame is in good physical shape and only the glass unit needs replacement.
    *   **Unknowns:** We do not know if the window sash frame has hidden wood rot underneath without a physical teardown.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Desiccant saturation and seal breach in double-pane Insulated Glass Unit (IGU) of window ID `win_202`.
    *   **Supporting Evidence:** Visual inspection `ins_822` showing internal condensation ring and glass staining.
    *   **Confidence:** 90% based on clear optical proof of interstitial condensation.
    *   **Why this Matters:** The Argon gas barrier has dissipated, reducing thermal performance and rendering the window sash prone to moisture pooling.
    *   **Recommended Next Steps:** Order a replacement 3/4-inch glass insert and swap the glazing bead package on-site.
    *   **Related Systems:** Siding trim joints, window rough opening framing.
    *   **Assumptions:** Vinyl window frame is in square and has less than 2mm of frame sag.
    *   **Unknowns:** Wood condition of the rough framing sill underneath the vinyl window track.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Degradation of the primary polyisobutylene (PIB) seal in double-pane insulated glass unit (`win_202`) leading to loss of inert Argon gas charge.
    *   **Supporting Evidence:** Thermal scan `th_9921` showing an elevated U-factor from a baseline of 0.30 to an estimated 0.52.
    *   **Confidence:** 90% validated by U-factor thermographic shift modeling.
    *   **Why this Matters:** Loss of the Argon gas envelope decreases the overall insulating R-value of the window by 42%, altering thermal bridging calculations for the north-facing wall.
    *   **Recommended Next Steps:** Perform field replacement of the IGU to satisfy NFRC 100 thermal transmission compliance ratings.
    *   **Related Systems:** Exterior thermal insulation envelope, localized zone heating loads.
    *   **Assumptions:** Window is double-glazed vinyl-framed with low-E coating.
    *   **Unknowns:** Remaining lifespan of adjacent window seals in the master bedroom.

---

### TEMPLATE 4: HVAC
*   **System Focus:** AC condenser, furnace, ductwork, thermostat, air filters.
*   **Required Ingestion Nodes:** Airflow pressure meters, temperature differentials, condenser current draw.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your air conditioner is working well, but its outdoor unit is due for a cleaning.
    *   **Supporting Evidence:** Photos showing grass clippings, leaves, and dust clogging the outdoor AC unit's metal fins.
    *   **Confidence:** High (95%). Dust buildup is clearly visible in the provided inspection photos.
    *   **Why this Matters:** Clogged outdoor units have to work harder to release heat. This strains the system, shortens its lifespan, and increases electricity usage.
    *   **Recommended Next Steps:** Use a gentle garden hose to spray down the outdoor unit fins and remove any dirt.
    *   **Related Systems:** Indoor air quality, main electrical breaker panel.
    *   **Assumptions:** The AC compressor is mechanically healthy and only has surface dirt.
    *   **Unknowns:** We cannot see the condition of the indoor ductwork walls from outside.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Restricted airflow across condenser coils due to surface debris buildup on AC outdoor unit ID `hvac_01`.
    *   **Supporting Evidence:** Visual report `ins_830` and photo `img_2209` showing 40% surface coverage by vegetation and dust.
    *   **Confidence:** 95% based on visual proof of dust density.
    *   **Why this Matters:** Surface debris blocks heat transfer, increasing head pressure inside the compressor and raising amp draw.
    *   **Recommended Next Steps:** Perform chemical coil wash, straighten aluminum fins with a comb, and clear a 2-foot zone around the unit.
    *   **Related Systems:** Compressor motor windings, air handler filter.
    *   **Assumptions:** System refrigerant charge is within manufacturer specifications.
    *   **Unknowns:** Electrical current draw of the condenser fan motor before cleaning.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Sub-optimal heat rejection in HVAC condenser unit (`hvac_01`) due to boundary-layer air insulation caused by particulate accumulation on aluminum fins.
    *   **Supporting Evidence:** Condenser fan motor current logging showing an elevated current draw of 12.4 Amps (nominal rating is 10.1 Amps).
    *   **Confidence:** 95% from electrical current telemetry and high-resolution optical fin analysis.
    *   **Why this Matters:** Elevated operating temperatures reduce the HVAC unit's Seasonal Energy Efficiency Ratio (SEER) from its rated 16.0 to a degraded 11.4, accelerating compressor mechanical winding decay.
    *   **Recommended Next Steps:** Restore design air-volume throughput by executing a thorough fin clearing and coil detergent wash.
    *   **Related Systems:** Liquid refrigerant lines, electrical power factor sub-panel.
    *   **Assumptions:** Refrigerant is R-410A; thermostat calibration has zero offset.
    *   **Unknowns:** Precise internal winding temperature of the compressor motor hermetic assembly.

---

### TEMPLATE 5: ELECTRICAL
*   **System Focus:** Main breaker panel, wiring connections, wall outlets, GFCI safety breakers.
*   **Required Ingestion Nodes:** Thermal camera scans of breaker panels, wire gauge measurements, circuit analyzer reports.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** We found an unsafe, overloaded electrical outlet in your garage.
    *   **Supporting Evidence:** A thermal image showing high heat (110°F) radiating from a single garage wall outlet with three heavy-duty power cords plugged in.
    *   **Confidence:** High (90%). Thermal scans clearly show excessive heat at that specific outlet.
    *   **Why this Matters:** Overloaded outlets generate extreme heat behind the wall, which can melt plastic casing and spark an electrical fire.
    *   **Recommended Next Steps:** Unplug the heavy appliances and spread them out to different electrical circuits.
    *   **Related Systems:** Garage lighting, home fire safety systems.
    *   **Assumptions:** The wiring behind the outlet is standard copper, not old aluminum.
    *   **Unknowns:** We don't know the exact wire thickness inside the wall box without opening the outlet cover.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Thermal hotspot on garage wall outlet, grid E-2, indicating load exceeding rated amp capacity.
    *   **Supporting Evidence:** Thermal scan ID `th_1002` showing a temperature differential of +35°F above ambient room temperature at the terminal screws.
    *   **Confidence:** 90% based on professional-grade infrared thermography.
    *   **Why this Matters:** Sustained terminal temperatures of 110°F can degrade wire insulation, leading to short-circuits and structural combustion.
    *   **Recommended Next Steps:** Open outlet box, verify wire gauge (12 AWG copper), and divide loads by running a dedicated 20-Amp circuit if necessary.
    *   **Related Systems:** Main panel breaker #4, outlet drywall box structure.
    *   **Assumptions:** Outlet is standard 15-Amp residential grade.
    *   **Unknowns:** Loose screw terminal connection vs. pure over-current as the primary heat source.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Interfacial thermal hotspot (+19.4°C over ambient) at electrical outlet terminal interface due to elevated contact resistance or over-current loading.
    *   **Supporting Evidence:** Thermographic imaging dataset `th_1002` recording an absolute temperature of 43.3°C under load.
    *   **Confidence:** 90% validated by high-resolution FLIR micro-bolometer matrix analysis.
    *   **Why this Matters:** Under NEC Article 210, residential terminal temperatures must not exceed 40°C. Sustained heat causes carbonization of the thermoplastic receptacle material, decreasing dielectric strength and inducing arc-fault hazards.
    *   **Recommended Next Steps:** Dismantle outlet, measure torque on terminal screws to confirm compliance with UL 486A-486B specifications, or replace with a heavy-duty receptacle.
    *   **Related Systems:** Overcurrent protection breakers, thermal wall decay models.
    *   **Assumptions:** Wire material is annealed copper with a 90°C THHN insulation rating.
    *   **Unknowns:** Exact electrical current wave-form harmonic distortion levels on that specific circuit branch.

---

### TEMPLATE 6: PLUMBING
*   **System Focus:** Supply pipes, drain lines, water heaters, water shutoff valves.
*   **Required Ingestion Nodes:** Water flow meters, acoustic leak detectors, pressure tests.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your main water shutoff valve is rusty and stuck, making it hard to close in an emergency.
    *   **Supporting Evidence:** Photos showing rust buildup and a seized handle on the main brass water valve in the basement.
    *   **Confidence:** Moderate (85%). The valve is rusty and was reported as stuck by the inspector.
    *   **Why this Matters:** If a pipe bursts in your home, you must turn off the main valve immediately. If it's stuck, water will flood your home, causing massive damage.
    *   **Recommended Next Steps:** Have a plumber replace the rusty gate valve with a modern, easy-to-turn ball valve.
    *   **Related Systems:** Water supply lines, water heater safety.
    *   **Assumptions:** The copper water line connected to the valve is still in good condition.
    *   **Unknowns:** We do not know if the rust has eaten through the internal valve seals.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Mechanical seize of main water shutoff gate valve due to heavy oxide accumulation.
    *   **Supporting Evidence:** Visual report `ins_844` and photo `img_4411` showing severe oxidation on brass stem and steel handle.
    *   **Confidence:** 85% based on physical torque test by certified inspector.
    *   **Why this Matters:** Inability to isolate supply water during plumbing system failures prevents emergency damage control and code compliance.
    *   **Recommended Next Steps:** Drain system, cut out old brass gate valve, and sweat-solder a new full-port brass ball valve.
    *   **Related Systems:** Water meter assembly, main copper supply line.
    *   **Assumptions:** Main pipe material is 3/4-inch L-type copper.
    *   **Unknowns:** Municipal water pressure before the house pressure-reducing valve.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Mechanical immobilization of brass gate valve stem assembly caused by galvanic corrosion and calcium-carbonate mineral build-up.
    *   **Supporting Evidence:** In-field mechanical stress logs (`ins_844`) confirming failure of gate wedge to move along the stem threads under normal operating torque limits.
    *   **Confidence:** 85% from mechanical failure logs and localized chemical deposit analysis.
    *   **Why this Matters:** Failed isolation mechanisms violate IPC Section 606.1 code requirements. Additionally, galvanic oxidation at the brass-steel junction reduces thread sheer margins, threatening mechanical failure during high-torque manipulation.
    *   **Recommended Next Steps:** Replace with full-port quarter-turn stainless steel ball valve compliant with MSS SP-110 specifications.
    *   **Related Systems:** Primary municipal supply line, water distribution pressure grids.
    *   **Assumptions:** Structural water pressure is regulated to a static 55 PSI.
    *   **Unknowns:** The condition of the internal municipal curb stop isolation valve at the street.

---

### TEMPLATE 7: WATER INTRUSION
*   **System Focus:** Attic moisture, basement humidity, foundation perimeter drainage.
*   **Required Ingestion Nodes:** Pin moisture meters, continuous humidity monitors, acoustic flow logs.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** High humidity and dampness are pooling in your basement's northeast corner.
    *   **Supporting Evidence:** Continuous readings from our dampness sensor showing basement air humidity hovering at 78% for a full week.
    *   **Confidence:** High (92%). The sensor has been collecting accurate humidity data every hour.
    *   **Why this Matters:** Sustained humidity over 60% allows toxic mold to grow, spoils carpets, rots basement framing, and creates musty odors.
    *   **Recommended Next Steps:** Install a dehumidifier in the basement and make sure gutters dump water far away from the house.
    *   **Related Systems:** Gutter downspouts, crawlspace vents.
    *   **Assumptions:** The basement dampness is caused by rain soaking through the concrete walls.
    *   **Unknowns:** We do not know if there is an active underground spring pushing water up under the concrete floor.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Elevated ambient relative humidity (78% RH) and capillary moisture migration in basement corner grid section B-1.
    *   **Supporting Evidence:** Sensor ID `hum_88` logging continuous humidity > 75% over 168 hours and visual white efflorescence powder on concrete.
    *   **Confidence:** 92% based on calibrated long-term telemetry array.
    *   **Why this Matters:** Concrete efflorescence indicates active mineral leaching caused by hydrostatic pressure, risking paint peel, drywall decay, and spore germination.
    *   **Recommended Next Steps:** Grade the outside soil to fall 6 inches over the first 10 feet from the foundation, and apply crystalline waterproofing sealer on interior concrete.
    *   **Related Systems:** Exterior foundation grading, basement drywall plates.
    *   **Assumptions:** Sub-slab vapor barrier is either non-existent or punctured.
    *   **Unknowns:** Exact composition of the backfill soil surrounding the northeast foundation wall.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Sustained capillary moisture transport and hydrostatic pressure gradient forcing moisture through basement concrete wall assembly.
    *   **Supporting Evidence:** Humidity sensor `hum_88` documenting continuous vapor pressure exceeding 2.1 kPa. Mechanical visual verification of concrete efflorescence and salt crystallization.
    *   **Confidence:** 92% validated by thermodynamic moisture vapor pressure models.
    *   **Why this Matters:** Sustained interior RH of 78% is sufficient to support structural wood decay and rapid proliferation of mold (Stachybotrys chartarum). Hydrostatic saturation of the concrete matrix reduces its shear friction resistance and accelerates masonry decay.
    *   **Recommended Next Steps:** Install exterior footing drains (French drain system) and apply an elastomeric membrane on the exterior foundation face to reverse the pressure gradient.
    *   **Related Systems:** Masonry retaining walls, foundation footings, interior ventilation grids.
    *   **Assumptions:** Concrete porosity is typical for residential structural pours (0.15 volume fraction).
    *   **Unknowns:** The presence or condition of original exterior footing drain tiles.

---

### TEMPLATE 8: THERMAL FINDINGS
*   **System Focus:** Thermal bridging, missing insulation, wall cavities, HVAC air leak thermal signatures.
*   **Required Ingestion Nodes:** Infrared thermographic cameras, indoor/outdoor temperature sensors.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your attic is missing insulation in several large spots, letting heat leak out.
    *   **Supporting Evidence:** A thermal picture of your attic ceiling showing hot spots (or cold spots in winter) that align with uninsulated plasterboard.
    *   **Confidence:** High (90%). The thermal camera pictures clearly show missing insulation outlines.
    *   **Why this Matters:** Missing insulation lets warm air escape your home in winter and hot air leak in during summer. This causes your AC and heater to run constantly and increases your energy bills.
    *   **Recommended Next Steps:** Lay down fiberglass insulation rolls to cover the bare spots on your attic floor.
    *   **Related Systems:** Roof heating, main HVAC air duct system.
    *   **Assumptions:** The rest of the attic insulation is standard R-30 fiberglass batting.
    *   **Unknowns:** We cannot tell if rodents have chewed or nested inside the insulation we can't see.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Wall cavity thermal bridging and missing insulation batts across 4 joist bays in attic zone C.
    *   **Supporting Evidence:** Infrared scan `th_8820` showing clear geometric heat-loss voids corresponding to bare drywall bays.
    *   **Confidence:** 90% based on professional thermal-camera imagery under a delta-T of 20°F.
    *   **Why this Matters:** Uninsulated bays reduce the attic R-value from a design target of R-30 down to R-3 in affected zones, creating cold drafts and localized moisture condensation risk.
    *   **Recommended Next Steps:** Install R-38 blown-in cellulose or fiberglass batts to achieve continuous thermal envelope.
    *   **Related Systems:** Attic hatch seals, HVAC duct wraps.
    *   **Assumptions:** Attic floor joists are standard 2x8 lumber spaced 16 inches on center.
    *   **Unknowns:** Condition of electrical wire junction boxes beneath adjacent insulation layers.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Discontinuous thermal boundary layer and high-flux heat transmission in attic joist bays due to complete omission of insulation material.
    *   **Supporting Evidence:** Thermographic dataset `th_8820` showing local heat-flux rate of 4.2 BTU/hr/sq.ft/°F against a nominal surrounding baseline of 0.03 BTU/hr/sq.ft/°F.
    *   **Confidence:** 90% calculated under ASTM C1153 thermographic inspection standards.
    *   **Why this Matters:** The local thermal resistance (R-value) drops by 90% in these bays. This localized heat loss shifts the building envelope's dew-point interface, inducing water-vapor condensation directly on the interior paper-faced drywall.
    *   **Recommended Next Steps:** Blow in cellulose insulation to establish a uniform, continuous thermal barrier satisfying ASHRAE 90.1 energy envelope code criteria.
    *   **Related Systems:** Building thermal envelope, mechanical heating design loads.
    *   **Assumptions:** Attic ventilation is balanced via equal intake/exhaust area.
    *   **Unknowns:** Absolute wood moisture content of the ceiling drywall joist plates in the affected bays.

---

### TEMPLATE 9: ENERGY PERFORMANCE
*   **System Focus:** Home energy efficiency, R-values, solar performance, air sealing.
*   **Required Ingestion Nodes:** Blower door airtightness tests, smart utility meter datasets.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your home is slightly drafts and is losing more energy than average.
    *   **Supporting Evidence:** Our blower door test recorded an air leakage rate that is 25% higher than energy-efficient guidelines.
    *   **Confidence:** High (95%). This is based on a standard mechanical pressure test of your home.
    *   **Why this Matters:** High air leakage means drafts are constantly letting outside air in. This forces your mechanical systems to run longer, raising bills and lowering comfort.
    *   **Recommended Next Steps:** Apply weatherstripping around exterior doors and use silicone caulk around drafty window frames.
    *   **Related Systems:** Heating and cooling, window frame joints.
    *   **Assumptions:** The home's exterior doors have standard wood or metal frames with aged weather seals.
    *   **Unknowns:** We do not know if there are major air leaks in the hidden rim joists under the first floor.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Excessive envelope leakage rate measuring 7.5 ACH50 on blower door depressurization test.
    *   **Supporting Evidence:** Blower door log `test_992` recording air flow of 2,100 CFM at 50 Pascals of differential pressure.
    *   **Confidence:** 95% based on calibrated digital manometer testing.
    *   **Why this Matters:** Energy-code baseline is 3.0 to 5.0 ACH50. High leakage increases infiltration of moisture-laden air, loading mechanical equipment and raising energy costs.
    *   **Recommended Next Steps:** Air-seal the attic floor plates, window frames, plumbing penetrations, and rim joists using low-expansion polyurethane foam.
    *   **Related Systems:** Attic bypasses, fireplace dampers, exterior siding wraps.
    *   **Assumptions:** Interior volume of the conditioned space is 16,800 cubic feet.
    *   **Unknowns:** Exact leak distribution percentage between the ceiling plane and the foundation sill plate.
*   **Level 3 (Engineering):**
    *   **Conclusion:** High structural air infiltration rate of 7.5 Air Changes per Hour at 50 Pa (ACH50) due to unsealed envelope bypasses.
    *   **Supporting Evidence:** Calibrated air-flow metrics from manometer log `test_992` documenting a leakage area equivalent to 144 square inches of open window space.
    *   **Confidence:** 95% compliant with ASTM E779 air-leakage measurement guidelines.
    *   **Why this Matters:** The high infiltration rate increases convective heat transfer across the envelope, expanding peak mechanical heating load from a design-basis 32,000 BTU/hr to 44,500 BTU/hr, thus degrading operational SEER/COP profiles.
    *   **Recommended Next Steps:** Systematically seal rim-joist perimeters and utility penetrations to drop infiltration below IECC 2021 code threshold of 3.0 ACH50.
    *   **Related Systems:** Passive HVAC ventilation, convective thermal loops.
    *   **Assumptions:** Conditioned volume calculations incorporate cathedral ceiling voids.
    *   **Unknowns:** Mechanical exhaust duct leakage rates outside the conditioned envelope.

---

### TEMPLATE 10: INSURANCE CLAIMS
*   **System Focus:** Wind damage, hail impact marks, water claim assessments, storm events.
*   **Required Ingestion Nodes:** Historic wind velocity databases, aerial impact imagery, storm timestamp logs.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your roof shingle damage is consistent with the major hailstorm that occurred last week.
    *   **Supporting Evidence:** Weather station logs confirm 1.5-inch hail in your neighborhood on 2026-07-15, matching circular dent marks found on your vents yesterday.
    *   **Confidence:** Moderate (85%). The weather data and roof dents match, but we must verify if the roof was already dented before the storm.
    *   **Why this Matters:** Insurance policies usually cover storm damage if claimed promptly. Circular dents on shingles weaken their structure and cause them to lose their protective gravel coating, leading to premature leaks.
    *   **Recommended Next Steps:** Submit our verified weather and damage report to your insurance adjuster to open a claim.
    *   **Related Systems:** Gutters, attic rafters.
    *   **Assumptions:** The shingles were in good condition with no hail damage before the 2026-07-15 storm.
    *   **Unknowns:** The exact age of the shingle wear before the storm occurred is unverified.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Functional hail impact damage to roofing shingles and metal accessories, matching NOAA storm event on 2026-07-15.
    *   **Supporting Evidence:** Weather data `noaa_901` showing 1.5-inch diameter ice stones at coordinates, and photo `img_772` showing 8 fracture bruises per square on south slope.
    *   **Confidence:** 85% based on correlating storm radar logs and visual circular fracture patterns.
    *   **Why this Matters:** circular bruising fractured the shingle fiberglass mat, which voids manufacturer warranties and permits immediate granule shedding, exposing the raw asphalt to UV breakdown.
    *   **Recommended Next Steps:** Prepare complete repair scope estimate for full south-slope shingle replacement to submit for claim adjustment.
    *   **Related Systems:** Valley flashing, aluminum gutter troughs.
    *   **Assumptions:** Mat fractures are active and not weathered/oxidized from old storm seasons.
    *   **Unknowns:** Whether the insurance carrier will require core-sample laboratory testing to prove mat fracture.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Mechanical fracture of shingle fiberglass reinforcement substrate caused by high-velocity impact of hail stones, correlated to storm event of 2026-07-15.
    *   **Supporting Evidence:** Localized radar reflectivity data (NEXRAD) indicating 38mm hail cores, matched with physical on-site micro-fracture analysis showing circular compression bruises of 35-40mm.
    *   **Confidence:** 85% calculated under ASCE structural damage forensic criteria.
    *   **Why this Matters:** High-velocity ice impacts exceed the elastic limits of weathered asphalt binders. The resulting mat fracture lowers wind-uplift limits and initiates rapid granule displacement, exposing the underlying bitumen to accelerated photo-oxidation.
    *   **Recommended Next Steps:** Draft a certified engineering damage assessment report detailing the density and distribution of functional damage.
    *   **Related Systems:** Gutter discharge paths, metal flashing.
    *   **Assumptions:** Shingles are standard 3-tab organic asphalt shingles; asphalt binder has reached its embrittlement phase.
    *   **Unknowns:** The precise pre-existing tensile strength of the weathered shingle substrate before the 2026-07-15 event.

---

### TEMPLATE 11: MAINTENANCE
*   **System Focus:** Filter changes, gutter cleaning, mechanical servicing schedules, wear tracking.
*   **Required Ingestion Nodes:** Historic maintenance logs, mechanical runtime files, physical wear logs.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Your gutters are completely blocked with leaves and need to be cleared.
    *   **Supporting Evidence:** Photos from our roof inspection showing leaves and pine needles filling the gutter channels on the east side.
    *   **Confidence:** High (95%). Leaf blockage is clearly visible in the provided photos.
    *   **Why this Matters:** Blocked gutters cannot drain rainwater. Water will overflow the edges, running down your siding and soaking the soil around your foundation, which can cause basement leaks and foundation cracks.
    *   **Recommended Next Steps:** Scoop out the leaves and pine needles from the east gutters and flush the downspouts with water.
    *   **Related Systems:** Basement grading, siding paint wear.
    *   **Assumptions:** The gutters have no structural damage and only require clearing of debris.
    *   **Unknowns:** We do not know if there is a block inside the underground pipes connected to the downspouts.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Restricted gutter channel capacity due to organic debris accumulation in east eave run.
    *   **Supporting Evidence:** Report `ins_891` and photos showing 95% volumetric fill of gutter troughs with leaves and pine needles.
    *   **Confidence:** 95% based on visual inspection.
    *   **Why this Matters:** Blocked gutters lead to water spillover, which washes away landscaping, saturates the foundation clay soil, and causes wood rot in the fascia boards.
    *   **Recommended Next Steps:** Clear organic debris, flush downspouts, inspect fascia board behind gutters for rot, and install mesh gutter guards.
    *   **Related Systems:** Fascia wrapping, downspout splash blocks.
    *   **Assumptions:** Gutter slope remains at the standard 1/16-inch drop per foot.
    *   **Unknowns:** The condition of downspout connection underground drainage lines.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Functional blockage of the roof drainage system on the eastern elevation due to organic particulate build-up, preventing designed stormwater run-off.
    *   **Supporting Evidence:** Aerial high-res capture (`img_9911`) indicating 95% cross-sectional area obstruction of the 5-inch K-style gutter.
    *   **Confidence:** 95% verified by optical capacity analysis.
    *   **Why this Matters:** Spillover during a 10-year storm event (2.5 inches/hour) exceeds the soil absorption rate, raising pore-water pressure at the foundation footprint. Weight of saturated debris (est. 12 lbs/linear foot) exceeds gutter bracket shear design loads.
    *   **Recommended Next Steps:** Clear debris to restore standard 12 GPM flow capacity and verify fastener spacing complies with ICC structural load recommendations.
    *   **Related Systems:** Structural fascia joists, perimeter foundation grading.
    *   **Assumptions:** Gutters are standard aluminum K-style hung with spike-and-ferrule hangers.
    *   **Unknowns:** Volume of debris trapped inside the subterranean drainage pipes.

---

### TEMPLATE 12: PROJECT OPPORTUNITIES
*   **System Focus:** Grouping repairs into high-value projects, solar+roof combos, insulation upgrades.
*   **Required Ingestion Nodes:** Financial cost estimators, carbon footprint reduction calculators, deferred maintenance ledgers.

#### Populated Multi-Level Example:
*   **Level 1 (Homeowner):**
    *   **Conclusion:** Combining your upcoming roof repair with a solar panel installation will save you money and protect your home.
    *   **Supporting Evidence:** Your roof shingles need replacement in 3 years, and your southern exposure receives over 6 hours of direct sunlight daily.
    *   **Confidence:** High (90%). Calculations are based on your roof age and solar mapping data.
    *   **Why this Matters:** Installing solar panels on an old roof is a mistake, because you'll have to pay extra to remove and reinstall the panels when the roof needs replacement. Doing both together saves you thousands in labor and qualifies you for green tax credits.
    *   **Recommended Next Steps:** Request a combined proposal for a new roof with integrated solar panels.
    *   **Related Systems:** Household electrical panel, roof structural shingles.
    *   **Assumptions:** Your electric bills average over $150 per month, making solar a financially viable choice.
    *   **Unknowns:** We do not know if your main electrical breaker box will need an upgrade to handle solar power without a physical inspection.
*   **Level 2 (Contractor):**
    *   **Conclusion:** Project opportunity identified: Coordinated South-Slope Shingle Replacement and 6.2 kW Photovoltaic (PV) Array installation.
    *   **Supporting Evidence:** South-slope roof age is 18 years (decay model shows replacement required within 36 months). Solar irradiance simulation indicates 1,850 kWh/sq.m annual exposure.
    *   **Confidence:** 90% based on composite analysis of roof age and geocoded solar exposure maps.
    *   **Why this Matters:** Combining projects avoids the $3,500 labor surcharge for removing and reinstalling solar racks during a future roof tear-off. It also minimizes staging and permitting overhead.
    *   **Recommended Next Steps:** Issue a unified estimate for roof strip-down to decking, installation of Class-A shingles, and immediate racking system bolt-down.
    *   **Related Systems:** Main service meter, roof underlayment barrier.
    *   **Assumptions:** Current roof structure has adequate structural capacity to handle PV dead loads (+3 lbs/sq.ft).
    *   **Unknowns:** Local utility net-metering connection approval timelines and rates.
*   **Level 3 (Engineering):**
    *   **Conclusion:** Integrated project opportunity: South-slope structural roofing replacement synchronized with 6.2 kW grid-tied Photovoltaic System deployment.
    *   **Supporting Evidence:** Projected roof degradation curves predict bitumen embrittlement limit reached within 30 months. Solar insolation modeling calculates a solar savings index of 0.88.
    *   **Confidence:** 90% validated by financial modeling and structural dead-load simulations.
    *   **Why this Matters:** Executing roof replacement and racking installation concurrently eliminates redundant construction overhead. It allows the solar flashing anchors to be integrated directly with the new underlayment, minimizing mechanical penetrations and water bypass risks.
    *   **Recommended Next Steps:** Perform a structural load calculation of the rafters to verify compliance with ASCE 7 dead-load allowances before solar racking layout.
    *   **Related Systems:** Electric service panel backfeeds, roof structural framing.
    *   **Assumptions:** The property is eligible for the 30% Federal Investment Tax Credit (ITC); local energy rates remain stable at $0.16/kWh.
    *   **Unknowns:** The internal wiring condition of the electrical service panel bus bars.
