from copy import deepcopy
import tkinter as tk

import pytest
import aviatest_v4 as v
from surface_geometry import interpolate,surface_mesh
from surface_view import SurfaceCanvas


@pytest.mark.parametrize('order',[v.ORDER,('A','C','D','B')])
def test_mesh_preserves_all_samples_and_value_bounds(order):
    values={code:[.2+i*.07,1.7-i*.05,.4+i*.1] for i,code in enumerate(order)}
    original=deepcopy(values)
    mesh=surface_mesh(values,order)
    assert len(mesh)==31 and all(len(row)==21 for row in mesh)
    for x,code in enumerate(order):
        for y,value in enumerate(values[code]):
            assert mesh[round(x*30/(len(order)-1))][y*10][2]==pytest.approx(value)
    assert all(.2<=z<=1.7 for row in mesh for x,y,z in row)
    assert values==original


def test_interpolation_gaps_zero_and_flat_fields():
    assert interpolate([0,1,0],0)==0
    assert interpolate([0,None,1],.5) is None
    assert interpolate([0,None,1],1.5) is None
    assert interpolate([0,None,1],2)==1
    order=('A','C','D','B')
    values={code:[1,1,1] for code in order}
    values['B']=[None]*3
    mesh=surface_mesh(values,order)
    assert all(p[2]==1 for row in mesh[:21] for p in row)
    assert all(p[2] is None for row in mesh[21:] for p in row)


def hull(points):
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    points=sorted(set(points));lower=[];upper=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=1e-7:lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=1e-7:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


