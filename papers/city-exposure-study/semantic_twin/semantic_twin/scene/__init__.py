"""The geometry floor: the frames, the mesh, the ground and the cut.

Everything else in the study stands on this. A square has a mesh, the mesh has a
ground, and a pixel, a camera and a triangle have to be able to talk about the
same point in space. That is what lives here.

Seven modules, split by which question they answer.

| Module | Question |
|---|---|
| :mod:`.site_config` | where is this square, and how high is its ground |
| :mod:`.enu` | what are these degrees in local metres |
| :mod:`.frames` | which way does a rectilinear crop of a panorama face |
| :mod:`.pinhole` | which pixel is this triangle, and which triangle is this pixel |
| :mod:`.planar` | polygon arithmetic in the image plane |
| :mod:`.mesh` | read the support mesh, and shoot a ray at it |
| :mod:`.camera_ground` | how high is the ground under this one camera |
| :mod:`.fishnet` | cut the visible mesh at the semantic island boundaries |

Two neighbours are named here because a reader will look for them and not find
them.

:mod:`semantic_twin.pano_geometry` is part of this layer and was left where it
is. It is the panorama sphere: equirectangular pixels, the rectilinear crops
sampled off them, and the rotation from panorama-local axes to world ENU. It has
about thirty importers spread over modules five other waves are rewriting, so
moving it would mean two live spellings of the most imported module in the
package while everybody is editing. :mod:`.frames` holds the one function it and
:mod:`.pinhole` genuinely share.

:mod:`semantic_twin.walk.ground` measures the walkable datum of a whole square.
:mod:`.camera_ground` measures the surface under one camera. Same word,
different question, and they disagree at seven of the 51 admitted stations.

Nothing heavy is imported at this level. :mod:`.fishnet` pulls in shapely and
scikit-image, :mod:`.mesh` pulls in trimesh, and both stay behind their own
import.
"""
