import cadquery as cq
import cadquery.selectors as cqs
import logging, importlib
from types import SimpleNamespace as Measures
from math import cos, sin, pi, radians, degrees
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

class Diverter:

    def __init__(self, workplane, measures):
        """
        A parametric rotary object diverter to be mounted over conveyor units.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``TODO``:** TODO

        TODO: Finish the build_shovel() method.
        """
        cq.Workplane.distribute_circular = utilities.distribute_circular

        self.model = workplane
        self.debug = False
        self.measures = measures

        # TODO: Initialize missing measures with defaults.

        self.build()


    def build_shovel(self, size, height, cavity, inclination):
        """
        Create a single shovel arm starting at z=0, pointing up, centered around the z axis, with the 
        shovel opening pointing towards +x and -x.

        :param size: Width of the shovel's opening.
        :param height: Height of the shovel.
        :param cavity: Depth of the deepest part of the shovel, measured to a line connecting its edges.
        :param inclination: Angle in radial direction against vertical. Positive angle lean towards 
            the center, negative away from it.
        :return: A Cadquery Workplane object with a solid on the stack representing the shovel.
        """

        size_x = size
        size_y = size / 4

        return (
            cq.Workplane("XY")
            .box(size_x, size_y, height)
            .translate((0, 0, height / 2))
        )
        

    def build(self):
        m = self.measures

        self.model = (
            self.model
            .circle(m.baseplate.diameter / 2)
            .extrude(m.baseplate.thickness)
            .faces(">Z")
            .workplane()
            .distribute_circular(
                self.build_shovel(
                    size = m.shovel.size,
                    height = m.shovel.height,
                    cavity = m.shovel.cavity,
                    inclination = m.shovel.inclination
                ),
                radius = m.baseplate.diameter / 2 - m.shovel.size / 2,
                copies = m.shovel.count,
                align = "center"
            )
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

measures = Measures(
    baseplate = Measures(
        diameter = 70,
        thickness = 2.0
    ),
    shaft = Measures(
        diameter = 5.0,
        flatten = 0.0
    ),
    shovel = Measures(
        count = 6,
        height = 20.0,
        size = 15.0,
        cavity = 4.0,
        inclination = -22.5
    )
)
show_options = {"color": "lightgray", "alpha": 0}

diverter = cq.Workplane("XY").part(Diverter, measures)
show_object(diverter, name = "diverter", options = show_options)
