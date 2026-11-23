"""Read-only topology and size validation of generated ASCII STL files."""
import collections
import math
import pathlib
import re
import sys

for filename in sys.argv[1:]:
    source = pathlib.Path(filename).read_text(encoding="ascii")
    vertices = [tuple(round(float(v), 5) for v in line.split())
                for line in re.findall(r"vertex\s+([^\r\n]+)", source)]
    assert len(vertices) % 3 == 0
    edges = collections.Counter()
    graph = collections.defaultdict(set)
    volume = 0
    for i in range(0, len(vertices), 3):
        a, b, c = vertices[i:i+3]
        cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0])
        volume += sum(a[j]*cross[j] for j in range(3))/6
        ab = tuple(b[j]-a[j] for j in range(3))
        ac = tuple(c[j]-a[j] for j in range(3))
        area = math.sqrt(sum(v*v for v in (
            ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2],
            ab[0]*ac[1]-ab[1]*ac[0]))) / 2
        assert area > 1e-9, "Degenerate triangle"
        for p, q in [(a,b),(b,c),(c,a)]:
            edges[tuple(sorted((p,q)))] += 1
            graph[p].add(q)
            graph[q].add(p)
    assert all(count == 2 for count in edges.values()), "Non-manifold mesh"
    visited = set()
    components = 0
    for start in graph:
        if start in visited:
            continue
        components += 1
        stack = [start]
        while stack:
            p = stack.pop()
            if p in visited:
                continue
            visited.add(p)
            stack.extend(graph[p]-visited)
    assert components == 1, "Disconnected solids"
    bounds = [(min(v[j] for v in vertices), max(v[j] for v in vertices)) for j in range(3)]
    size = tuple(round(hi-lo, 3) for lo,hi in bounds)
    assert volume > 0
    print(pathlib.Path(filename).name, "triangles", len(vertices)//3,
          "closed manifold", True, "components", components, "size_mm", size,
          "volume_mm3", round(volume,2))
