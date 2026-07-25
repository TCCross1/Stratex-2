# PROPERTY DNA API SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 011 · OPERATION PROPERTY DNA
**Status:** API APPROVED  
**Scope:** Hardened NextGen v1 endpoints for reading and updating Property DNA.

---

## 1. System Endpoints Overview

The Property DNA Engine™ exposes a dual REST interface under `/nextgen/v1` for safe, high-speed ecosystem reads and controlled, peer-reviewed writes.

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| **GET** | `/nextgen/v1/properties/{property_id}/dna` | Reader / Contractor / GM / CEO | Retrieves the structured DNA profile and its full historical attribution. |
| **POST** | `/nextgen/v1/properties/{property_id}/dna/update` | Admin / GM / CEO | Performs a version-safe write to a single DNA node, appending to history. |

---

## 2. API Endpoints Specification

### A. GET Property DNA
**Path:** `/nextgen/v1/properties/{property_id}/dna`  
**Description:** Retrieves the fully compiled Property DNA profile, including history, confidence levels, and provenance links.

#### Request Headers
```http
Authorization: ******
X-Tenant-ID: <tenant_id>
```

#### Successful Response (200 OK)
```json
{
  "property_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
  "dna": {
    "canonical_id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A",
    "property_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
    "tenant_id": "tenant_north_east_01",
    "version": 4,
    "created_at": "2026-07-21T03:12:00Z",
    "updated_at": "2026-07-21T03:15:30Z",
    "identity": {
      "property_name": {
        "current_value": "Sandy Shores Cottage",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Sandy Shores Cottage",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "address": {
        "current_value": "123 Ocean Drive, Portland ME 04101",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "123 Ocean Drive, Portland ME 04101",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "build_year": {
        "current_value": 1994,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 1994,
            "source_attribution": "01H2Z4M4E3S9Q8V1T4N6K9B2D",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_ceo_jack",
            "timestamp": "2026-07-21T03:14:00Z"
          }
        ]
      },
      "size": {
        "current_value": 2400,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 2400,
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 98.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "construction_type": {
        "current_value": "Wood Frame / Architectural Shingle",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Wood Frame / Architectural Shingle",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "climate_zone": {
        "current_value": "Zone 5 - Cool / Dry",
        "provenance": "Estimated",
        "history": [
          {
            "version": 1,
            "value": "Zone 5 - Cool / Dry",
            "source_attribution": "01H2Z4N8E2R3W6P2M9G8T1D1S",
            "approval_status": "APPROVED",
            "confidence_score": 90.0,
            "reviewer": "usr_analyst_agent",
            "timestamp": "2026-07-21T03:13:10Z"
          }
        ]
      }
    },
    "health": {
      "overall_home_health": {
        "current_value": 84.5,
        "provenance": "Estimated",
        "history": [
          {
            "version": 1,
            "value": 84.5,
            "source_attribution": "01H2Z4R9P5A4S8Q3N2M1V9G5K",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      },
      "structural": {
        "current_value": "Foundation: Excellent / Load-bearing wall settlement nominal (APPROVED)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Foundation: Excellent / Load-bearing wall settlement nominal (APPROVED)",
            "source_attribution": "01H2Z4P2M9T5Q7F8N1B6A2D1V",
            "approval_status": "APPROVED",
            "confidence_score": 98.0,
            "reviewer": "usr_inspector_bill",
            "timestamp": "2026-07-21T03:14:15Z"
          }
        ]
      },
      "roofing": {
        "current_value": "Asphalt Shingle (Architectural)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Asphalt Shingle (Architectural)",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "exterior": {
        "current_value": "Vinyl Siding",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Vinyl Siding",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "moisture": {
        "current_value": "Sump Pump active / relative humidity in crawlspace stable (APPROVED)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Sump Pump active / relative humidity in crawlspace stable (APPROVED)",
            "source_attribution": "01H2Z4S8N1F4W5Q2G8T3P1B9Y",
            "approval_status": "APPROVED",
            "confidence_score": 94.0,
            "reviewer": "usr_mdu_sensor_array",
            "timestamp": "2026-07-21T03:14:50Z"
          }
        ]
      },
      "air": {
        "current_value": "Mechanical recovery ventilator operational / IAQ indices healthy (APPROVED)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Mechanical recovery ventilator operational / IAQ indices healthy (APPROVED)",
            "source_attribution": "01H2Z4T9E2W3Q4G5S6T7N8M9P",
            "approval_status": "APPROVED",
            "confidence_score": 96.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:15:00Z"
          }
        ]
      },
      "energy": {
        "current_value": "Standard Residential (HE RS)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Standard Residential (HE RS)",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "safety": {
        "current_value": "Interconnected smoke detectors present / Fire extinguishers fully charged (APPROVED)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Interconnected smoke detectors present / Fire extinguishers fully charged (APPROVED)",
            "source_attribution": "01H2Z4V2M1S3D4N5Q6P7W8A9R",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_inspector_bill",
            "timestamp": "2026-07-21T03:13:45Z"
          }
        ]
      },
      "site": {
        "current_value": "Positive grading established around north-west perimeter wall (APPROVED)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Positive grading established around north-west perimeter wall (APPROVED)",
            "source_attribution": "01H2Z4W8N3V4D5E6Q7T8G9P1S",
            "approval_status": "APPROVED",
            "confidence_score": 97.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      }
    },
    "awe": {
      "air_index": {
        "current_value": 85,
        "provenance": "Estimated",
        "history": [
          {
            "version": 1,
            "value": 85,
            "source_attribution": "01H2Z4X3N2M4G5Q7P8W9S1D2Y",
            "approval_status": "APPROVED",
            "confidence_score": 92.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:14:00Z"
          }
        ]
      },
      "water_index": {
        "current_value": 90,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 90,
            "source_attribution": "01H2Z4Y4N5E3D2S6W7P8N9M1A",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      },
      "energy_index": {
        "current_value": 78,
        "provenance": "Estimated",
        "history": [
          {
            "version": 1,
            "value": 78,
            "source_attribution": "01H2Z4Z5N6Q3W4D7S8P9G1A2B",
            "approval_status": "APPROVED",
            "confidence_score": 90.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:13:30Z"
          }
        ]
      },
      "overall_we_index": {
        "current_value": "Resilient Envelope (Water Shield active)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Resilient Envelope (Water Shield active)",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      }
    },
    "risk": {
      "current_risk_level": {
        "current_value": "Low",
        "provenance": "Projected",
        "history": [
          {
            "version": 1,
            "value": "Low",
            "source_attribution": "01H2Z50N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 85.0,
            "reviewer": "usr_risk_modeler",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      },
      "five_year_risk_projection": {
        "current_value": "Medium (Factor of micro-climatic humidity escalation)",
        "provenance": "Projected",
        "history": [
          {
            "version": 1,
            "value": "Medium (Factor of micro-climatic humidity escalation)",
            "source_attribution": "01H2Z51N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 80.0,
            "reviewer": "usr_risk_modeler",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      },
      "deferred_maintenance_exposure": {
        "current_value": 0,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 0,
            "source_attribution": "01H2Z4P2M9T5Q7F8N1B6A2D1V",
            "approval_status": "APPROVED",
            "confidence_score": 98.0,
            "reviewer": "usr_inspector_bill",
            "timestamp": "2026-07-21T03:14:15Z"
          }
        ]
      },
      "weather_exposure": {
        "current_value": "Coastal Wind Zone - Elevated Shingle Hold Rating",
        "provenance": "Estimated",
        "history": [
          {
            "version": 1,
            "value": "Coastal Wind Zone - Elevated Shingle Hold Rating",
            "source_attribution": "01H2Z52N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 90.0,
            "reviewer": "usr_risk_modeler",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      },
      "moisture_exposure": {
        "current_value": "Flood Zone X - Low Risk",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Flood Zone X - Low Risk",
            "source_attribution": "01H2Z53N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 99.0,
            "reviewer": "usr_risk_modeler",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      },
      "insurance_exposure": {
        "current_value": "Highly Insurable / Preferred Risk Band",
        "provenance": "Projected",
        "history": [
          {
            "version": 1,
            "value": "Highly Insurable / Preferred Risk Band",
            "source_attribution": "01H2Z54N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 88.0,
            "reviewer": "usr_risk_modeler",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      }
    },
    "lifecycle": {
      "roof_age": {
        "current_value": 2,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 2,
            "source_attribution": "01H2Z55N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      },
      "hvac_age": {
        "current_value": "Forced Air Heat Pump (14 SEER)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Forced Air Heat Pump (14 SEER)",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "windows": {
        "current_value": "Double-Hung Vinyl",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Double-Hung Vinyl",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "exterior": {
        "current_value": "Vinyl Siding",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Vinyl Siding",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "foundation": {
        "current_value": "Poured Concrete Crawlspace",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Poured Concrete Crawlspace",
            "source_attribution": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_system_seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          }
        ]
      },
      "solar": {
        "current_value": "None Installed",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "None Installed",
            "source_attribution": "01H2Z4P2M9T5Q7F8N1B6A2D1V",
            "approval_status": "APPROVED",
            "confidence_score": 98.0,
            "reviewer": "usr_inspector_bill",
            "timestamp": "2026-07-21T03:14:15Z"
          }
        ]
      },
      "major_components": {
        "current_value": "Water Heater: Gas 50 Gal (5 Years Old)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Water Heater: Gas 50 Gal (5 Years Old)",
            "source_attribution": "01H2Z4P2M9T5Q7F8N1B6A2D1V",
            "approval_status": "APPROVED",
            "confidence_score": 98.0,
            "reviewer": "usr_inspector_bill",
            "timestamp": "2026-07-21T03:14:15Z"
          }
        ]
      },
      "remaining_service_life": {
        "current_value": 23,
        "provenance": "Projected",
        "history": [
          {
            "version": 1,
            "value": 23,
            "source_attribution": "01H2Z56N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 85.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      }
    },
    "financial": {
      "estimated_deferred_maintenance": {
        "current_value": 0,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 0,
            "source_attribution": "01H2Z4P2M9T5Q7F8N1B6A2D1V",
            "approval_status": "APPROVED",
            "confidence_score": 98.0,
            "reviewer": "usr_inspector_bill",
            "timestamp": "2026-07-21T03:14:15Z"
          }
        ]
      },
      "estimated_annual_energy_waste": {
        "current_value": 145.0,
        "provenance": "Estimated",
        "history": [
          {
            "version": 1,
            "value": 145.0,
            "source_attribution": "01H2Z4Z5N6Q3W4D7S8P9G1A2B",
            "approval_status": "APPROVED",
            "confidence_score": 90.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:13:30Z"
          }
        ]
      },
      "completed_improvements": {
        "current_value": "Completed roof deck re-nailing and high-wind shingle install (APPROVED)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Completed roof deck re-nailing and high-wind shingle install (APPROVED)",
            "source_attribution": "01H2Z57N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      },
      "future_investment_opportunities": {
        "current_value": "Heat Pump replacement recommended / Solar offset potential high",
        "provenance": "Projected",
        "history": [
          {
            "version": 1,
            "value": "Heat Pump replacement recommended / Solar offset potential high",
            "source_attribution": "01H2Z58N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 85.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      }
    },
    "history": {
      "inspection_count": {
        "current_value": 2,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 2,
            "source_attribution": "01H2Z59N2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      },
      "mission_count": {
        "current_value": 3,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 3,
            "source_attribution": "01H2Z5AN2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_analytical_engine",
            "timestamp": "2026-07-21T03:15:30Z"
          }
        ]
      },
      "major_events": {
        "current_value": "Hurricane Beryl Survival / No critical envelope degradation recorded",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Hurricane Beryl Survival / No critical envelope degradation recorded",
            "source_attribution": "01H2Z5BN2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 98.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      },
      "timeline_summary": {
        "current_value": "Completed Roof Install -> Passed Inspection -> Weather Event Resiliency Confirmed",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Completed Roof Install -> Passed Inspection -> Weather Event Resiliency Confirmed",
            "source_attribution": "01H2Z5CN2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 99.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      },
      "verified_contractor_work": {
        "current_value": "Coastal Roofing Inc - Complete replacement under contract #C410 (APPROVED)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Coastal Roofing Inc - Complete replacement under contract #C410 (APPROVED)",
            "source_attribution": "01H2Z5DN2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      },
      "warranty_status": {
        "current_value": "Active 10-Year Workmanship Warranty (ID: W99104)",
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": "Active 10-Year Workmanship Warranty (ID: W99104)",
            "source_attribution": "01H2Z5EN2M3S4D5G6Q7W8E9R1T",
            "approval_status": "APPROVED",
            "confidence_score": 100.0,
            "reviewer": "usr_gm_sarah",
            "timestamp": "2026-07-21T03:15:10Z"
          }
        ]
      }
    }
  }
}
```

