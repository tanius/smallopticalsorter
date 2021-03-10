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
            - **``shovel.size``:** Width of the shovel's opening.
            - **``shovel.height``:** Height of the shovel.
            - **``shovel.cavity``:** Depth of the deepest part of the shovel, measured to a line 
                connecting its edges.
            - **``shovel.inclination``:** Angle in radial direction against vertical. Positive 
                angle lean towards the center, negative away from it.

        .. todo:: Add the shaft mount.
        .. todo:: Use rectangular through-holes for dropping in nuts into the right half of the 
            shaft collar. Less fiddly than hexagonal holes from the back. And removing less material.
        .. todo:: Move calculations of derived measures into the initializer.
        .. todo:: Fix that the upper wire of the shovels does not reach in radially inside as much as 
            it should. That is because it is drawn on an inclined plane, which shortens its 
            effective radial length. When placing a cylinder into the center that should fill the 
            space, there is no gap to the shovels at the bottom, but at the top there is.
        .. todo:: Change the orientation of the part by rotating it 90° on the z axis. That will 
            give proper meanings to the measures nuthole_width, nuthole_depth, nuthole_depth_position.
            However, maybe the measures should not refer to the global part orientation, cf. 
            "depth of a hole", which is always a local measure. In that case, rename the measures.
        """

        cq.Workplane.distribute_circular = utilities.distribute_circular
        cq.Workplane.angle_sector = utilities.angle_sector
        cq.Workplane.shaft_outline = utilities.shaft_outline
        cq.Vector.toTuple2D = utilities.toTuple2D

        self.baseplane = workplane # To keep a re-usable reference to an unmodified workplane.
        self.debug = False
        self.measures = measures

        # To distribute part strength evenly, distribute block thickness and embedding depth of the 
        # nuts in the collar counterpart using a 60:40 ratio. Because for the counterpart, the 
        # intact back of the part also contributes to bend stiffness an breaking strength.
        self.measures.shaft.clamp_block_thickness = \
            0.6 * (self.measures.bolts.clamp_length - self.measures.shaft.clamp_gap)
        self.measures.bolts.nuthole_depth_position = \
            0.4 * (self.measures.bolts.clamp_length - self.measures.shaft.clamp_gap)

        # TODO: Initialize missing measures with defaults.

        self.build()


    def build_collar(self, half = "right", clamp_gap = 0.0):
        m = self.measures
        outer_r = m.shaft.collar_outer_diameter / 2
        inner_r = m.shaft.collar_inner_diameter / 2
        clamp_gap_offset = clamp_gap if half == "right" else -clamp_gap
        # Due to a bug in utilities.angle_sector, the numerically smaller angle is always used as 
        # the start angle. So for the right half, we have to express it as a negative number instead 
        # of as 270.
        start = -90 if half == "right" else  90
        stop =   90 if half == "right" else 270

        result = (
            # Cylindrical bottom of the collar.
            self.baseplane
            .workplane(offset = m.baseplate.thickness)
            .tag("collar_bottom")
            .angle_sector(radius = outer_r, start_angle = start, stop_angle = stop)
            .extrude(m.shaft.collar_outer_height)

            # Conical top of the collar.
            .faces(">Z").wires().toPending()
            .workplane(offset = m.shaft.collar_inner_height - m.shaft.collar_outer_height)
            .angle_sector(radius = inner_r, start_angle = start, stop_angle = stop)
            .loft()

            # Cut out the shaft hole.
            .workplaneFromTagged("collar_bottom")
            .shaft_outline(diameter = m.shaft.diameter, flatten = m.shaft.flatten)
            .cutThruAll()

            # Cut off space for the clamp gap.
            .transformed(offset = (clamp_gap_offset, 0, 0), rotate = (0, -90, 0))
            #.box(100, 100, 1)
            .split(
                keepBottom = True if  half == "right" else False,
                keepTop    = False if half == "right" else True
            )

            # Bolt holes.
            .workplaneFromTagged("collar_bottom")
            # TODO: Change the workplane transformation so that the global y axis is the x axis of 
            # the resulting workplane. That allows to switch the coordinates in moveTo() to the 
            # intuitive order.
            .transformed(rotate = (0, -90, 0))
            .moveTo(m.bolts.hole_position_vertical, m.bolts.hole_position_radial)
            .circle(m.bolts.hole_size / 2)
            .moveTo(m.bolts.hole_position_vertical, - m.bolts.hole_position_radial)
            .circle(m.bolts.hole_size / 2)
            .cutThruAll()
        )

        return result


    def build_shovel(self):
        """
        Create a single shovel.
        
        The origin is located at its outer edge, centered between the opposiong shovel cavities, 
        on the bottom face of the object, and so that the shovel openings point towards +y and -y.

        :return: A Cadquery Workplane object with a solid on the stack representing the shovel.
        """

        def shovel_profile(self, m):
            width = m.shovels.size
            # Since the two arcs are at an angle (see center_angle_rad), the minimum thickness 
            # is less than m.shovels.cavity. TODO: Make this parametric in a reasonable way.
            depth = m.shovels.cavity * 2 - 3.0
            circumradius = m.baseplate.diameter / 2
            # Angle at which the outer extension of the shovel appears from the baseplate center.
            # TODO: Make the center angle configurable in a reasonable way. Currently it is 
            # derived from the number of shovels using a statis factor (0.45).
            center_angle_rad = radians(360 / m.shovels.count) * 0.45

            # Profile corner points.
            left_bottom = cq.Vector((-width, -depth / 2))
            right_bottom = (
                (cq.Vector((circumradius, 0)) * -1)
                + (cq.Vector(cos(center_angle_rad / 2), -sin(center_angle_rad / 2)) * circumradius)
            )
            right_center = cq.Vector((0, 0))
            right_top = (
                cq.Vector((circumradius, 0)) * -1
                + cq.Vector(cos(center_angle_rad / 2), sin(center_angle_rad / 2)) * circumradius
            )
            left_top = cq.Vector((-width, depth / 2))

            profile = (
                self
                .moveTo(left_bottom.x, left_bottom.y)
                .sagittaArc(right_bottom.toTuple2D(), m.shovels.cavity)
                .threePointArc(right_center.toTuple2D(), right_top.toTuple2D())
                .sagittaArc(left_top.toTuple2D(), m.shovels.cavity)
                .close()
            )

            return self.newObject(profile.objects)

        cq.Workplane.shovel_profile = shovel_profile
        m = self.measures

        return (
            cq.Workplane("XY") # TODO: Rather use the workplane passed in through self.baseplane.
            # Draw the lower wire.
            .shovel_profile(m)

            # Draw the upper_wire.
            # TODO: Make the x offset parametric. It can be used to make the shovels protrude 
            # over the baseplate, so that they are pointing straight down if the baseplate is 
            # mounted at an angle. It also means that the diverter wheel needs more space and that 
            # the shovels cannot align with the belt side walls perfectly because they are 
            # inclined now.
            .transformed(rotate = (0, m.baseplate.inclination, 0), offset = (0, 0, m.shovels.height))
            .shovel_profile(m)

            .loft(combine = True)
            .faces(">Z")
            .fillet(1.5)
        )

    def build_wheel(self):
        m = self.measures
        nutholes_offset = m.bolts.nuthole_depth_position + 0.5 * m.bolts.nuthole_depth

        result = (
            self.baseplane
            .circle(m.baseplate.diameter / 2)
            .extrude(m.baseplate.thickness)

            # Create the shaft collar (resp. half of it, as it's split for clamping).
            .faces(">Z")
            .workplane()
            .tag("baseplate_topface")
            .union(self.build_collar(half = "right"))

            # Cut the shaft hole.
            .workplaneFromTagged("baseplate_topface")
            .shaft_outline(diameter = m.shaft.diameter, flatten = m.shaft.flatten)
            .cutThruAll()

            # Cut the nut holes.
            # TODO: This should be better in build_collar() but cannot because it also has to cut 
            #   through the baseplate. Maybe rename to build_base() or transform to a plugin that 
            #   will both add the collar and cut the holes.
            .workplaneFromTagged("collar_bottom") # Comes from build_collar() above.
            .moveTo(nutholes_offset, m.bolts.hole_position_radial)
            .rect(m.bolts.nuthole_depth, m.bolts.nuthole_width)
            .moveTo(nutholes_offset, -m.bolts.hole_position_radial)
            .rect(m.bolts.nuthole_depth, m.bolts.nuthole_width)
            .cutThruAll()

            # Add the shovels.
            .workplaneFromTagged("baseplate_topface")
            .distribute_circular(
                self.build_shovel(),
                # To prevent CAD kernel issues when union'ing everything together, the shovel's 
                # outer arc should not be coincident with the baseplate arc. We offset the shovel 
                # by 0.01 mm to the inside to guarantee that.
                radius = m.baseplate.diameter / 2 - 0.1,
                copies = m.shovels.count,
                align = "center"
            )
        )
        return result


    def build_clamp_block(self):
        m = self.measures

        result = (
            self.baseplane
            .union(self.build_collar(half = "left", clamp_gap = m.shaft.clamp_gap))

            # Create a plain surface for the boltheads.
            .workplaneFromTagged("collar_bottom")
            .transformed(offset = (-m.shaft.clamp_gap - m.shaft.clamp_block_thickness, 0, 0), rotate = (0, -90, 0))
            .split(keepBottom = True)
        )
        return result


    def build(self):
        self.wheel = self.build_wheel()
        self.clamp_block = self.build_clamp_block()

        self.model = (
            self.baseplane
            .union(self.wheel)
            .union(self.clamp_block)
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

# True to be able to export everything in a single STEP file. False to be able to selectively show 
# and hide objects in cq-editor and be able to export them to one STEP file each.
union_results = False

measures = Measures(
    baseplate = Measures(
        diameter = 90.0,
        thickness = 3.0,
        inclination = 22.5
    ),
    shovels = Measures(
        count = 6,
        height = 30.0,
        size = 18.0,
        cavity = 4.0
    ),
    shaft = Measures(
        diameter = 5.0,
        flatten = 0.01, # TODO: Fix that this cannot be 0 due to a bug in utilities.shaft_shape.
        collar_outer_diameter = 54.0,
        collar_inner_diameter = 8.0,
        collar_outer_height = 6.5,
        collar_inner_height = 15.0,
        clamp_gap = 1.5
    ),
    bolts = Measures(
        hole_size = 3.2,
        hole_position_radial = 13.5,
        hole_position_vertical = 4.0,
        headhole_size = 5.65,
        nuthole_width = 5.65, # M3 nut size between flats is 5.5 mm.
        nuthole_depth = 2.45, # M3 nut height is 2.3 mm.
        clamp_length = 25.0 # Good for using M3×15 bolts.
    )
)
show_options = {"color": "lightgray", "alpha": 0}

if union_results:
    diverter = cq.Workplane("XY").part(Diverter, measures)
    show_object(diverter, name = "diverter", options = show_options)
else:
    # Create the model as a Diverter object to get access to its parts.
    diverter = Diverter(cq.Workplane("XY"), measures)    
    show_object(diverter.wheel, name = "diverter_wheel", options = show_options)
    show_options = {"color": "orange", "alpha": 0}
    show_object(diverter.clamp_block, name = "diverter_clamp_block", options = show_options)
