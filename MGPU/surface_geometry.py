"""Display-only smooth quadrilateral mesh; missing measurements remain gaps."""
import math


def interpolate(values, coordinate):
    """Shape-preserving Hermite interpolation, with no extrapolation over gaps."""
    nearest=round(coordinate)
    if abs(coordinate-nearest)<1e-10:
        return values[nearest] if 0<=nearest<len(values) else None
    index=math.floor(coordinate)
    if index<0 or index+1>=len(values):
        return None
    a,b=values[index:index+2]
    if a is None or b is None:
        return None
    delta=b-a
    def slope(left,right):
        return 0. if left*right<=0 else 2*left*right/(left+right)
    before=values[index-1] if index else None
    after=values[index+2] if index+2<len(values) else None
    sa=delta if before is None else slope(a-before,delta)
    sb=delta if after is None else slope(delta,after-b)
    t=coordinate-index
    result=(2*t**3-3*t*t+1)*a+(t**3-2*t*t+t)*sa+(-2*t**3+3*t*t)*b+(t**3-t*t)*sb
    return max(min(a,b),min(max(a,b),result))


def surface_mesh(values,order,nx=30,ny=20):
    """31 by 21 vertices; four or six method samples retain their exact values."""
    rows=[]
    for ix in range(nx+1):
        x=ix*(len(order)-1)/nx
        stages=[interpolate([values[code][stage] for code in order],x) for stage in range(3)]
        rows.append([(x,iy*2/ny,interpolate(stages,iy*2/ny)) for iy in range(ny+1)])
    return rows
