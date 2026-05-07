"""Inspect Options children + try ExportModel via the active model."""

import glob
import os
import tempfile
import time

import s4l_v1.document as document
import s4l_v1.model as model
import XCoreModeling

skin = model.AllEntities()["Skin"]
OUT = r"C:\Users\rwydaegh\Downloads\thelonious_skin.stl"


def check(label):
    if os.path.exists(OUT):
        size = os.path.getsize(OUT)
        print(f"  [{label}] file EXISTS, size={size}")
        return True
    print(f"  [{label}] file NOT created")
    return False


def make_sphere():
    """Make a fresh non-protected entity to compare against."""
    try:
        return XCoreModeling.CreateSolidSphere(XCoreModeling.Vec3(0, 0, 0), 50.0)
    except Exception:
        try:
            return model.CreateSolidSphere(model.Vec3(0, 0, 0), 50.0)
        except Exception as e:
            print(f"  could not create sphere: {e}")
            return None


# ============================================================
# 1. Inspect Options children
# ============================================================
print("=" * 70)
print("Inspect exporter.Options children")
print("=" * 70)
exp = XCoreModeling.CreateExporterFromFile(OUT)
opts = exp.Options
for i, child in enumerate(opts.Children):
    print(f"\n  Child[{i}]: type={type(child).__module__}.{type(child).__name__}")
    for a in ("Name", "Description", "Value", "ValueDescription", "Values", "ValueDescriptions"):
        try:
            v = getattr(child, a)
            print(f"    {a} = {v!r}")
        except Exception as e:
            print(f"    {a} -> {e}")

# ============================================================
# 2. Try to find an active model object
# ============================================================
print("\n" + "=" * 70)
print("Look for an 'active model' handle to feed ExportModel")
print("=" * 70)
candidates = []
for src_name, src in [("XCoreModeling", XCoreModeling), ("model", model), ("document", document)]:
    for a in dir(src):
        if "model" in a.lower() and not a.startswith("_"):
            candidates.append((src_name, a))
print(f"  candidates: {candidates}")

active_model = None
for src_name, attr_name in candidates:
    src = {"XCoreModeling": XCoreModeling, "model": model, "document": document}[src_name]
    try:
        v = getattr(src, attr_name)
        if callable(v):
            try:
                v = v()
            except Exception:
                continue
        # Heuristic: take the first thing whose class name contains "Model"
        if "Model" in type(v).__name__ and not isinstance(v, type):
            print(f"  candidate hit: {src_name}.{attr_name} -> {type(v).__module__}.{type(v).__name__}")
            if active_model is None:
                active_model = v
    except Exception:
        pass

# ============================================================
# 3. Try ExportModel with the active model handle (sphere first)
# ============================================================
print("\n" + "=" * 70)
print("Try ExportModel on a fresh sphere via active_model")
print("=" * 70)
sphere = make_sphere()
if sphere is not None and active_model is not None:
    if os.path.exists(OUT):
        os.remove(OUT)
    try:
        exp2 = XCoreModeling.CreateExporterFromFile(OUT)
        exp2.ExportModel(active_model, OUT)
        check("sphere via ExportModel")
    except Exception as e:
        print(f"  ExportModel(active_model, OUT) failed: {type(e).__name__}: {e}")
    sphere.Delete()
else:
    print(f"  skipped (sphere={sphere}, active_model={active_model})")

# ============================================================
# 4. Search Documents/Downloads/temp for any newly-written STL
# ============================================================
print("\n" + "=" * 70)
print("Final attempt: Export([skin], OUT) and search for output anywhere")
print("=" * 70)

# Snapshot existing STLs in likely dirs
search_dirs = [
    r"C:\Users\rwydaegh\Downloads",
    r"C:\Users\rwydaegh\Documents",
    tempfile.gettempdir(),
    os.getcwd(),
]
before = set()
for d in search_dirs:
    if os.path.isdir(d):
        before.update(glob.glob(os.path.join(d, "**", "*.stl"), recursive=True))
print(f"  pre-call: {len(before)} stl files in search dirs")

t0 = time.time()
exp3 = XCoreModeling.CreateExporterFromFile(OUT)
exp3.Export([skin], OUT)
print(f"  Export([skin], OUT) returned after {time.time() - t0:.2f}s")

after = set()
for d in search_dirs:
    if os.path.isdir(d):
        after.update(glob.glob(os.path.join(d, "**", "*.stl"), recursive=True))
new_files = after - before
print(f"  post-call new stl files: {sorted(new_files)}")

print("\nDone.")
