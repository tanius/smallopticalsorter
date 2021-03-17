import cadquery as cq
import logging, importlib
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class PlateGuide:

    def __init__(self, workplane, measures):
        """
        A parametric, bracket-like guide for inserting a plate or separation wall into a case. 
        To be used pairwise. This plate guide is mounted to an orthogonal case wall. There is also 
        a variant mounted to parallel case walls – see PlateGuideSpacer.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``TODO``:** TODO

        .. todo:: Create small fillets around the edges that are plain 90° corners so far.
        .. todo:: Create a drill jig with left and right parts combined. A hot 3 mm drillbit 
            will be used with that to make holes into the case. Two versions are needed: one for 
            plates at the end, one for other plates. It should rest at the bottom of the box to 
            get a 90° angle. The plate guides themselves will not touch the bottom, though.
        .. todo:: To use less plastic and space, give the part a triangular cross-section 
            except that there would be an added cylinder at the positions of bolts. However, that 
            would make it more difficult to merge this design with PlateSpacer as intended.
        """

        cq.Workplane.fillet_if = utilities.fillet_if
        cq.Workplane.chamfer_if = utilities.chamfer_if
        cq.Workplane.nut_hole = utilities.nut_hole

        self.model = workplane
        self.debug = False
        self.measures = measures

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

        # todo: Initialize missing measures with defaults.

        self.build()


    def build(self):
        m = self.measures
        if m.type == "left":
            ramp_edge_selector = ">X"
            horizontal_fillets_edge_selector = "<Y or <X"
            vertical_fillets_edge_selector = "<X"
            mounthole_origin_selector = ">X and <Z"
            mounthole_horizontal_direction = -1
        else:
            ramp_edge_selector = "<X"
            horizontal_fillets_edge_selector = "<Y or >X"
            vertical_fillets_edge_selector = ">X"
            mounthole_origin_selector = "<X and <Z"
            mounthole_horizontal_direction = 1

        self.model = (
            self.model

            # Base shape part that is in parallel with the plate.
            .rect(m.width, m.depth)
            .extrude(m.height)
            .translate((0, - m.depth / 2, 0))

            # Remember the unmodified front face as reference for placing the holes later.
            .faces("<Y")
            .vertices(mounthole_origin_selector)
            .workplane(centerOption = "CenterOfMass")
            .tag("hole_plane")
            .end(3)

            # Ramps that help to insert the plate.
            .faces(">Z")
            .edges(ramp_edge_selector)
            .chamfer_if(m.ramp_1.enabled, length2 = m.ramp_1.width, length = m.ramp_1.height)
            .faces("<Z")
            .edges(ramp_edge_selector)
            .chamfer_if(m.ramp_2.enabled, length2 = m.ramp_2.width, length = m.ramp_2.height)

            # Hole 1 (usually the upper hole).
            .workplaneFromTagged("hole_plane")
            .center(mounthole_horizontal_direction * m.hole_1.horizontal_pos, m.hole_1.vertical_pos)
            .tag("hole_1_plane")
            .hole(m.hole_1.diameter)
            .workplaneFromTagged("hole_1_plane")
            .nut_hole(size = m.hole_1.nuthole_size, length = m.hole_1.nuthole_depth)

            # Hole 2 (usually the lower hole).
            .workplaneFromTagged("hole_plane")
            .center(mounthole_horizontal_direction * m.hole_2.horizontal_pos, m.hole_2.vertical_pos)
            .tag("hole_2_plane")
            .hole(m.hole_2.diameter)
            .workplaneFromTagged("hole_2_plane")
            .nut_hole(size = m.hole_2.nuthole_size, length = m.hole_2.nuthole_depth)

            # Fillets around the upper and lower edges (except towards back and plate).
            .faces(">Z").edges(horizontal_fillets_edge_selector)
            .fillet_if(m.fillets.upper > 0, m.fillets.upper)
            .faces("<Z").edges(horizontal_fillets_edge_selector)
            .fillet_if(m.fillets.lower > 0, m.fillets.lower)

            # Fillet around the vertical edge (the one not towards back or plate).
            .faces("<Y").edges(vertical_fillets_edge_selector)
            .fillet_if(m.fillets.vertical > 0, m.fillets.vertical)
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

# Orientation is as if looking from the center of the guided plate.

height = 100.0

# Gap between end of the part and top edge of the case.
top_edge_to_part = 20.0

# Hole position constraints so that hole_1 comes out at the center of the second-from-top 
# reinforcement rectangle on the outside of the Auer 400×300 mm boxes.
top_edge_to_hole_1 = 40.85
inner_wall_to_holes = 18.0

# Calculate max. part depth when using a given bolt.
# We want the bolt to end flush with the upper part surface in a nut.
bolt_length = 16.0 # Includes head, as this is a countersunk bolt.
bolt_head = 1.9 # M3 countersunk bolt head with 0.48 mm M4 washer, tightened.
case_wall_thickness = 2.3 # Under compression of a bolt, otherwise 2.6 - 2.8.
max_part_depth = bolt_length - bolt_head - case_wall_thickness
log.info("max_part_depth = %s", max_part_depth)

# Calculate horizontal position from the end of the part, as needed for holes in the center of the 
# reinforcement rectangles near the vertical edges of Auer 400×300 mm boxes.
wall_to_hole = 18.0 # Horizontal distance from inside surface of case wall to center of hole.
opposite_plate_guide = 5.0
plate_thickness = 5.0
plate_free_travel = 1.2
inner_wall_to_holes = wall_to_hole - opposite_plate_guide - plate_thickness - plate_free_travel
log.info("horizontal_pos = %s", inner_wall_to_holes)

measures = Measures(
    # Type does not matter, as we create a symmetric part that can be used on both sides.
    type = "right",
    width = 2 * inner_wall_to_holes, # To horizontally center the holes. Just because.
    depth = max_part_depth,
    height = height,
    fillets = Measures(
        upper = 5.5,
        vertical = 3.0,
        lower = 5.0
    ),
    ramp_1 = Measures(
        width = 5.0, # TODO: Fix that this cannot be the same as width due to a CAD kernel issue.
        height = 13.5
    ),
    ramp_2 = Measures(
        width = 5.0, # TODO: Fix that this cannot be the same as width due to a CAD kernel issue.
        height = 13.5
    ),
    hole_1 = Measures(
        horizontal_pos = inner_wall_to_holes, # From end of part near the plate surface.
        vertical_pos = height - (top_edge_to_hole_1 - top_edge_to_part), # From bottom end of part.
        diameter = 3.3,
        nuthole_size = 5.6, # 5.4 mm for a M3 nut, 0.2 mm for easy inserting.
        nuthole_depth = 3.0 # 2.3 mm for a M3 nut, and 0.7 mm for the bolt to protrude.
    ),
    hole_2 = Measures( # Same as for hole_1.
        horizontal_pos = inner_wall_to_holes,
        vertical_pos = top_edge_to_hole_1 - top_edge_to_part, # From bottom end of part.
        diameter = 3.3,
        nuthole_size = 5.6, # 5.4 mm for a M3 nut, 0.2 mm for easy inserting.
        nuthole_depth = 3.0 # 2.3 mm for a M3 nut, and 0.7 mm for the bolt to protrude.
    )
)

plate_guide = cq.Workplane("XY").part(PlateGuide, measures)

show_options = {"color": "lightgray", "alpha": 0}
show_object(plate_guide, name = "plate_guide", options = show_options)
