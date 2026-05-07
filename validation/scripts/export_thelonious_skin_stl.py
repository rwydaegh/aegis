"""Export the thelonious Skin entity as an STL. Run inside Sim4Life.

The IT'IS Virtual Population license blocks programmatic access to vertex
data on protected entities (skin.Points raises, ModelToGridFilter's grid
raises on GetPoint, Clone / PlanarCut / RepairTriangleMesh / .sab round-trip
all preserve the flag, ExportProtectedModel is the inverse — it creates
protected bundles).

The sanctioned export path is XCoreModeling.CreateExporterFromFile(path),
which returns a format-specific ExporterBase whose .Export(entities, path)
is allowed to read protected geometry internally. STL is in the registry
(AvailableExporters), so we just route through that.

The top-level XCoreModeling.Export does NOT know STL; it only handles a
subset (.sab etc), which is why model.Export raised "File format not
supported" earlier.
"""

import s4l_v1.model as model
import XCoreModeling

OUTPUT_PATH = r"C:\Users\rwydaegh\Downloads\thelonious_skin.stl"
ENTITY_NAME = "Skin"

skin = model.AllEntities()[ENTITY_NAME]

exporter = XCoreModeling.CreateExporterFromFile(OUTPUT_PATH)
exporter.Export([skin], OUTPUT_PATH)

print(f"wrote {OUTPUT_PATH}")
