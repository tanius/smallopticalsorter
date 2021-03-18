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


class ShaftCoupling:

    def __init__(self, workplane, measures):
        """
        A parametric shaft coupling, for example to connect stepper motors to devices in a removable 
        way. Provides various coupling styles including (1) spider / Lovejoy coupling without a 
        rubber insert, (2) hexagonal drive profile, e.g. for bolt heads.

        **3D printing hints**

        Print at 100% infill as these couplings need quite some strength. PLA works, but PETG material 
        is better. Print with the bolts in vertical position. This will need a bit of support material, 
        but (1) the layers will now be printed so that they are flexed when clamping the bolt and 
        (2) there are circular shells around the bolthole, which is good to prevent part splitting 
        when using a countersunk bolt.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``diameter``:** Coupling diameter in mm.
            - **``base_height``:** Height of the cylindrical base of the coupling, without the cogs.
            - **``clamp_gap``:** Width of the central clamping groove in the coupling's base.
            - **``cogs.count``:** Number of cogs on each half of the coupling.
            - **``cogs.height``:** Height of the cogs above the coupling base.
            - **``cogs.gap_angle``:** Angular gap left to the left and right of each cog after 
                interlocking with their counterparts from the other half of the coupling.
            - **``shaft.diameter ``:** Diameter of the shaft hole in the bottom of the coupling.
            - **``shaft.flatten``:** Height of the arc cut off from a cull circle for shafts with 
                a D-shape cross-section.
            - **``bolts.hole_size``:** Size of the clamping bolt holes.
            - **``bolts.headhole_size``:** Hole diameter for the heads of the clamping bolts.
            - **``bolts.nuthole_size``:** Size between flats for the hexagonal hole for the nuts of 
                the clamping bolts.
            - **``bolts.clamp_length``:** Clamping length (between bolt head and nut) of the clamping 
                bolts.

        .. todo:: Fix that the cog generation code only works for 4 and 6 cogs so far.
        .. todo:: Provide a way to calculate the coupling based on bolt length as input parameter. 
            The idea is to let the bolt ends end just inside the coupling outline.
        .. todo:: Make the cogs rounded or pointed at the top so that two parts will usually 
            come together under light pressure without having to turn one manually.
        .. todo:: Add a parameter that can offset the initial rotation angle of the cogs, so that 
            the groove can go through a location with no cogs on top for better flexing.
        .. todo:: Add a parameter to also use a rubber insert, allowing to create a backlash-free 
            coupling.
        .. todo:: Add a parameter to configure the size of the circular cutout between the cogs.
        .. todo:: Determine a default for clamp_lenght automatically if no measure is given.
        .. todo:: Initialize missing measures with defaults where reasonable.
        .. todo:: Make the 3D printer bridging distance configurable. Currently, a constant value 
            of 4 mm is used in Workplane::shaft(…, top_diameter = 4).
        .. todo:: Replace using bolt() with with cbore_csk_hole() (resp. bolt_hole() when renamed) 
            and nut_hole() (which might be included in bolt_hole() later). Because these are 
            specifically meant for cutting bolt holes, while bolt() is for generating the positive 
            shape. Both are provided in utilities.py.
        .. todo:: Add a parameter for the number of rows of bolts that do the clamping. So to 
            create couplings for higher torsion, one would use three or four pairs of bolts stacked.
        """

        cq.Workplane.transformedWorkplane = utilities.transformedWorkplane
        cq.Workplane.first_solid = utilities.first_solid
        cq.Workplane.union_pending = utilities.union_pending
        cq.Workplane.difference_pending = utilities.difference_pending
        cq.Workplane.point_sector = utilities.point_sector
        cq.Workplane.shaft = utilities.shaft
        cq.Workplane.bolt = utilities.bolt
        cq.Workplane.nut_hole = utilities.nut_hole

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

            # Add a fillet around the bottom edge. Much easier to do now than later.
            .edges("<Z")
            .fillet(m.fillets)
        )

        # Create the shaft cutout as a through hole.
        # Using a through hole reduces the coupling height and also allows to push out support 
        # material easily. The design can be chosen so that the sides provide enough strength even 
        # for a clip-style single part coupling.
        self.model = (
            self.model

            # Create the shaft through hole for clamping it.
            .cut(
                cq.Workplane()
                .copyWorkplane(self.model.workplaneFromTagged("baseplane"))
                .shaft(
                    height = m.base_height,
                    diameter = m.shaft.clamping_diameter, 
                    flatten = m.shaft.flatten
                )
            )

            # Enlarge the hole in the unclamped part that allows to easily insert the shaft.
            # TODO: Calculate the effectively unclamped part better, or make it configurable. 
            # Currently, as much grooved section is considered unclamped as there is ungrooved section. 
            # That's an approximation only, to prevent splitting the part when inserting the shaft 
            # into a slightly undersized hole.
            .cut(
                cq.Workplane()
                .copyWorkplane(self.model.workplaneFromTagged("baseplane"))
                .workplane(offset = m.base_height - 2 * (m.base_height - m.clamp.groove_depth))
                .shaft(
                    height = 2 * (m.base_height - m.clamp.groove_depth),
                    diameter = m.shaft.hole_diameter, 
                    flatten = m.shaft.flatten
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
            # Cut the slot to specified depth. Factor 2 is just because we can cut only with one 
            # half of the slot, so the total height has to be twice the height used for cutting.
            .slot2D(length = m.clamp.groove_depth * 2, diameter = m.clamp_gap, angle = 90)
            .cutThruAll()
        )

        # Create the cutouts for the clamping nuts and bolts.
        bolt_specs = dict(
            bolt_size = m.bolt_holes.hole_size, 
            head_size = m.bolt_holes.headhole_size, 
            head_shape = "conical",
            head_angle = 90,
            nut_size = m.bolt_holes.nuthole_size, 
            clamp_length = m.bolt_holes.clamp_length,
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
                    0.5 * m.shaft.clamping_diameter + 0.25 * (m.diameter - m.shaft.clamping_diameter) + m.bolt_holes.radial_offset,
                    # Position the bolt cutout vertically at the same distance from the bottom 
                    # that it has from the left and right of the flat internal area created by the groove.
                    # But don't forget to add a user-defined offset.
                    0.25 * (m.diameter - m.shaft.clamping_diameter) + m.bolt_holes.vertical_offset
                    # TODO: Calculate these positions in variables and re-use them below, to reduce 
                    # redundancy.
                )
                .workplane(offset = - m.bolt_holes.depth_offset)
                .bolt(**bolt_specs)
            )
            .cut(
                cq.Workplane("YZ")
                # Bolt position as for the first cut above, but mirrored at the local Y axis.
                .center(
                    -(0.5 * m.shaft.clamping_diameter + 0.25 * (m.diameter - m.shaft.clamping_diameter) + m.bolt_holes.radial_offset),
                    0.25 * (m.diameter - m.shaft.clamping_diameter) + m.bolt_holes.vertical_offset
                )
                .workplane(offset = - m.bolt_holes.depth_offset)
                .bolt(**bolt_specs)
            )
        )

        # Create the coupler according to the style that was configured.
        if m.coupler.style == "spider":
            self.model = (
                self.model
                .faces(">Z").workplane().tag("coupler_plane")

                # Circle sectors as the base shape.
                #
                # There is an OCCT kernel issue that does not allow to extrude with the same diameter 
                # as the circle of the coupling base below. Error message is "BRep_Tool: TopoS_Vertex 
                # hasn't gp_Pnt". To solve it, we subtract 0.01.
                .polygon(nSides = m.coupler.cogs, diameter = m.diameter - 0.01, forConstruction = True)
                .vertices()
                .point_sector(360 / (m.coupler.cogs * 2) - m.coupler.gap_angle)
                .union_pending()

                # Inner circle to subtract.
                .workplaneFromTagged("coupler_plane")
                .circle(0.4 * m.diameter / 2)

                # Determine the inner circle from the circle sectors, and extrude the cogs.
                .difference_pending()
                .extrude(m.coupler.height)

                # Add small fillets at the edges of the cogs.
                .faces(">Z or <Z")
                .edges("%Circle")
                .fillet(m.fillets)
            )
        elif m.coupler.style == "hexagonal":
            self.model = (
                self.model
                
                # TODO: Instead of the code below, extrude the existing face by converting it into 
                # a wire first. It is not yet clear how to do that, though.
                .faces(">Z")
                .workplane()
                .circle(m.diameter / 2)
                .extrude(m.coupler.height + m.fillets)
                
                .faces(">Z")
                .workplane()
                .nut_hole(size = m.coupler.size, length = m.coupler.height + m.fillets)

                .edges(">Z").fillet(m.fillets)
            )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

