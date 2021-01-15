import cadquery as cq
from math import sin, cos, radians

# =============================================================================
# Simple functions
# =============================================================================

def circlePoint(radius, angle):
    """
    Get the coordinates of apoint on the circle circumference.
    :param radius: Circle radius.
    :param angle: Angle of a radius line to the specified point, with the +y axis as 0°.
    
    :todo Switch to using the +x axis as 0°, as that conforms to the CadQuery 2D coordinate system.
    """
    angle = radians(angle)
    return (radius * sin(angle), radius * cos(angle))

# =============================================================================
# CadQuery plugins
# =============================================================================

def optionalPolarLine(self, length, angle):
    """
    CadQuery plugin that draws a polar line, or nothing if line length is 0.
    
    To use this, import it and also add the following line: `cq.Workplane.optionalPolarLine = optionalPolarLine`
    Since imports only import types  but don't execute code, this cannot be done at import time.
    
    :param self: A CadQuery Workplane object, available after registering it as a Workplane plugin method.
    :param length: Length of the line.
    :param length: Angle of the line, counting from the +x axis as zero.
    """
    if length == 0:
        return self
    else:
        return self.polarLine(length, angle)


def sagittaArcOrLine(self, endPoint, sag):
    """
    An arc that can also be a straight line, unlike with the CadQuery core Workplane.sagittaArc().
    :param: endPoint  End point for the arc. A 2-tuple, in workplane coordinates.
    :param: sag  Sagitta of the arc, or zero to get a straight line. A float, indicating the 
      perpendicular distance from arc center to arc baseline.
    """
    if sag == 0:
        return self.lineTo(endPoint[0], endPoint[1])
    else:
        return self.sagittaArc(endPoint, sag)


def uProfile(self, w, straight_h, rounded_h, wall_thickness):
    """
    A configurable U-shaped profile that can be rounded or flat at the bottom, open to +y.
    :param: w  The width of the profile, measured between the outside of its two parallel legs.
    :param: straight_h  Straight part of the wall height. Must be at least wall_thickness, as that is the height of a flat 
      sheet. If it is less, it is automatically corrected to wall_thickness.
    :param: rounded_h  Rounded portion of the wall height, measured as the arc height of convex curvature on the inside.
    :param: wall_thickness  The part wall thickness when measured orthogonal to the wall.
    """
        
    cq.Workplane.sagittaArcOrLine = sagittaArcOrLine

    # To create a non-zero but negligible surface, as offset2D() can't work with pure lines.
    nothing = 0.01
    
    # Automatically correct straight_h if needed, as the object is always at least as high as a flat sheet. Also, we have to 
    # make it a tiny bit larger than wall_thickness or else vLine() would trip because it gets a zero as argument.
    if straight_h <= wall_thickness: 
        straight_h = wall_thickness + nothing

    # Outside outline.
    #   Draw the wall centerline. Mirroring half the line does not simplify 
    #   anything as it complicated drawing the arc.
    profile = (self
        # Start position is the centerline of a wall_thickness thick, flat sheet touching the x axis.
        .move(- w / 2 + wall_thickness / 2, - wall_thickness / 2)
        # First straight wall. A straight_h value of just wall_thickness is a flat sheet, so draw no vertical walls in that case.
        .vLine(-straight_h + wall_thickness)
        # Without straight wall parts, the arc endpoint starts on the centerline of a flat sheet, so "- wall_thickness / 2".
        .sagittaArcOrLine(
            endPoint = (w / 2 - wall_thickness / 2, -straight_h + wall_thickness / 2), 
            sag = -rounded_h
        )
        # Second straight wall, drawn in the opposite direction as the first. See above.
        .vLine(straight_h - wall_thickness)
    )

    # Inside outline.
    #   Draw in parallel to the centerline but in the other direction, to create a very thin U profile. Because offset2D() 
    #   cannot deal with zero-width shapes yet due to a bug. See: https://github.com/CadQuery/cadquery/issues/508
    #   @todo Get the bug mentioned above fixed.
    profile = (profile
        .hLine(-nothing)
        .vLine(-straight_h + wall_thickness)
        .sagittaArcOrLine(
            endPoint = (- w / 2 + wall_thickness / 2 + nothing, -straight_h + wall_thickness / 2 - nothing), 
            sag = rounded_h
        )
        .vLine(straight_h - wall_thickness)
        .close()
    )
    
    # Offset to create a shape in wall_thickness and with rounded edges.
    profile = profile.offset2D(wall_thickness / 2, "arc")
    
    return profile