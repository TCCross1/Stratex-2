# Property Intelligence Report Schema

**Version:** 1.0.0  
**Matches:** Visual structure of the Comprehensive Property Report mockups  
**Source of Truth:** Passport projections only

## Report Structure (Fixed Order)

01. Executive Summary  
    - Property overview, scores (Property / Roof / Energy / Moisture / AWE Index)  
    - Critical / High / Medium / Low finding counts  
    - Digital Twin completeness  
    - Truth classifications for every score

02. 3D Digital Twin Overview  
03. CAD/BIM – Overall Model  
04. CAD/BIM – Structural Layers  
05. CAD/BIM – Thermal Layer  
06. Framing Layer (candidate / projected when not verified)  
07. Sheathing Layer  
08. Decking Layer  
09. Roofing Layer  
10. System Health & Thermal Overview  

11. Window Schedule  
12. Door Schedule  
13. Energy Efficiency Report  
14. Ventilation Report  
15. Materials List  
16. Labor Report  
17. Found Damages  
18. Maintenance Priority List  

## Deliverables Block
- Interactive 3D Digital Twin
- CAD/BIM files (when geometry is verified)
- High-resolution imagery package
- Detailed Inspection Report (PDF)
- Materials & Labor Estimate
- Maintenance Roadmap
- Property Passport entry (hash-chained)

## Rules
- Every numeric value and finding must carry a truth classification:  
  VERIFIED | ESTIMATED | PROJECTED | UNKNOWN | WITHHELD
- Subsurface layers (framing, decking, sheathing) are never claimed as VERIFIED from exterior drone imagery alone.
- Habitat renders this schema from Passport projections only.
- Core generates the report after successful governed publication.

## Implementation Target
- Backend report composer in Core that consumes sealed package + Passport state
- Habitat consumes the resulting projection and renders the same structure
