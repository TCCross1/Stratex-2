import hashlib
import importlib.util
import pathlib


MODULE_PATH = pathlib.Path("/app/backend/tests/test_nextgen_wave2a.py")
spec = importlib.util.spec_from_file_location("wave2a", MODULE_PATH)
wave2a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wave2a)


def sha_for_suffix(suffix: str, seed: int = 1) -> str:
    old_suffix = wave2a._TEST_SUFFIX
    try:
        wave2a._TEST_SUFFIX = suffix
        return hashlib.sha256(wave2a._png_bytes(seed=seed)).hexdigest()
    finally:
        wave2a._TEST_SUFFIX = old_suffix


base = "1700000000123"
delta = str(int(base) + 65536)

same_run_a = wave2a._png_bytes(seed=1)
same_run_b = wave2a._png_bytes(seed=1)
assert same_run_a == same_run_b, "same-run _png_bytes(seed=1) is not deterministic"

base_sha = sha_for_suffix(base, seed=1)
delta_sha = sha_for_suffix(delta, seed=1)
assert base_sha != delta_sha, "65,536 ms suffix delta still collides"

print("same_run_identical=True")
print(f"base_sha={base_sha}")
print(f"delta_sha={delta_sha}")
print("collision_at_65536ms=False")