# Measures for a low-profile stepper motor coupling with 5 mm round shaft. M3×20 countersunk bolts 
# are fitting just inside the part outline. To achieve good clamping strength with just two bolts 
# and without splitting the parts (even though using countersunk bolts), a large diameter is used.

measures = Measures(
    diameter = 25.0,
    base_height = 16.0,
    clamp_gap = 1.2, # Enough, as measured decrease by clamping is 0.5 mm for a 20 mm diameter part.
    fillets = 1.25, # Default for filleted edges, if nothing more specific is found in other parameters.
    shaft = Measures(
        # Diameter for holes without a clamp. The shaft should be insertable easily, not creating 
        # any splitting force for the part. 5.3 is good for a shaft diameter of 5.0 mm.
        hole_diameter = 5.3,
        # Diameter for holes with the clamp mechanism. Usually use the exact shaft diameter here.
        # This also applies for the clip-style clamping mechanism. There will be some printer 
        # artefacts that push the clamping clip slightly outwards, but this is undone when fastening 
        # it. It ideally leads to a clamp having the configured part diameter along its whole length, 
        # because that results in the least internal stress (and thus, no part splitting).
        clamping_diameter = 5.00,
        flatten = 0.0
    ),
    clamp = Measures(
        style = "clip", # "clip" or (later) "two parts"
        groove_depth = 14.0
    ),
    bolt_holes = Measures(
        clamp_length = 14.5, # The cylindrical section of the bolt between head and nut.
        hole_size = 3.2, # Good for M3 and some printer artefacts.
        nuthole_size = 5.8, # 5.4 mm for a M3 nut, 0.4 mm for easy inserting. Corrected from 0.2.
        headhole_size = 6.3, # 6.1 for a DIN 7991 M3 countersunk bolt head, 0.2 for easy assembly.
        head_angle = 90, # DIN 7991 countersunk bolt. Cone tip angle. Omit to use a bolt with cylindrical head.
        # Manual offset from default position radially centered in the available space.
        # Moving the bolts towards the center like here can help to compensate that in its default 
        # position there is more material around a bolt towards the center. We better distribute 
        # that material to prevent part splitting equally well on all sides.
        radial_offset = -2.25,
        # Manual offset from default position near the end of the clamping groove.
        vertical_offset = 2.0,
        # Manual offset from default position in the depth direction. Bolt direction is positive.
        #  The default is to position the bolt so that half the bolt's cylindrical part between 
        # head and nut (see clamp_length) is half above and half below the workplane. You can adjust 
        # this to hide both nut and bolt head just inside the coupling outline.
        #  The right value for M3 bolts is to keep 0.35 mm of cylindrical hole depth at the inlet of 
        # the bolt hole (measured where the wall height is lowest). Not more, as this guarantees 
        # that the bolt head is only just inside the part outline. This applies when a M3 hole is 
        # configured for countersunk bolts using headhole_size = 6.3, head_angle = 90.
        depth_offset = -0.1
    ),
    coupler = Measures(
        # Coupling with a hexagonal drive profile for M5 hex bolts.
        # Using measures from ISO 4017 / DIN 933 and ISO 4014 / DIN 931. For couplings that should be 
        # short, interlocking with a hex bolt like this is preferable to a spider coupling. Also, 
        # it is one part less to 3D print, as this coupling type needs simply a bolt as counterpart.
        style = "hexagonal",
        height = 3.5, # Excludes filleted height added automatically on top.
        size = 8.4, # 8.0 mm wrench size, 0.4 mm for coupler play and easy inserting.

        # Example for a spider coupling. Suitably sized for NEMA17 stepper motors.
        # style = "spider", # "spider" / "hexagonal"
        # height = 6.0,
        # cogs = 4, # Can only be 4 or 6 so far due to a bug.
        # gap_angle = 3
    ),
)
show_options = {"color": "lightgray", "alpha": 0.0}

shaft_coupling = cq.Workplane("XY").part(ShaftCoupling, measures)
show_object(shaft_coupling, name = "shaft_coupling", options = show_options)
