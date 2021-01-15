import cadquery as cq
from cadquery import selectors
import logging
from math import sqrt, asin, degrees
import importlib

# Local directory imports.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
import utilities
import fdm_stud
importlib.reload(utilities)
importlib.reload(fdm_stud)

# In addition to importing the whole packages to be accessible by importlib.reload(), import some names.
from utilities import sagittaArcOrLine, uProfile
from fdm_stud import fdmStud

# TODOS FOR NOW
#
# @todo Refactor the code into a class.
# @todo Implement that the studs can have a captured nut inserted from the top near the end, allowing them 
#   to be bolted to the machine wall.
# @todo Implement that a stud will not get a support bracket when flush with the input, i.e. the print bed in 3D printing.
# @todo Create stud extension parts (basically just cylinders with a conical widening at the end and a hole for a 
#   bolt going through them, here to be configured for M4.) Because studs with support for 3D printing can only be short.
# @todo Correct the depth calculation. Currently, the part in front of the tip protrudes over the specified depth.

# TODOS FOR LATER
#
# @todo Add chamfers where the studs connect to the chute. (Better than fillets, as they are 3D printable.)
# @todo Make the stud supports for FDM 3D printing optional.
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
# Chute implementation
# =============================================================================

def chute(h, d, wall_thickness, 
          upper_w, lower_w, lower_straight_wall_h, lower_rounded_wall_h, upper_straight_wall_h, upper_rounded_wall_h,
          left_studs, left_wall_distance, right_studs, right_wall_distance
    ):
    """
    Create a chute from parametric upper and lower profiles, which can be rounded or square U-profiles.
    
    The chute is optimized for support-less FDM 3D printing upside-down, since the top end is not cut at an angle and suitable 
    as a standing surface. That also is a suitable orientation to get a strong part. The horizontal mounting studs come 
    with 45° integrated supports for 3D printing.
    
    Note that currently, the method will fail if any *_straight_wall_h is not at least 0.05 larger than wall_thickness. This is 
    because the system will consider such wires as incompatible for lofting. Error message: 
    "BRepCompatibleWires: SameNumberByPolarMethod failed".
    
    :param: h  Height of the chute in total, in its rotated position.
    :param: d  Depth of the chute in total, in its rotated position.
    :param: wall_thickness  Wall thickness of the chute's side walls, measured vertically to the wall.
    :param: upper_w  Outer width of the chute at its input.
    :param: lower_w  Outer width of the chute at its output.
    :param: lower_straight_wall_h  Height of the straight part of the chute's lower U profile's side walls, measured vertically 
      for a horizontal chute (means, before rotation). Must be at least wall_thickness, because that is the height of a 
      flat sheet of the given wall_thickness. If less, it is automatically treated as if wall_thickness was given.
    :param: lower_rounded_wall_h  Height of the rounded part of the chute's lower U profile's side walls, measured vertically 
      for a horizontal chute (means, before rotation).
    :param: upper_straight_wall_h  Like lower_straight_wall_h, but for the upper U profile.
    :param: upper_rounded_wall_h  Like lower_rounded_wall_h, but for the upper U profile.
    :param: left_studs  Positions of stud mounts on the chute's left side face, given as a list of tuples. Each tuple 
       defines the x and y position of one stud, with x measured from the edge along the chute opening and y measured from 
       the bottom tip, both for the unrotated chute in a vertical position.
    :param: left_wall_distance Gap between the chute and the left wall to which to mount it, at the narrowest point.
    :param: right_studs  Positions of stud mounts on the chute's left side face. See left_studs for the format.
    :param: right_wall_distance Gap between the chute and the right wall to which to mount it, at the narrowest point.
    """
    # @todo Check for the error condition mentioned in the function docstring, and correct it automatically, with a hint 
    #   to the user.
    
    cq.Workplane.uProfile = uProfile
    slide_length = sqrt(d*d + h*h)
    slide_angle = degrees(asin(h / slide_length)) # Drop angle at entry to the chute, same as exit angle.
    
    # Adjust the wall mount distances to count from the center plane.
    w = max(upper_w, lower_w)
    left_wall_distance = left_wall_distance + w / 2
    right_wall_distance = right_wall_distance + w / 2
    
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
    
    # Attach wall mount studs to the left side face.
    left_case_plane = cq.Workplane("YZ").workplane(offset = -left_wall_distance)
    left_face_plane = chute.faces("<X").workplane()
    for stud_pos in left_studs:
        a_stud = (
            left_case_plane
            .center(-stud_pos[0], stud_pos[1])
            .transformed(rotate = (0,0,180))
            .fdmStud(radius = 4, height = left_wall_distance + w)
            .copyWorkplane(left_face_plane)
            .split(keepTop = True)
        )
        chute = chute.union(a_stud, glue = True)
    
    # Attach wall mount studs to the right side face.
    # Note that workplane offsets are in the workplane's local z coordinates, which are reversed by invert = True.
    right_case_plane = cq.Workplane("YZ").workplane(offset = -right_wall_distance, invert = True)
    right_face_plane = chute.faces(">X").workplane()
    for stud_pos in left_studs:
        #a_stud = stud(radius = 4, base_plane = left_case_plane.center(-stud_pos[0], stud_pos[1]), cut_plane = left_face_plane)
        a_stud = (
            right_case_plane
            .center(-stud_pos[0], -stud_pos[1])
            .fdmStud(radius = 4, height = right_wall_distance + w)
            .copyWorkplane(right_face_plane)
            .split(keepTop = True)
        )
        chute = chute.union(a_stud, glue = True)

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

cq.Workplane.fdmStud = fdmStud

chute = chute(
    h = 50.0, d = 35.0, wall_thickness = 2, 
    upper_w = 50.0, upper_straight_wall_h = 30, upper_rounded_wall_h = 0,
    lower_w = 24.0, lower_straight_wall_h = 2.05, lower_rounded_wall_h = 10,
    left_studs = ((7, 53), (7, 25)), left_wall_distance = 5, 
    right_studs = ((7, 53), (7, 25)), right_wall_distance = 5
)

show_object(chute, name = "chute", options = {"color": "blue", "alpha": 0})
