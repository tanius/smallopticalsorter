import cadquery as cq
import logging, importlib
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class PlateSpacer:

    def __init__(self, workplane, measures):
        """
        A parametric, spacer-style guide for inserting a plate or separation wall into a case. 
        To be used pairwise. This plate guide is mounted to a parallel case wall. There is also 
        a variant mounted to orthogonal case walls – see PlateGuideBracket.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``TODO``:** TODO

        .. todo:: Once we have a way to cut bolts to custom lengths, embed the nut into the 
            spacer and run a custom length bolt through the case wall so that it ends just flush 
            with the spacer's surface. That way, all bolts go into the case, with no nuts visible 
            on the outside. Also, no wrench is needed for assembly then. However, the current 
            solution of counterbored and countersunk holes is also quite nice, and allows to use 
            a standard 10 mm bolt with the chosen case.
        .. todo:: Add parameters for a grid with multiple rows and columns of mount holes, and 
            parameters to position them.
        """

        cq.Workplane.fillet_if = utilities.fillet_if
        cq.Workplane.chamfer_if = utilities.chamfer_if
        cq.Workplane.cbore_csk_hole = utilities.cbore_csk_hole

        self.model = workplane
        self.debug = False
        self.measures = measures

        # todo: Initialize missing measures with defaults.

        # Give the hole position a meaning as coordinates when using the plane to drill the hole 
        # in as the coordinate system.
        if measures.type == "left" and measures.hole.horizontal_pos > 0:
            measures.hole.horizontal_pos *= -1

        # Add parameters to easily check if a ramp should be added.
        if (hasattr(measures.ramp_1, "width") and measures.ramp_1.width > 0 and
            hasattr(measures.ramp_1, "height") and measures.ramp_1.height > 0
        ):
            measures.ramp_1.enabled = True
        else:
            measures.ramp_1.enabled = False
            measures.ramp_1.width = None
            measures.ramp_1.height = None

        if (hasattr(measures.ramp_2, "width") and measures.ramp_2.width > 0 and
            hasattr(measures.ramp_2, "height") and measures.ramp_2.height > 0
        ):
            measures.ramp_2.enabled = True
        else:
            measures.ramp_2.enabled = False
            measures.ramp_2.width = None
            measures.ramp_2.height = None

        self.build()


    def build(self):
        m = self.measures
        if m.type == "left":
            initial_position = (- m.width / 2, 0)
            ramp_edge_selector = ">X"
            case_edge_selector = "<X"
            mounthole_face_selector = ">X"
            mounthole_origin_offset = (m.depth / 2, 0)
        else:
            initial_position = (m.width / 2, 0)
            ramp_edge_selector = "<X"
            case_edge_selector = ">X"
            mounthole_face_selector = "<X"
            mounthole_origin_offset = (-m.depth / 2, 0)

        self.model = (
            self.model

            # Base shape.
            .rect(m.width, m.depth)
            .extrude(m.height)
            .translate(initial_position)

            # Ramps that help to insert the plate.
            .faces(">Z")
            .edges(ramp_edge_selector)
            .chamfer_if(m.ramp_1.enabled, length2 = m.ramp_1.width, length = m.ramp_1.height)
            .faces("<Z")
            .edges(ramp_edge_selector)
            .chamfer_if(m.ramp_2.enabled, length2 = m.ramp_2.width, length = m.ramp_2.height)

            # Edge fillet for fitting into the corner of the case.
            .faces(">Y")
            .edges(case_edge_selector)
            .fillet_if(m.corner_radius.case > 0, m.corner_radius.case)

            # Add corner radii to the upper and lower corners.
            .faces(">Z").edges("<Y")
            .fillet_if(m.corner_radius.upper > 0, m.corner_radius.upper)
            .faces("<Z").edges(">Y")
            .fillet_if(m.corner_radius.lower > 0, m.corner_radius.lower)

            # Mount holes.
            .faces(mounthole_face_selector)
            .workplane()
            .center(*mounthole_origin_offset) # Move origin to reference position in the lower back corner.
            .tag("mounthole_plane")
            .center(m.hole_1.horizontal_pos, m.hole_1.vertical_pos) # Measure hole position from reference.
            .cbore_csk_hole(
                diameter = m.hole_1.diameter,
                cboreDiameter = m.hole_1.head_diameter,
                cboreDepth = m.hole_1.counterbore_depth,
                cskDiameter = m.hole_1.head_diameter, 
                cskAngle = m.hole_1.head_angle
            )
            .workplaneFromTagged("mounthole_plane")
            .center(m.hole_2.horizontal_pos, m.hole_2.vertical_pos) # Measure hole position from reference.
            .cbore_csk_hole(
                diameter = m.hole_2.diameter,
                cboreDiameter = m.hole_2.head_diameter,
                cboreDepth = m.hole_2.counterbore_depth,
                cskDiameter = m.hole_2.head_diameter, 
                cskAngle = m.hole_2.head_angle
            )
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

# Variable names refer to a part orientation as if looking from the center of the guided plate 
# towards the part, with the top of the guide plate being the edge inserted last.

height = 100.0

# Gap between end of the part and top edge of the case.
top_edge_to_part = 20.0

# Hole position constraints so that hole_1 comes out at the center of the second-from-top 
# reinforcement rectangle on the outside of the Auer 400×300 mm boxes.
top_edge_to_hole_1 = 40.85
inner_wall_to_holes = 18.0

head_diameter = 6.1 # A DIN 7991 M3 countersunk bolt head is 6.1 mm in diameter.
head_hole_additional_radius = 0.2 # Chosen for comfortable mounting.
head_hole_diameter = 6.1 + 2 * head_hole_additional_radius
# With a 90° countersink head angle like here, increasing the hole radius sinks in the bolt head 
# by the same amount. (Oberve the 45-90-45 triangle between head center, hole radius and cone tip.)
countersink_excess_depth = head_hole_additional_radius

# A counterunk DIN 7991 M3 bolt has a 0.6 mm thick cylindrical section at the very top of its head.
# To sink this in, you either need a counterbore hole and / or a deeper countersink hole.
head_cylindrical_height = 0.6
head_to_surface = 1.0 # Intended depth of sinking the head below the surface of the hole.
counterbore_depth = head_to_surface + head_cylindrical_height - countersink_excess_depth

measures = Measures(
    # Type does not matter, as we create the part symmetrical so that it can be used on both sides.
    type = "right", # Means right side of plate, not right side of case.
    width = 5.0,
    depth = 25.0,
    height = height,
    corner_radius = Measures(
        # No upper corner radius here, as that corner is flat against a wall and won't hurt anyone.
        # And without that corner radius, printing it with its front face down becomes possible.
        upper = 0.0,
        case = 4.5, # Best value. Tested: 3.0, 4.0, 4.5, 4.99.
        lower = 0.0
    ),
    ramp_1 = Measures(
        width = 4.99, # TODO: Fix that this cannot be the same as width due to a CAD kernel issue.
        height = 13.5
    ),
    ramp_2 = Measures(
        width = 4.99, # TODO: Fix that this cannot be the same as width due to a CAD kernel issue.
        height = 13.5
    ),
    hole_1 = Measures(
        diameter = 3.3,
        horizontal_pos = inner_wall_to_holes,
        vertical_pos = height - (top_edge_to_hole_1 - top_edge_to_part), # From bottom end of part.
        head_diameter = head_hole_diameter,
        head_angle = 90, # As per DIN 7991 for M20 and smaller.
        counterbore_depth = counterbore_depth
    ),
    # hole_2 is symmetrical to hole_1, to make this part usable for both right and left.
    hole_2 = Measures(
        diameter = 3.3,
        horizontal_pos = inner_wall_to_holes, # From case wall surface.
        vertical_pos = top_edge_to_hole_1 - top_edge_to_part, # From bottom end of part.
        head_diameter = head_hole_diameter,
        head_angle = 90,
        counterbore_depth = counterbore_depth
    )
)
show_options = {"color": "lightgray", "alpha": 0}

plate_spacer = cq.Workplane("XY").part(PlateSpacer, measures)
show_object(plate_spacer, name = "plate_spacer", options = show_options)

# 3D printing hints:
# Print with the ramp facing down. That way, you'll need support for the ramp, but no support for 
# the edge fillet. The latter would not work well, as support for very low overhangs cannot be 
# provided, leading to a not-very-round fillet.