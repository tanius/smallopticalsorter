import cadquery as cq
from math import sin, cos, radians, sqrt


def optionalPolarLine(self, support_h, angle):
    if support_h == 0:
        return self
    else:
        return self.polarLine(support_h, angle)


def circlePoint(radius, angle):
    angle = radians(angle)
    return (radius * sin(angle), radius * cos(angle))


def studProfile(self, radius, support_h):
    """
    :param: support_h  
    """
    
    # Width of the straight line at the bottom of the support.
    # Imagine the circle with two tangents that meet at 90°. support_w is the line between the points 
    # where the tangents meet, forming a triangle with them. The other two sides of the triangle are of 
    # length radius, so Pythagoras lets us solve for support_w.
    support_w = sqrt(2 * radius * radius)
    
    return (
        self
        # Workplane transformation relative to global coordinates, to provide the result along the depth axis(y)
        # while allowing to work with a more comfortable local coordinate system in this method.
        .transformed(rotate = cq.Vector(0, 0, 45))
        .moveTo(0, -radius)
        .threePointArc(circlePoint(radius, 45), (-radius, 0))
        .optionalPolarLine(support_h, -135)
        .optionalPolarLine(support_w, -45)
        .close()
        # Transform the workplane's coordinate system back to its original state to prevent side effects on the 
        # calling code, which is using the same workplane.
        .transformed(rotate = cq.Vector(0, 0, -45))
    )


def fdmStud(height, radius):
    return (
        cq
        .Workplane("XY")
        .studProfile(radius = radius, support_h = height) # lower profile
        .transformed(offset = cq.Vector(0, 0, height))
        # We need a minimal support height to guarantee that the upper and lower stud profile have an identical 
        # number of edges. That makes lofting predictable, like an extrusion with a cutoff in this case. With 
        # unequal numbers of edges, loft() would choose by itself which to combine, resulting in a weird shape.
        .studProfile(radius = radius, support_h = 0.01) # upper profile
        .loft(combine = True)
    )


cq.Workplane.optionalPolarLine = optionalPolarLine
cq.Workplane.studProfile = studProfile

fdm_stud = fdmStud(height = 30, radius = 10)
