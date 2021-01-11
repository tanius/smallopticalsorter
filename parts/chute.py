import cadquery as cq
from cadquery import selectors
import logging
from math import sqrt, asin, degrees

# TODOS FOR NOW
#
# @todo Give the studs a proper shape. Use 3-4 studs that have a captured nut inserted from the top near the end, allowing them 
#   to be bolted to the machine wall. That uses little material and, when in a triangle arrangement and with brackets 
#   stabilizing the studs, is quite tough. It can also nivellate the different wall distances of the chute along its length.
# @todo Adapt the depth calculation. Currently, the part in front of the tip protrudes over the specified depth.

# TODOS FOR LATER
#
# @todo Use an elliptical arc instead of a circular arc. That allows deep chutes and also avoids the problem of 
#   arcs being more than a half circle sometimes. See: https://cadquery.readthedocs.io/en/latest/classreference.html#cadquery.Workplane.ellipseArc
#   Or even better, use a spline: https://github.com/CadQuery/cadquery/issues/318#issuecomment-612860937
# @todo If necessary, cut off the upper chute end somewhat (but not vertically down, that would be too much).
# @todo If necessary, add that a width (x axis) offset of the output can be configured.
# @todo Refactor the uProfile() straight_h and rounded_h parameters to be more natural and less technical. As in: both 
#   parameters should only refer to the height added to a flat sheet by adding straight resp. rounded walls. So the total 
#   height would be higher by wall_thickness. Also, rounded_h = w/2 should create a half circle.
# @todo Fix that, depending on the wall_thickness setting and esp. for larger ones, CadQuery might choose a different 
#   mode of lofting, which connects the two profiles in ways that do not lead to a smooth rounded edge along the chute.
# @todo Support different widths at the front and back of the profile. That allows to visually correct that cutting 
#   a longitudinally widening chute at a non-orthogonal angle will create a shape where the side walls are narrower 
#   together at the front of the chute because that portion at the tip of the chute comes from a different length.


# =============================================================================
# Reusable Code
# =============================================================================

# Arcs cannot be straight lines, so we have to catch that case.
def sagittaArcOrLine(self, endPoint, sag):
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


def stud(radius, base_plane, cut_plane):
    """
    Create a cylinder vertically in the origin of plane_1 and cut by plane_2. This allows to create connectors between 
    a case wall and any face of a part.
    :radius: Radius of the studding cylinder.
    :param: base_plane  The base plane, with its origin where the stud should be created and its normal vector pointing towards 
    cut_plane.
    :param: cut_plane  The plane to cut the studding cylinder.
    """
    stud = (
        cq.Workplane("XY")
        .copyWorkplane(base_plane)
        .circle(radius)
        .extrude(500) # @todo: Limit this to approx. the distance to face_plane.
        .copyWorkplane(cut_plane)
        .split(keepTop = True)
    )
    # show_object(stud, name = "stud DEBUG HELPER", options = {"color": "red", "alpha": 0})
    return stud


def chute(h, d, wall_thickness, upper_w, lower_w, lower_straight_wall_h, lower_rounded_wall_h, upper_straight_wall_h, upper_rounded_wall_h):
    """
    Create a chute from parametric upper and lower profiles.
    
    Note that currently, the method will fail if any *_straight_wall_h is not at least 0.05 larger than wall_thickness. This is 
    because the system will consider such wires as incompatible for lofting. Error message: 
    "BRepCompatibleWires: SameNumberByPolarMethod failed".
    """
    # @todo Check for the error condition mentioned in the function docstring, and correct it automatically, with a hint 
    #   to the user.
    
    cq.Workplane.uProfile = uProfile
    slide_length = sqrt(d*d + h*h)
    slide_angle = degrees(asin(h / slide_length)) # Drop angle at entry to the chute, same as exit angle.
    
    # Create wires for the lower and upper profile independently, while no other pending wire is present. Because offset2D() 
    # used in uProfile() will affect all pending wires at the same time. See: https://github.com/CadQuery/cadquery/issues/570
    lower_profile = cq.Workplane("XY").uProfile(
        w = lower_w, straight_h = lower_straight_wall_h, rounded_h = lower_rounded_wall_h, wall_thickness = wall_thickness
    )
    upper_profile = cq.Workplane("XY").transformed(offset = (0,0,slide_length)).uProfile(
        w = upper_w, straight_h = upper_straight_wall_h, rounded_h = upper_rounded_wall_h, wall_thickness = wall_thickness
    )
    chute = cq.Workplane("XY")
    chute.ctx.pendingWires.extend(lower_profile.ctx.pendingWires)
    chute.ctx.pendingWires.extend(upper_profile.ctx.pendingWires)
    
    # Create the basic chute solid.
    chute = chute.loft(combine = True)
    
    # Attach studs to a side face, to allow mounting to a wall or case.
    left_face_plane = chute.faces("<X").workplane()
    right_face_plane = chute.faces("<X").workplane()
    left_case_plane = cq.Workplane("YZ").workplane(offset = -35)
    right_case_plane = cq.Workplane("YZ").workplane(offset = 35)
    # show_object(left_face_plane.box(100, 100, 1), name = "DEBUG HELPER", options = {"color": "blue", "alpha": 0.9})
    stud_1 = stud(radius = 4, base_plane = left_case_plane.center(-7, 53), cut_plane = left_face_plane)
    stud_2 = stud(radius = 4, base_plane = left_case_plane.center(-7, 25), cut_plane = left_face_plane)
    chute = chute.union(stud_1, glue = True).union(stud_2, glue = True)
    
    # Rotate the chute as needed.
    chute = chute.rotate((-1,0,0), (1,0,0), 90 - slide_angle)
    
    # Cut off the lower chute end horizontally (along the XY plane).
    #   Workplanes are not rotated when rotating the object, so we can use the original baseplane without needing a 
    #   Workplane::transformed(rotate = (…)).
    chute = chute.copyWorkplane(cq.Workplane("XY")).split(keepTop = True)

    return chute

# =============================================================================
# Debug Assistance
# =============================================================================

# Enable logging.
# log = logging.getLogger(__name__)

# Display profiles instead of the chute.
# cq.Workplane.uProfile = uProfile
# chute_profile = (cq
#     .Workplane("XY")
#     .uProfile(w = 24, straight_h = 10, rounded_h = 6, wall_thickness = 4)
# )

# =============================================================================
# Part Creation
# =============================================================================

chute = chute(
    h = 50.0, d = 35.0, wall_thickness = 2, 
    upper_w = 50.0, upper_straight_wall_h = 30, upper_rounded_wall_h = 0,
    lower_w = 24.0, lower_straight_wall_h = 2.05, lower_rounded_wall_h = 10
)

show_object(chute, name = "chute", options = {"color": "blue", "alpha": 0})
