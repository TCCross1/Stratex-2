.PHONY: field-test-publish-dry field-test-publish

# Field-test golden path: pipeline seal (+ ATC) and governed Passport publish demo.
# See docs/FIELD_TEST_GOVERNED_PUBLISH.md

field-test-publish-dry:
	python3 -m backend.nextgen.field_test_governed_publish_demo --dry-run

field-test-publish:
	python3 -m backend.nextgen.field_test_governed_publish_demo
