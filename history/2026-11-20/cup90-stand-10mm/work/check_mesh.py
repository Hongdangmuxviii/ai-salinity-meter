"""Check the exported stand without modifying the mesh."""
from collections import Counter, defaultdict, deque
from pathlib import Path
import json
import struct

import numpy as np

mesh_path = Path(__file__).resolve().parent.parent / "cup90_stand_10mm_v2.stl"
data = mesh_path.read_bytes()
triangle_count = struct.unpack_from("<I", data, 80)[0]
assert len(data) == 84 + triangle_count * 50, "Unexpected binary STL length"

facets = []
vertices = {}
points = []
for index in range(triangle_count):
    values = struct.unpack_from("<12fH", data, 84 + index * 50)
    facet = []
    for offset in (3, 6, 9):
        point = tuple(round(value, 5) for value in values[offset:offset + 3])
        if point not in vertices:
            vertices[point] = len(points)
            points.append(point)
        facet.append(vertices[point])
    assert len(set(facet)) == 3, "Degenerate face"
    facets.append(facet)

edge_counts = Counter()
directed_edges = Counter()
neighbors = defaultdict(set)
for facet in facets:
    for first, second in zip(facet, facet[1:] + facet[:1]):
        edge_counts[tuple(sorted((first, second)))] += 1
        directed_edges[(first, second)] += 1
        neighbors[first].add(second)
        neighbors[second].add(first)

assert all(count == 2 for count in edge_counts.values()), "Non-manifold or open edge"
assert all(directed_edges[(a, b)] == directed_edges[(b, a)] for a, b in edge_counts), "Inconsistent winding"
visited = {0}
queue = deque([0])
while queue:
    for neighbor in neighbors[queue.popleft()]:
        if neighbor not in visited:
            visited.add(neighbor)
            queue.append(neighbor)
assert len(visited) == len(points), "More than one disconnected component"

coordinates = np.array(points)
triangles = coordinates[np.array(facets)]
signed_volume = np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6
assert signed_volume > 0, "Inverted mesh"
dimensions = coordinates.max(axis=0) - coordinates.min(axis=0)
assert np.allclose(dimensions, [126, 30, 40], atol=0.001)
assert abs(coordinates[:, 2].min()) < 0.001, "Print base must be at z=0"

results = {
    "triangles": triangle_count,
    "closed_manifold": True,
    "connected_components": 1,
    "dimensions_mm": dimensions.tolist(),
    "volume_cm3": round(signed_volume / 1000, 3),
    "solid_PLA_mass_g_at_1_24_density": round(signed_volume / 1000 * 1.24, 2),
    "head_bearing_mm_each_side": (58 - 36.8) / 2,
    "head_side_clearance_mm_each_side": 0.6,
    "rim_side_clearance_mm_at_90mm": (94 - 90) / 2,
    "head_bottom_below_rim_mm": 20,
    "exposed_tip_mm": 10,
    "example_water_below_rim_mm": 22,
    "example_immersion_mm": 8,
    "physical_fit_tested": False,
}
print(json.dumps(results, ensure_ascii=False, indent=2))
