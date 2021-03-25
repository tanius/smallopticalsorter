import cadquery as cq
import cadquery.selectors as cqs
import logging, importlib
from types import SimpleNamespace as Measures
from math import cos, radians, sqrt
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class PlateBracket:

    def __init__(self, workplane, measures):
        """
        A simple, parametric L-profile bracket to connect two flat plates.

        The bracket will have a horizontal leg pointing from the joint to the front (into -y) and a 
        vertical leg pointing from the joint to the top (into +z) of the provided workplane.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``center_fillet``:** Fillet radius for the main structural fillet of the bracket.
            - **``corner_radius``:** Radius for rounding the bracket's outside corners.
            - **``edge_radius``:** Radius for rounding all outer edges except those touching the plates.
            - **``horizontal_leg.width``:** Width of the horizontal leg of the bracket. Different widths 
                of the two legs are not yet supported.
            - **``horizontal_leg.depth``:** Depth of the horizontal leg of the bracket.
            - **``horizontal_leg.height``:** Height (material thickness) of the horizontal leg of the bracket.
            - **``horizontal_leg.hole_count``:** Number of holes in the horizontal leg of the bracket. 
                All holes will be arranged in a line.
            - **``horizontal_leg.hole_diameters``:** Diameter of the holes in the horizontal leg of the 
                bracket. Provided as a single float when using a common value for all holes; otherwise 
                as a list with one element for each hole in the bracket, starting with the one closest 
                to its front.
            - **``horizontal_leg.nuthole_sizes``:** Size between flats of the nutholes that are part 
                of the holes in the horizontal leg of the bracket. See ``hole_diamaters`` for the format.
            - **``horizontal_leg.clamp_lengths``:** Length between the outer surface of the part 
                (touching a connected plate) and the start of the nut hole. See ``hole_diamaters`` for the format.
            - **``vertical_leg.*``:** Specs for the vertical leg of the bracket, using the same 
                elements and semantics as for the horizontal leg.

        .. todo:: Support specifying custom hole spacings, for each hole relative to the previous one.
            If given, this will override the automatic positioning. Then use it to position the 
            holes closest to the joint closer to it. Currently, the material thickness of the other 
            leg prevents that from happening.
        .. todo:: Support chamfering in addition to filleting for the main structural support fillet.
        .. todo:: Support different widths of the two legs of the bracket.
        """

        cq.Workplane.bracket = utilities.bracket
        cq.Workplane.transformedWorkplane = utilities.transformedWorkplane
        cq.Workplane.bolt = utilities.bolt
        cq.Workplane.cutEachAdaptive = utilities.cutEachAdaptive

        self.model = workplane
        self.debug = False
        self.measures = measures
        m = self.measures

        # The bracket lengths are measured at the outside, but the construction actually uses a 
        # central cuboid block with two attached brackets. Adapting the measures accordingly.
        m.center_block = Measures(
            # Naming is as seen from the horizontal leg.
            width = max(m.horizontal_leg.width, m.vertical_leg.width),
            depth = m.vertical_leg.height,
            height = m.horizontal_leg.height
        )
        m.horizontal_leg.depth -= m.center_block.depth
        m.vertical_leg.depth -= m.center_block.height

        # Create hole specs which combine the other hole measures in the format expected by bolthole().
        m.horizontal_leg.hole_specs = [
            {
                "diameter": m.horizontal_leg.hole_diameters[i] if isinstance(m.horizontal_leg.hole_diameters, list) else m.horizontal_leg.hole_diameters,
                "clamp_length": m.horizontal_leg.clamp_lengths[i] if isinstance(m.horizontal_leg.clamp_lengths, list) else m.horizontal_leg.clamp_lengths, 
                "nuthole_size": m.horizontal_leg.nuthole_sizes[i] if isinstance(m.horizontal_leg.nuthole_sizes, list) else m.horizontal_leg.nuthole_sizes, 
                "nuthole_depth": 1.1 * m.vertical_leg.depth # Just choose something large enough for cutting. 
            }
            for i in range(m.horizontal_leg.hole_count)
        ]
        m.vertical_leg.hole_specs = [
            {
                "diameter": m.vertical_leg.hole_diameters[i] if isinstance(m.vertical_leg.hole_diameters, list) else m.vertical_leg.hole_diameters,
                "clamp_length": m.vertical_leg.clamp_lengths[i] if isinstance(m.vertical_leg.clamp_lengths, list) else m.vertical_leg.clamp_lengths, 
                "nuthole_size": m.vertical_leg.nuthole_sizes[i] if isinstance(m.vertical_leg.nuthole_sizes, list) else m.vertical_leg.nuthole_sizes, 
                "nuthole_depth": 1.1 * m.horizontal_leg.depth # Just choose something large enough for cutting. 
            }
            for i in range(m.vertical_leg.hole_count)
        ]

        # TODO: Initialize missing measures with defaults.

        self.build()


    def build(self):
        def bolthole(location, diameter, clamp_length, nuthole_size, nuthole_depth):
            """
            Create a bolthole at the specified location in the current workplane, with the given 
            measures.
            :param location: The location to place the bolthole, using the point at the center of 
                the hole cross-section and at half its clamp length as the handle.
            :param diameter: Diameter of the cylindrical section of the bolthole.
            :param clamp_length: Length between start of the bolt head and start of the nuthole.
            :param nuthole_size: Size between flats of a hexagonal hole for a nut.
            :param nuthole_depth: Maximum depth of the nuthole. If the part ends earlier, this 
                depth is not reached.
            """
            bolthole = (
                cq.Workplane()
                .bolt(
                    bolt_size = diameter,
                    head_size = 2 * diameter,
                    head_length = 2 * diameter,
                    head_shape = "cylindrical", 
                    head_angle = 90,
                    clamp_length = clamp_length,
                    nut_size = nuthole_size,
                    nut_length = nuthole_depth
                )
                .val()
                .located(location * cq.Location(cq.Vector(0, 0, - clamp_length / 2)))
            )
            # show_object(bolthole) # Debug helper.
            return bolthole

        m = self.measures

        self.model = (
            self.model
            # Cuboid to attach both brackets to.
            .box(m.center_block.width, m.center_block.depth, m.center_block.height)
            .translate((0, - m.center_block.depth / 2, m.center_block.height / 2))
            
            # Vertical leg.
            .faces(">Z")
            .edges(">Y")
            .transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 0)
            .tag("vertical_leg_workplane")
            .bracket(
                width = m.vertical_leg.width,
                height = m.vertical_leg.depth,
                thickness = m.vertical_leg.height,
                holes_count = m.vertical_leg.hole_count,
                holes_tag = "vertical_leg_holes",
                # No edge fillet here, as the 90° edge to place it only exists after creating the horizontal leg.
                # edge_fillet = m.center_fillet,
                corner_fillet = m.corner_radius
            )

            # Horizontal leg.
            .faces("<Y")
            .edges("<Z")
            .transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 180)
            .tag("horizontal_leg_workplane")
            .bracket(
                width = m.horizontal_leg.width,
                height = m.horizontal_leg.depth,
                thickness = m.horizontal_leg.height,
                holes_count = m.horizontal_leg.hole_count,
                holes_tag = "horizontal_leg_holes",
                edge_fillet = m.center_fillet,
                corner_fillet = m.corner_radius
            )

            # Fillet edges that don't touch the plates.
            .edges("(not <Z) and (not >Y)")
            .fillet(m.edge_radius)

            # Cut the holes.
            # This is not included as part of the bracket() calls because (1) we need holes incl. 
            # nut holes, not just the simple cylindrical holes that bracket() can create and (2) 
            # the main fillet may overlap and thus obstruct the hole in the bracket leg created 
            # first, if holes were cut at the time of the bracket() calls.
            .workplaneFromTagged("horizontal_leg_workplane")
            # Switch from the workplane of the bracket to that of its holes.
            .transformedWorkplane(centerOption = "CenterOfMass", rotate_x = -90)
            .vertices(tag = "horizontal_leg_holes")
            .cutEachAdaptive(bolthole, m.horizontal_leg.hole_specs, useLocalCoords = True)
            #
            .workplaneFromTagged("vertical_leg_workplane")
            .transformedWorkplane(centerOption = "CenterOfMass", rotate_x = -90)
            .vertices(tag = "vertical_leg_holes")
            .cutEachAdaptive(bolthole, m.vertical_leg.hole_specs, useLocalCoords = True)
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

bolt_length = 10.0

measures = Measures(
    center_fillet = 51.9, # Max. 52.0, which is the inner depth of the bracket.
    corner_radius = 5.0,
    edge_radius = 1.5,
    horizontal_leg = Measures(
        width = 15.0,
        depth = 60.0,
        height = 8.0,
        hole_count = 2,
        hole_diameters = 3.2, # Good for M3 and some printer artefacts.
        nuthole_sizes = 5.8, # 5.4 mm for a M3 nut, 0.4 mm for easy inserting. Corrected from 0.2.
        # Clamp length 7.5 is for M3×16, 11.5 is for M3×20, both with a countersunk head and 
        # for additional 5 mm plate material thickness. The bolt will protrude ca. 1 mm over the nut.
        clamp_lengths = [11.5, 7.5]
    ),
    vertical_leg = Measures(
        width = 15.0,
        depth = 60.0,
        height = 8.0,
        hole_count = 2,
        hole_diameters = 3.2,
        nuthole_sizes = 5.8,
        clamp_lengths = [11.5, 7.5]
    )
)

plate_bracket = cq.Workplane("XY").part(PlateBracket, measures)
show_options = {"color": "lightgray", "alpha": 0}
show_object(plate_bracket, name = "plate_bracket", options = show_options)

# Debug helpers.
# show_object(
#     plate_bracket.vertices(tag = "horizontal_leg_holes"), 
#     name = "horizontal_leg_holes", 
#     options = show_options
# )
# show_object(
#     plate_bracket.vertices(tag = "vertical_leg_holes"), 
#     name = "vertical_leg_holes", 
#     options = show_options
# )
