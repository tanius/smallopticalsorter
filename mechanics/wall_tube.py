import cadquery as cq
from cadquery import selectors
import logging
import importlib
from math import sqrt, asin, degrees
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)


class WallTube:
    def __init__(self, workplane, measures):
        """
        A parametric wastewater tube socket in a wall.
        
        The parameters allow to make this a socket for EN 1451 wastewater tubes.

        :param workplane: The CadQuery workplane to create the chute on.
        :param measures: The measures to use for the parameters of this design. Keys and defaults:
            - **``name``:** Description. TODO.

        .. todo:: Probably it's better to make the whole input tube 3D printable. It's short anyway, 
            easily 3D printed, and allows to avoid the overhang on the back wall since the whole section 
            with the rubber ring can be inside.
        .. todo:: Add a dummy for the tube's widening connector end.
        .. todo:: Add a cylindrical sheath at the front side of the tube holder to provide surface for 
            glueing in the tube.
        .. todo:: Cut out the tube's shape from the tube holder using a tolerance gap between the two.
        .. todo:: Cut out the slots for mounting the tube holder to the wall, with added tolerance for 
            a gap. (No wall dummy needed.)
        """

        self.model = workplane
        self.build()


    def build(self):
        
        # Add the tube.
        self.model = (
            self.model
            .circle(32/2)
            .circle(32/2 - 3)
            .extrude(200)
            .translate((0,0,-100))
            .rotateAboutCenter((1, 0, 0), 45)
        )

        # Add the wall element.
        # self.model = (
        #     self.model
        #     .workplane("XY")
        #     .box(40, 10, 60)
        # )


# =============================================================================
# Part Creation
# =============================================================================

cq.Workplane.part = utilities.part

measures = dict()
show_options = {"color": "orange", "alpha": 0.6}

wall_tube = cq.Workplane("XY").part(WallTube, measures)
show_object(wall_tube, name = "wall_tube", options = show_options)
