import cadquery as cq
import cadquery.selectors as cqs
import logging, importlib
from types import SimpleNamespace as Measures
from math import cos, radians
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class BoltMount:

    def __init__(self, workplane, measures):
        """
        A parametric mount for captured hex bolts to flat surfaces.

        This can be used for several purposes, including as a generic system of support studs for 
        mounting units inside machines and electronic devices to the case walls.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``block.width``:** Width of the mount's cuboid base shape.
            - **``block.height``:** Height of the mount's cuboid base shape.
            - **``block.depth``:** Depth of the mount's cuboid base shape.
            - **``hole.diameter``:** Diameter of the hole for the bolt to be mounted.
            - **``hole.head_depth``:** Longitudinal space for the captured bolt head.
            - **``hole.head_across_flats``:** Radial space for the captured bolt head, specified 
                as the "nut size" of that space. Should be minimally larger than the nut size of the 
                captured hexagonal bolt head.
            - **``brackets.positions``:** Where to create mount brackets around the main cuboid 
                shape. A SimpleNamespace objects with booleans values "left", "right", "top", "bottom".
            - **``brackets.height``:** Local height of an individual support bracket.
            - **``brackets.thickness``:** Thickness of an individual support bracket.
            - **``brackets.hole_count``:** Number of holes per support bracket.
            - **``brackets.hole_diameter``:** Diameter of the holes in the support brackets.
            - **``brackets.fillet_radius``:** Radius of the reinforcing fillet along the bracketed edge.

        .. todo:: Adjust the hole positioning to be suitable for high brackets.
        .. todo:: Place the bracket holes only into the non-filleted portion of the bracket.
        .. todo:: Adjust the positioning so that the mounted bolt is positioned upside-down on the 
            XY plane. That would be the natural orientation for a generic bolt mount.
        .. todo:: Allow configurations for each of the attached brackets individually, with 
            parameters for width and offet from the center of the core edge (plus or minus).
        .. todo:: Allow the bolt hole to go through the block at any angle, for cases when 
            the angle of the mounted bolt should not be simply 90°.
        """

        cq.Workplane.bracket = utilities.bracket
        cq.Workplane.transformedWorkplane = utilities.transformedWorkplane

        self.model = workplane
        self.debug = False
        self.measures = measures

        # todo: Initialize missing measures with defaults.

        self.build()


    def build(self):
        m = self.measures

        # Create the bolt mount base shape.
        self.model = (
            self.model
            .box(m.block.width, m.block.depth, m.block.height)
        )

        # Create brackets in the positions specified.
        # todo: Make this code more compact by avoiding the redundancy

        if m.brackets.positions.top:
            self.model = (
                self.model
                .faces(">Z").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 0)
                .bracket(
                    thickness = m.brackets.thickness, 
                    height = m.brackets.height,
                    width = m.block.width,
                    hole_count = m.brackets.hole_count, 
                    hole_diameter = m.brackets.hole_diameter,
                    edge_fillet = m.brackets.fillet_radius,
                    corner_fillet = min(m.block.width, m.brackets.height) / 4
                )
            )

        if m.brackets.positions.bottom:
            self.model = (
                self.model
                .faces("<Z").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 180)
                .bracket(
                    thickness = m.brackets.thickness,
                    height = m.brackets.height,
                    width = m.block.width,
                    hole_count = m.brackets.hole_count,
                    hole_diameter = m.brackets.hole_diameter,
                    edge_fillet = m.brackets.fillet_radius,
                    corner_fillet = min(m.block.width, m.brackets.height) / 4
                )
            )
        
        if m.brackets.positions.left:
            self.model = (
                self.model
                .faces("<X").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 90)
                .bracket(
                    thickness = m.brackets.thickness,
                    height = m.brackets.height,
                    width = m.block.height,
                    hole_count = m.brackets.hole_count,
                    hole_diameter = m.brackets.hole_diameter,
                    # The OCCT CAD kernel cannot create fillets on adjacent sides of a cube that 
                    # meet in one point on their common edge. To prevent this, the left and right 
                    # brackets will get a minimally smaller fillet radius.
                    # todo: Once different measures can be used for all of the four brackets, the 
                    #   constructor has to make sure that the fillet measures are different between 
                    #   adjacent brackets.
                    edge_fillet = m.brackets.fillet_radius - 0.01,
                    corner_fillet = min(m.block.width, m.brackets.height) / 4
                )
            )

        if m.brackets.positions.right:
            self.model = (
                self.model
                .faces(">X").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 270)
                .bracket(
                    thickness = m.brackets.thickness,
                    height = m.brackets.height,
                    width = m.block.height,
                    hole_count = m.brackets.hole_count,
                    hole_diameter = m.brackets.hole_diameter,
                    # See the creation of the left bracket why we have to deduct 0.01.
                    edge_fillet = m.brackets.fillet_radius - 0.01,
                    corner_fillet = min(m.block.width, m.brackets.height) / 4
                )
            )

        self.model = (
            self.model

            # Fillet all outer edges except at the base.
            # Much easier to do now than after cutting the bolt hole, which would have to be excluded 
            # from the edges to fillet.
            .edges("(not %CIRCLE) and (not >Y)")
            .fillet(m.outer_edge_radius)
        
            # Cut the bolt hole into the core part.
            .faces("<Y")
            .workplane(centerOption = "CenterOfBoundBox")
            .hole(m.hole.diameter)

            # Cut the hex bolt head into the core part, from a workplane on the other side of the part.
            # TODO: Use dummy_bolt() from utilities.py instead of cutting bolt and bolthead separately.
            .faces("<Y")
            .workplane(centerOption = "CenterOfBoundBox", invert = True, offset = m.block.depth)
            # TODO: Use nut_hole() from utilities.py instead of polygon().
            .polygon(6, (m.hole.head_across_flats / 2) / cos(radians(30)) * 2)
            .cutBlind(-m.hole.head_depth)
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

measures = Measures(
    block = Measures(
        width = 20,
        height = 20,
        depth = 50
    ),
    hole = Measures(
        head_depth = 5,
        head_across_flats = 10.3,
        diameter = 6.1
    ),
    brackets = Measures(
        positions = Measures(top = True, bottom = True, left = False, right = False),
        height = 30,
        thickness = 6,
        hole_count = 1,
        hole_diameter = 5.1,
        fillet_radius = 10
    ),
    outer_edge_radius = 1.5
)
show_options = {"color": "lightgray", "alpha": 0}

bolt_mount = cq.Workplane("XY").part(BoltMount, measures)
show_object(bolt_mount, name = "bolt_mount", options = show_options)