---

### B. POST Update Property DNA Node
**Path:** `/nextgen/v1/properties/{property_id}/dna/update`  
**Description:** Appends a peer-reviewed value to a single node inside the Property DNA record. Requires elevated execution credentials (Admin, GM, or CEO) and automatically propagates changes down to the Passport.

#### Request Headers
```http
Authorization: ******
X-Tenant-ID: <tenant_id>
Content-Type: application/json
```

#### Request Payload Body
```json
{
  "field_name": "identity.build_year",
  "value": 1994,
  "source_attribution": "01H2Z4M4E3S9Q8V1T4N6K9B2D",
  "confidence_score": 95.0
}
```

#### Successful Response (200 OK)
```json
{
  "success": true,
  "dna": {
    "canonical_id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A",
    "property_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
    "tenant_id": "tenant_north_east_01",
    "version": 5,
    "updated_at": "2026-07-21T03:16:00Z",
    "identity": {
      "build_year": {
        "current_value": 1994,
        "provenance": "Verified",
        "history": [
          {
            "version": 1,
            "value": 1993,
            "source_attribution": "Baseline Seeder",
            "approval_status": "APPROVED",
            "confidence_score": 90.0,
            "reviewer": "System Seeder",
            "timestamp": "2026-07-21T03:12:00Z"
          },
          {
            "version": 2,
            "value": 1994,
            "source_attribution": "01H2Z4M4E3S9Q8V1T4N6K9B2D",
            "approval_status": "APPROVED",
            "confidence_score": 95.0,
            "reviewer": "usr_ceo_jack",
            "timestamp": "2026-07-21T03:16:00Z"
          }
        ]
      }
    }
  }
}
```

---

## 3. Detailed Error Handling

If an update sequence fails, the endpoint rolls back any partial transactions and issues standard error structures:

*   **400 Bad Request:** Occurs when the `field_name` does not exist in the DNA schema, or is missing required validation attributes.
    ```json
    {
      "detail": "Invalid DNA field 'identity.unsupported_field'"
    }
    ```
*   **403 Forbidden:** Occurs when the authenticated user’s active role does not meet write authorization criteria (Reader/Contractor attempt).
    ```json
    {
      "detail": "Only Admin, GM, or CEO may update Property DNA records."
    }
    ```
*   **404 Not Found:** Issued if the target property does not exist within the specified tenant boundary.
    ```json
    {
      "detail": "Property not found"
    }
    ```
