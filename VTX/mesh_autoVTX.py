'''
BEGIN GPL LICENSE BLOCK

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

END GPL LICENCE BLOCK
'''

bl_info = {
    "name": "autoVTX",
    "author": "zeffii (aka Dealga McArdle)",
    "version": (1, 0, 0),
    "blender": (2, 7, 0),
    "category": "Mesh",
    "location": "View3D > EditMode > (w) Specials",
    "wiki_url": "",
    "tracker_url": ""
}

"""
rewrite of the VTX addon, it automatically decides based on what
you've selected.

"""

import bpy
import sys
import bmesh
from mathutils import Vector, geometry
from mathutils.geometry import intersect_line_line as LineIntersect

VTX_PRECISION = 1.0e-5  # or 1.0e-6 ..if you need


def point_on_edge(p, edge):
    '''
    - p is a vector
    - edge is a tuple of 2 vectors
    returns True / False if a point happens to lie on an edge
    '''
    A, B = edge
    eps = (((A - B).length - (p - B).length) - (A - p).length)
    return abs(eps) < VTX_PRECISION


def get_intersection_points(edge1, edge2):
    [p1, p2], [p3, p4] = edge1, edge2
    return LineIntersect(p1, p2, p3, p4)


def intersection_edge(edge1, edge2):
    line = get_intersection_points(edge1, edge2)
    return ((line[0] + line[1]) / 2)


def test_coplanar(edge1, edge2):
    line = get_intersection_points(edge1, edge2)
    return (line[0]-line[1]).length < VTX_PRECISION


def closest(p, e):
    ''' p is a vector, e is a bmesh edge'''
    ev = e.verts
    v1 = ev[0].co
    v2 = ev[1].co
    distance_test = (v1 - p).length < (v2 - p).length
    return ev[0].index if distance_test else ev[1].index


def coords_from_idx(self, idx):
    v = self.bm.edges[idx].verts
    return v[0].co, v[1].co


def find_intersection_vector(self):
    return intersection_edge(self.edge1, self.edge2)


def find_intersecting_edges(self, idx1, idx2, point):
    edges = [None, None]
    if point_on_edge(point, self.edge1):
        edges[0] = idx1
    if point_on_edge(point, self.edge2):
        edges[1] = idx2
    return edges


def checkVTX(context, self):
    '''
    - decides VTX automatically.
    - remembers edges attached to current selection, for later.
    '''

    # [x] if either of these edges share a vertex, return early.
    ei = [self.bm.edges[i].verts for i in self.selected_edges]
    ii = [ei[a][b].index for a, b in [(0, 0), (0, 1), (1, 0), (1, 1)]]
    if len(set(ii)) < 4:
        msg = "edges share a vertex, degenerate case, returning early"
        self.report({"WARNING"}, msg)
        return

    # [x] find which edges intersect
    idx1, idx2 = self.selected_edges
    self.edge1 = coords_from_idx(self, idx1)
    self.edge2 = coords_from_idx(self, idx2)

    point = find_intersection_vector(self)
    edges = find_intersecting_edges(self, idx1, idx2, point)

    # [x] it may not be coplanar
    print(edges)
    if [None, None] == edges:
        coplanar = test_coplanar(self.edge1, self.edge2)
        if not coplanar:
            msg = "not coplanar! returning early"
            self.report({"WARNING"}, msg)
            return


class AutoVTX(bpy.types.Operator):
    ''' Makes a weld/slice/extend to intersecting edges/lines '''
    bl_idname = 'view3d.autovtx'
    bl_label = 'autoVTX'
    # bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        '''
        - only activate if two selected edges
        - and both are not hidden
        '''

        obj = context.active_object
        self.me = obj.data
        self.bm = bmesh.from_edit_mesh(self.me)
        self.me.update()

        if obj is not None and obj.type == 'MESH':
            edges = self.bm.edges
            ok = lambda v: v.select and not v.hide
            idxs = [v.index for v in edges if ok(v)]
            if len(idxs) is 2:
                self.selected_edges = idxs
                self.edge1 = None
                self.edge2 = None
                return True

    def execute(self, context):
        self.geom_cache = []
        checkVTX(context, self)
        return {'FINISHED'}


def menu_func(self, context):
    nm = "Edges VTX Intersection"
    self.layout.operator(AutoVTX.bl_idname, text=nm)


def register():
    bpy.utils.register_class(AutoVTX)
    bpy.types.VIEW3D_MT_edit_mesh_specials.append(menu_func)


def unregister():
    bpy.utils.unregister_class(AutoVTX)
    bpy.types.VIEW3D_MT_edit_mesh_specials.remove(menu_func)


if __name__ == "__main__":
    register()