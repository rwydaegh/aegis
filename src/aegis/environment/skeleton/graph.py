"""Face extraction graph for the straight skeleton."""

from __future__ import annotations

from collections import defaultdict
from functools import cmp_to_key


def _pseudoangle(d):
    denom = abs(d[0]) + abs(d[1])
    if denom == 0:
        return 0
    p = d[0] / denom
    if d[1] < 0:
        return 3 + p
    return 1 - p


def _compare_angles(v_list, p1, p2, center):
    a1 = _pseudoangle(v_list[p1] - v_list[center])
    a2 = _pseudoangle(v_list[p2] - v_list[center])
    if a1 < a2:
        return 1
    return -1


class _Poly2FacesGraph:
    def __init__(self):
        self.g_dict = {}

    def add_vertex(self, vertex):
        if vertex not in self.g_dict:
            self.g_dict[vertex] = []

    def add_edge(self, edge):
        edge = set(edge)
        if len(edge) == 2:
            vertex1 = edge.pop()
            vertex2 = edge.pop()
            self.add_vertex(vertex1)
            self.add_vertex(vertex2)
            self.g_dict[vertex1].append(vertex2)
            self.g_dict[vertex2].append(vertex1)

    def edges(self):
        edges = []
        for vertex in self.g_dict:
            for neighbour in self.g_dict[vertex]:
                if {neighbour, vertex} not in edges:
                    edges.append((vertex, neighbour))
        return edges

    def circular_embedding(self, v_list, direction="CCW"):
        embedding = defaultdict(list)

        for vertex in self.g_dict:
            neighbors = self.g_dict[vertex]
            ordering = sorted(
                neighbors,
                key=cmp_to_key(lambda a, b, v=vertex: _compare_angles(v_list, a, b, v)),
            )

            if direction == "CCW":
                embedding[vertex] = ordering
            elif direction == "CW":
                embedding[vertex] = ordering[::-1]

        return embedding

    def faces(self, embedding, nr_of_poly_verts):
        edgeset = set()
        for edge in self.edges():
            edgeset.add((edge[0], edge[1]))
            edgeset.add((edge[1], edge[0]))

        faces = []
        path = []
        for edge in edgeset:
            path.append(edge)
            edgeset -= {edge}
            break

        while len(edgeset) > 0:
            neighbors = embedding[path[-1][-1]]
            next_node = neighbors[(neighbors.index(path[-1][-2]) + 1) % len(neighbors)]
            tup = (path[-1][-1], next_node)
            if tup == path[0]:
                faces.append(path)
                path = []
                for edge in edgeset:
                    path.append(edge)
                    edgeset -= {edge}
                    break
            else:
                if tup in path:
                    raise RuntimeError("Endless loop in poly2FacesGraph faces()")
                path.append(tup)
                edgeset -= {tup}
        if path:
            faces.append(path)

        final_faces = []
        for face in faces:
            orig_edges = [x[0] for x in enumerate(face) if x[1][0] < nr_of_poly_verts and x[1][1] < nr_of_poly_verts]
            if orig_edges:
                next_orig_index = next(
                    x[0] for x in enumerate(face) if x[1][0] < nr_of_poly_verts and x[1][1] < nr_of_poly_verts
                )
                face = face[next_orig_index:] + face[:next_orig_index]
            vert_list = [e[0] for e in face]
            if any(i >= nr_of_poly_verts for i in vert_list):
                final_faces.append(vert_list)
        return final_faces
