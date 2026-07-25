"""Corpus suitability audit for PX-006B."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from nextgen.dataset_lab.common import artifact_dir, get_registry_entry, load_registry, read_json
from nextgen.dataset_lab.inventory import inventory_dataset
from nextgen.dataset_lab.license_check import license_check

from .common import load_yaml, px006b_dir, write_json
from .constants import SUITABILITY_CLASSES


# Curated suitability assessments from ODM documentation, DroneDB metadata,
# and local inventory/reconstruction receipts. No fabricated dimensions.
EXISTING_CORPUS_PROFILES: Dict[str, Dict[str, Any]] = {
    "MYGLA": {
        "suitability_classification": "CAPTURE_QUALITY_ONLY",
        "visible_buildings": True,
        "residential_structures": False,
        "detached_structures": True,
        "roof_visibility": "partial",
        "roof_complexity": "low",
        "wall_visibility": "limited",
        "obstruction_level": "moderate",
        "vegetation_level": "moderate",
        "nadir_coverage": "good",
        "oblique_coverage": "limited",
        "roof_plane_benchmark": False,
        "wall_plane_benchmark": False,
        "opening_detection": False,
        "notes": [
            "Starter ODM corpus (~29 images); useful for pipeline smoke only.",
            "Not a residential roof benchmark corpus.",
        ],
    },
    "AUKERMAN": {
        "suitability_classification": "USEFUL_SMALL_BUILDING",
        "visible_buildings": True,
        "residential_structures": False,
        "detached_structures": True,
        "roof_visibility": "good",
        "roof_complexity": "moderate",
        "wall_visibility": "partial",
        "obstruction_level": "low",
        "vegetation_level": "low",
        "nadir_coverage": "good",
        "oblique_coverage": "partial",
        "roof_plane_benchmark": True,
        "wall_plane_benchmark": False,
        "opening_detection": False,
        "notes": [
            "Ohio dairy farm with barns and agricultural structures.",
            "Pitched roofs present; not detached residential homes.",
        ],
    },
    "BELLUS": {
        "suitability_classification": "USEFUL_SMALL_BUILDING",
        "visible_buildings": True,
        "residential_structures": False,
        "detached_structures": True,
        "roof_visibility": "good",
        "roof_complexity": "moderate",
        "wall_visibility": "good",
        "obstruction_level": "moderate",
        "vegetation_level": "low",
        "nadir_coverage": "good",
        "oblique_coverage": "partial",
        "roof_plane_benchmark": True,
        "wall_plane_benchmark": True,
        "opening_detection": False,
        "notes": [
            "Construction-site structures with GCP file.",
            "Strong GCP/control reference for development benchmarking.",
        ],
    },
    "CALITERRA": {
        "suitability_classification": "HIGH_VALUE_RESIDENTIAL",
        "visible_buildings": True,
        "residential_structures": True,
        "detached_structures": True,
        "roof_visibility": "good",
        "roof_complexity": "moderate",
        "wall_visibility": "partial",
        "obstruction_level": "moderate",
        "vegetation_level": "moderate",
        "nadir_coverage": "good",
        "oblique_coverage": "partial",
        "roof_plane_benchmark": True,
        "wall_plane_benchmark": False,
        "opening_detection": False,
        "notes": [
            "Chile vineyard/residential estate structures.",
            "Best existing corpus candidate for residential roof-plane work.",
        ],
    },
    "COPR": {
        "suitability_classification": "USEFUL_SMALL_BUILDING",
        "visible_buildings": True,
        "residential_structures": False,
        "detached_structures": True,
        "roof_visibility": "good",
        "roof_complexity": "moderate",
        "wall_visibility": "partial",
        "obstruction_level": "low",
        "vegetation_level": "low",
        "nadir_coverage": "good",
        "oblique_coverage": "partial",
        "roof_plane_benchmark": True,
        "wall_plane_benchmark": False,
        "opening_detection": False,
        "notes": [
            "ODM COPR corpus with explicit CC-BY-SA-4.0 license.txt and GCP control files.",
            "Share-alike and attribution required; never treat as CC0.",
            "Acquired in PX-006B for GCP-aware roof benchmark development.",
        ],
    },
    "GARFIELD": {
        "suitability_classification": "GENERAL_GEOMETRY_ONLY",
        "visible_buildings": True,
        "residential_structures": False,
        "detached_structures": True,
        "roof_visibility": "partial",
        "roof_complexity": "high",
        "wall_visibility": "partial",
        "obstruction_level": "high",
        "vegetation_level": "moderate",
        "nadir_coverage": "good",
        "oblique_coverage": "partial",
        "roof_plane_benchmark": False,
        "wall_plane_benchmark": False,
        "opening_detection": False,
        "notes": [
            "Minneapolis-St Paul urban/industrial mix; neighbor contamination risk.",
        ],
    },
    "DJI_TERRA_SAMPLE": {
        "suitability_classification": "LICENSE_RESTRICTED_INVENTORY_ONLY",
        "visible_buildings": True,
        "residential_structures": "unknown",
        "detached_structures": "unknown",
        "roof_visibility": "unknown",
        "roof_complexity": "unknown",
        "wall_visibility": "unknown",
        "obstruction_level": "unknown",
        "vegetation_level": "unknown",
        "nadir_coverage": "good",
        "oblique_coverage": "unknown",
        "roof_plane_benchmark": False,
        "wall_plane_benchmark": False,
        "opening_detection": False,
        "notes": [
            "License redistribution prohibited; inventory/metadata only.",
            "Reconstruction blocked by license gate.",
        ],
    },
}


def _reconstruction_summary(dataset_id: str) -> Dict[str, Any]:
    path = artifact_dir(dataset_id) / "reconstruction_latest.json"
    if not path.is_file():
        return {"executed": False, "status": "NOT_ATTEMPTED"}
    receipt = read_json(path)
    outputs = receipt.get("outputs_discovered") or {}
    return {
        "executed": receipt.get("status") == "SUCCESS" and receipt.get("promoted") is True,
        "status": receipt.get("status"),
        "profile": receipt.get("profile"),
        "promoted": receipt.get("promoted"),
        "odm_digest": (receipt.get("environment") or {}).get("container_digest"),
        "output_classes": {
            key: bool((outputs.get(key) or {}).get("present"))
            for key in (
                "orthophoto",
                "dsm",
                "dtm",
                "point_cloud",
                "mesh",
                "textured_model",
                "report",
                "cameras",
            )
        },
        "reconstruction_version": receipt.get("output_dir"),
    }


def audit_existing_dataset(dataset_id: str) -> Dict[str, Any]:
    profile = EXISTING_CORPUS_PROFILES.get(dataset_id.upper())
    if not profile:
        raise KeyError(f"unknown dataset for suitability audit: {dataset_id}")
    registry = get_registry_entry(dataset_id)
    lic = license_check(dataset_id)
    inv = inventory_dataset(dataset_id)
    recon = _reconstruction_summary(dataset_id)
    suitability = profile["suitability_classification"]
    if suitability not in SUITABILITY_CLASSES:
        raise ValueError(f"invalid suitability class: {suitability}")
    return {
        "dataset_id": dataset_id.upper(),
        "display_name": registry.get("display_name"),
        "license_status": lic.get("license_status"),
        "license_name": lic.get("license_name"),
        "privacy_classification": registry.get("privacy_classification"),
        "suitability_classification": suitability,
        "visible_buildings_present": profile["visible_buildings"],
        "residential_structures_present": profile["residential_structures"],
        "detached_structures_present": profile["detached_structures"],
        "roof_visibility": profile["roof_visibility"],
        "roof_complexity": profile["roof_complexity"],
        "wall_visibility": profile["wall_visibility"],
        "obstruction_level": profile["obstruction_level"],
        "vegetation_level": profile["vegetation_level"],
        "image_overlap": inv["inventory"].get("overlap_estimate", "unknown"),
        "nadir_coverage": profile["nadir_coverage"],
        "oblique_coverage": profile["oblique_coverage"],
        "point_cloud_density": "unknown_without_local_reconstruction",
        "orthophoto_usefulness": "high" if recon.get("executed") else "pending_reconstruction",
        "dsm_availability": recon.get("output_classes", {}).get("dsm", False),
        "mesh_availability": recon.get("output_classes", {}).get("mesh", False),
        "known_dimensions": False,
        "gcp_availability": bool(inv["inventory"].get("gcp_present")),
        "suitability_roof_plane_benchmarking": profile["roof_plane_benchmark"],
        "suitability_wall_plane_benchmarking": profile["wall_plane_benchmark"],
        "suitability_opening_detection": profile["opening_detection"],
        "license_suitability": lic.get("license_status"),
        "privacy_limitations": [registry.get("privacy_classification", "DEVELOPMENT_EXTERNAL_IMAGERY")],
        "inventory_summary": {
            "total_images": inv["inventory"]["total_images"],
            "total_bytes": inv["inventory"]["total_bytes"],
            "gps_status": inv["inventory"]["gps_status"],
        },
        "reconstruction_summary": recon,
        "notes": profile["notes"],
        "physical_validation": "NOT_PERFORMED",
        "authoritative": False,
    }


def audit_existing_corpus() -> Dict[str, Any]:
    reg = load_registry()
    datasets = [str(entry["dataset_id"]).upper() for entry in reg.get("datasets") or []]
    audited = [audit_existing_dataset(dataset_id) for dataset_id in datasets]
    residential = [d for d in audited if d["residential_structures_present"] is True]
    small_building = [
        d
        for d in audited
        if d["suitability_classification"] in {"USEFUL_SMALL_BUILDING", "HIGH_VALUE_RESIDENTIAL"}
    ]
    return {
        "version": "0.1.0",
        "production_readiness": "NOT_READY",
        "physical_validation": "NOT_PERFORMED",
        "datasets": audited,
        "summary": {
            "datasets_reviewed": len(audited),
            "residential_structures_identified": len(residential),
            "small_building_candidates": len(small_building),
            "high_value_residential": [
                d["dataset_id"]
                for d in audited
                if d["suitability_classification"] == "HIGH_VALUE_RESIDENTIAL"
            ],
            "license_blocked": [
                d["dataset_id"]
                for d in audited
                if d["suitability_classification"] == "LICENSE_RESTRICTED_INVENTORY_ONLY"
            ],
        },
    }


def write_corpus_suitability_artifacts() -> Dict[str, Any]:
    payload = audit_existing_corpus()
    out_dir = px006b_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "EXISTING_CORPUS_SUITABILITY.yaml", payload)
    md_lines = [
        "# PX-006B Existing Corpus Suitability",
        "",
        "Development benchmark suitability only. Not physical validation.",
        "",
        f"- Datasets reviewed: {payload['summary']['datasets_reviewed']}",
        f"- Residential structures identified: {payload['summary']['residential_structures_identified']}",
        f"- Small-building candidates: {payload['summary']['small_building_candidates']}",
        "",
    ]
    for item in payload["datasets"]:
        md_lines.extend(
            [
                f"## {item['dataset_id']}",
                "",
                f"- Suitability: `{item['suitability_classification']}`",
                f"- License: `{item['license_status']}` ({item['license_name']})",
                f"- Residential structures: {item['residential_structures_present']}",
                f"- Roof-plane benchmark: {item['suitability_roof_plane_benchmarking']}",
                f"- Reconstruction executed: {item['reconstruction_summary'].get('executed')}",
                "",
            ]
        )
        for note in item.get("notes") or []:
            md_lines.append(f"  - {note}")
        md_lines.append("")
    (out_dir / "EXISTING_CORPUS_SUITABILITY.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload
