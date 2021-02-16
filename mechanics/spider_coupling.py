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


class SpiderCoupling:

    def __init__(self, workplane, measures):
        """
        A parametric shaft coupling of the Spider / Lovejoy type, without a rubber insert.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``TODO``:** TODO

        .. todo:: Fix that the cog generation code only works for 4 and 6 cogs so far.
        .. todo:: Make the cogs rounded or pointed at the top so that two parts will usually 
            come together under light pressure without having to turn one manually.
        .. todo:: Add a parameter to also use a rubber insert, allowing to create a backlash-free 
            coupling.
        .. todo:: Add a parameter to configure the size of the circular cutout between the cogs.
        .. todo:: Determine a default for clamp_lenght automatically if no measure is given.
        .. todo:: Make the 3D printer bridging distance configurable. Currently, a constant value 
            of 4 mm is used in Workplane::shaft(…, top_diameter = 4).
        """

        cq.Workplane.transformedWorkplane = utilities.transformedWorkplane
        cq.Workplane.first_solid = utilities.first_solid
        cq.Workplane.union_pending = utilities.union_pending
        cq.Workplane.difference_pending = utilities.difference_pending
        cq.Workplane.point_sector = utilities.point_sector
        cq.Workplane.shaft = utilities.shaft
        cq.Workplane.bolt_dummy = utilities.bolt_dummy

        self.model = workplane
        self.debug = False
        self.measures = measures

        # todo: Initialize missing measures with defaults.

        self.build()


    def build(self):
        m = self.measures

        # Create the coupling base.
        self.model = (
            self.model
            .tag("baseplane")
            .circle(m.diameter / 2)
            .extrude(m.base_height)
        )

        # Create the shaft cutout.
        self.model = (
            self.model
            .cut(
                cq.Workplane()
                .copyWorkplane(self.model.workplaneFromTagged("baseplane"))
                .shaft(
                    height = m.base_height - 1, # Leave 1 mm solid wall above the shaft hole.
                    diameter = m.shaft.diameter, 
                    flatten = m.shaft.flatten, 
                    top_diameter = 4 # Assume 4 mm as an FDM printer's bridging distance.
                )
            )
        )

        # Create the groove in the base for clamping the shaft.
        # todo: Create a plugin Workplane::half_slot2D() to simplify this code by cutting with 
        #   exactly the shape we need.
        self.model = (
            self.model
            # Locate the workplane center at the bottom of the coupling, so the slot cuts up from there.
            .transformedWorkplane(offset_z = - m.base_height / 2, rotate_x = -90)
            # Cut the slot to 80% of base height. Factor 2 is just because we can cut only with one 
            # half of the slot, so the total height has to be twice the height used for cutting.
            .slot2D(length = 0.8 * m.base_height * 2, diameter = m.clamp_gap, angle = 90)
            .cutThruAll()
        )

        # Create the cutouts for the clamping nuts and bolts.
        bolt_specs = dict(
            bolt_size = m.bolt.size, 
            head_size = m.bolt.head_size, 
            nut_size = m.bolt.nut_size, 
            clamp_length = m.bolt.clamp_length,
            head_length = m.diameter, # Just a surely long enough head cutter length.
            nut_length = m.diameter   # Just a surely long enough nut cutter length.
        )
        self.model = (
            self.model
            .cut(
                cq.Workplane("YZ")
                .center(
                    # Position the bolt cutout horizontally at the center of the flat space next to 
                    # the shaft cutout.
                    0.5 * m.shaft.diameter + 0.25 * (m.diameter - m.shaft.diameter),
                    # Position the bolt cutout vertically at the same distance from the bottom 
                    # that it has from the left and right of the flat internal area created by the groove.
                    0.25 * (m.diameter - m.shaft.diameter)
                )
                .bolt_dummy(**bolt_specs)
            )
            .cut(
                cq.Workplane("YZ")
                # Bolt position as for the first cut above, but mirrored at the local Y axis.
                .center(
                    -(0.5 * m.shaft.diameter + 0.25 * (m.diameter - m.shaft.diameter)),
                    0.25 * (m.diameter - m.shaft.diameter)
                )
                .bolt_dummy(**bolt_specs)
            )
        )

        # Create the coupling cogs
        self.model = (
            self.model
            .faces(">Z").workplane().tag("cog_plane")

            # Circle sectors as the base shape.
            #
            # There is an OCCT kernel issue that does not allow to extrude with the same diameter 
            # as the circle of the coupling base below. Error message is "BRep_Tool: TopoS_Vertex 
            # hasn't gp_Pnt". To solve it, we subtract 0.01.
            .polygon(nSides = m.cogs.count, diameter = m.diameter - 0.01, forConstruction = True)
            .vertices()
            .point_sector(360 / (m.cogs.count * 2) - m.cogs.gap_angle)
            .union_pending()

            # Inner circle to subtract.
            .workplaneFromTagged("cog_plane")
            .circle(0.4 * m.diameter / 2)

            # Determine the inner circle from the circle sectors, and extrude the cogs.
            .difference_pending()
            .extrude(m.cogs.height)
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

measures = Measures(
    diameter = 30,
    base_height = 24,
    clamp_gap = 1.5,
    cogs = Measures(
        count = 4, # Number of teeth on one part of the coupling, not on both together.
        height = 12,
        gap_angle = 3
    ),
    shaft = Measures(
        diameter = 8,
        flatten = 1.5
    ),
    bolt = Measures( # Rather bolthole measures, slightly larger than the bolts used.
        size = 4.3,
        head_size = 7.3,
        nut_size = 7.3, # M4 nut size is 7.0 mm.
        clamp_length = 10
    )
)
show_options = {"color": "lightgray", "alpha": 0}

spider_coupling = cq.Workplane("XY").part(SpiderCoupling, measures)
show_object(spider_coupling, name = "spider_coupling", options = show_options)
