import cadquery as cq
from cadquery import selectors
import logging
from math import sqrt, asin, degrees

# A parametric tube passage for walls.

# @todo Probably it's better to make the whole input tube 3D printable. It's short anyway, easily 3D printed, and allows 
#   to avoid the overhang on the back wall since the whole section with the rubber ring can be inside.
# @todo Add a dummy for the tube's widening connector end.
# @todo Add a cylindrical sheath at the front side of the tube holder to provide surface for glueing in the tube.
# @todo Cut out the tube's shape from the tube holder using a tolerance gap between the two.
# @todo Cut out the slots for mounting the tube holder to the wall, with added tolerance for a gap. (No wall dummy needed.)
# @todo Make the design parametric.

tube_dummy = (
    cq
    .Workplane("XY")
    .circle(32/2)
    # .circle(32/2 - 3)  # We keep the tube solid to function properly as a cutter for the tube holder.
    .extrude(200)
    .translate((0,0,-100))
    .rotateAboutCenter((1, 0, 0), 45)
)

tube_holder = (
    cq
    .Workplane("XY")
    .box(40, 10, 60)
)