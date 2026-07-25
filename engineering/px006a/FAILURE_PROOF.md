# PX-006A Failure Proof

Results:

```
{
  "cases": {
    "wrong_digest": {
      "ok": true,
      "error": "digest mismatch vs registry: 'opendronemap/odm@sha256:0000000000000000000000000000000000000000000000000000000000000000' != 'opendronemap/odm@sha256:56be7b87a5ef3abfc0bb2afe88df839862fd18c41d26ca13672bf79cd2d59dd1'"
    },
    "latest_tag": {
      "ok": true,
      "error": "floating tag latest rejected for execution"
    },
    "mutable_tag": {
      "ok": true,
      "error": "mutable tag without digest rejected"
    },
    "input_path_escape": {
      "ok": true,
      "status": "FAILED",
      "promoted": false,
      "classification": "PATH_ESCAPE"
    },
    "output_path_escape": {
      "ok": true,
      "status": "FAILED",
      "promoted": false,
      "classification": "PATH_ESCAPE"
    },
    "low_disk": {
      "ok": true,
      "promoted": false,
      "status": "FAILED"
    },
    "timeout": {
      "ok": true,
      "promoted": false,
      "status": "FAILED"
    },
    "license_blocked_dji": {
      "ok": true,
      "promoted": false,
      "status": "LICENSE_BLOCKED",
      "failure_classification": "LICENSE_REVIEW_REQUIRED"
    }
  },
  "physical_validation": "NOT_PERFORMED",
  "partial_output_promotion_protection": true
}
```

All controlled negative cases recorded `promoted=false`.
Partial-output promotion protection: True
