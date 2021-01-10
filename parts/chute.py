import cadquery as cq
import logging
from math import sqrt, asin, degrees

# TODOS FOR NOW
#
# @todo Add a parametric mounting bracket to the wall. 
#   Proposal: Add 3-4 studs that have a captured nut inserted from the top near the end, allowing them to be bolted to 
#   the machine wall. That uses little material and, when in a triangle arrangement and with brackets stabilizing the studs, 
#   is quite tough. It can also nivellate the different wall distances of the chute along its length.
#   Proposal: Draw the bracket as part of the profiles and then be extruded together with the chute shape.
# @todo Adapt the depth calculation. Currently, the part in front of the tip protrudes over the specified depth.

# TODOS FOR LATER
#
# @todo Use an elliptical arc instead of a circular arc. That allows deep chutes and also avoids the problem of 
#   arcs being more than a half circle sometimes. See: https://cadquery.readthedocs.io/en/latest/classreference.html#cadquery.Workplane.ellipseArc
# @todo Rotate the part 180° around z. Because parts should be created in their natural orientation to be well re-usable.
# @todo If necessary, cut off the upper chute end somewhat (but not vertically down, that would be too much).
# @todo If necessary, add that a width (x axis) offset of the output can be configured.
# @todo Refactor the uProfile() straight_h and rounded_h parameters to be more natural and less technical. As in: both 
#   parameters should only refer to the height added to a flat sheet by adding straight resp. rounded walls. So the total 
#   height would be higher by wall_thickness. Also, rounded_h = w/2 should create a half circle.
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
    A configurable U-shaped profile that can be rounded or flat at the bottom.
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
        .move(- w / 2 + wall_thickness / 2, wall_thickness / 2)
        # First straight wall. A straight_h value of just wall_thickness is a flat sheet, so draw no vertical walls in that case.
        .vLine(straight_h - wall_thickness)
        # Without straight wall parts, the arc endpoint starts on the centerline of a flat sheet, so "- wall_thickness / 2".
        .sagittaArcOrLine(endPoint = (w / 2 - wall_thickness / 2, straight_h - wall_thickness / 2), sag = rounded_h)
        # Second straight wall, drawn in the opposite direction as the first. See above.
        .vLine(-straight_h + wall_thickness)
    )

    # Inside outline.
    #   Draw in parallel to the centerline but in the other direction, to create a very thin U profile. Because offset2D() 
    #   cannot deal with zero-width shapes yet due to a bug. See: https://github.com/CadQuery/cadquery/issues/508
    #   @todo Get the bug mentioned above fixed.
    arc_endpoint = (- w / 2 + wall_thickness / 2 + nothing, straight_h - wall_thickness / 2 - nothing)
    profile = (profile
        .hLine(-nothing)
        .vLine(straight_h - wall_thickness)
        .sagittaArcOrLine(arc_endpoint, -rounded_h)
        .vLine(-straight_h + wall_thickness)
        .close()
    )
    
    # Offset to create a shape in wall_thickness and with rounded edges.
    profile = profile.offset2D(wall_thickness / 2, "arc")
    
    return profile


def chute(h, d, wall_thickness, upper_w, lower_w, lower_straight_wall_h, lower_rounded_wall_h, upper_straight_wall_h, upper_rounded_wall_h):
    """
    Create a chute from parametric upper and lower profiles.
    
    Note that currently, the method will fail if any *_straight_wall_h is not at least 0.05 larger than wall_thickness. This is 
    because the system will consider such wires as incompatible for lofting. Error message: 
    "BRepCompatibleWires: SameNumberByPolarMethod failed".
    """
    
    # @todo Check for the error condition mentioned in the function docstring, and correct it automatically, with a hint 
    #   to the user.
    
    log = logging.getLogger(__name__)
    cq.Workplane.uProfile = uProfile
    
    # Since we'll cut off the chute horizontally and vertically, its 
    # slide length is simply based on Pythagoras of is depth and height:
    slide_length = sqrt(d*d + h*h)
    # Drop angle at entry to the chute, same as exit angle.
    slide_angle = degrees(asin(h / slide_length))
    
    # Normal lofting, does not work as creating two wires from the same Workplane object will cause the first one created to 
    #   use an arbitrarily larger number in the offset2D() operation.
    # @todo Fix the bug mentioned above and then re-enable this normal lofting code.
    # chute = (cq
    #     .Workplane("XY")
    #     .uProfile(w = lower_w, straight_h = lower_straight_wall_h, rounded_h = lower_rounded_wall_h, wall_thickness = wall_thickness)
    #     .workplane(offset = slide_length)
    #     .uProfile(w = upper_w, straight_h = upper_straight_wall_h, rounded_h = upper_rounded_wall_h, wall_thickness = wall_thickness)
    #     .loft(combine = True)
    # )
    
    # Lofting with a special technique by creating the wires independently, as a workaround for the above issue. See:
    # https://github.com/CadQuery/cadquery/issues/327#issuecomment-616127686
    lower_profile = cq.Workplane("XY").uProfile(
        w = lower_w, straight_h = lower_straight_wall_h, rounded_h = lower_rounded_wall_h, wall_thickness = wall_thickness
    )
    upper_profile = cq.Workplane("XY").transformed(offset = (0,0,slide_length)).uProfile(
        w = upper_w, straight_h = upper_straight_wall_h, rounded_h = upper_rounded_wall_h, wall_thickness = wall_thickness
    )
    chute = cq.Workplane("XY")
    chute.ctx.pendingWires.extend(lower_profile.ctx.pendingWires)
    chute.ctx.pendingWires.extend(upper_profile.ctx.pendingWires)
    chute = chute.loft(combine = True)
    
    # Rotate the chute as needed.
    chute = chute.rotate((-1,0,0), (1,0,0), -(90 - slide_angle))
    
    # Cut off the lower chute end horizontally.
    # output_shape width and depth is generous to cut off a widening chute properly.
    output_shape = cq.Workplane("XY").box(lower_w * 4, d * 4, h).translate((0,0,-h/2))
    chute = chute.cut(output_shape)

    return chute


# =============================================================================
# Part Creation
# =============================================================================

# Proposal for the chute dimensions, adapt as needed.
chute = chute(
    h = 50.0, d = 35.0, wall_thickness = 2, 
    upper_w = 50.0, upper_straight_wall_h = 30, upper_rounded_wall_h = 0,
    lower_w = 24.0, lower_straight_wall_h = 2.05, lower_rounded_wall_h = 10,
)


# =============================================================================
# Debug Assistance
# =============================================================================

# Debug helper code (displaying profiles instead of the chute).
#
#cq.Workplane.uProfile = uProfile
# measure_element = (cq.Workplane("XY").box(24, 24, 1).translate((0,0,-1.5)))
# chute_profile = (cq
#     .Workplane("XY")
#     .uProfile(w = 24, straight_h = 2.0, rounded_h = 10, wall_thickness = 2)
# )
