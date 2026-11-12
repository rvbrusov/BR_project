"""Geometry of oriented text extents, for non-overlapping axis captions."""
import math

def box(x,y,width,height,angle=0,anchor='center',padding=3):
    left=-width if anchor=='e' else 0 if anchor=='w' else -width/2
    right=left+width;top=-height/2;bottom=height/2
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    return [(x+u*c+v*s,y-u*s+v*c) for u,v in ((left-padding,top-padding),(right+padding,top-padding),(right+padding,bottom+padding),(left-padding,bottom+padding))]

def intersects(a,b):
    for polygon in (a,b):
        for p,q in zip(polygon,polygon[1:]+polygon[:1]):
            axis=(q[1]-p[1],p[0]-q[0])
            av=[x*axis[0]+y*axis[1] for x,y in a];bv=[x*axis[0]+y*axis[1] for x,y in b]
            if max(av)<=min(bv) or max(bv)<=min(av):return False
    return True
