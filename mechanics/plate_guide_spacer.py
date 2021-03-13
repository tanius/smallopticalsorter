import cadquery as cq
import logging, importlib
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class PlateGuideSpacer:

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

        .. todo:: Add parameters for a grid with multiple rows and columns of mount holes, and 
            parameters to position them.
        """

        cq.Workplane.fillet_if = utilities.fillet_if

        self.model = workplane
        self.debug = False
        self.measures = measures

        # todo: Initialize missing measures with defaults.

        self.build()


    def build(self):
        m = self.measures
        if m.type == "left":
            initial_position = (- m.width / 2, 0)
            funnel_edge_selector = ">X"
            case_edge_selector = "<X"
            mounthole_face_selector = ">X"
        else:
            initial_position = (m.width / 2, 0)
            funnel_edge_selector = "<X"
            case_edge_selector = ">X"
            mounthole_face_selector = "<X"

        self.model = (
            self.model

            # Base shape.
            .rect(m.width, m.depth)
            .extrude(m.height)
            .translate(initial_position)

            # Guides that help like a funnel to insert the plate.
            .faces(">Z")
            .edges(funnel_edge_selector)
            # TODO: Better use chamfer_if() to allow a zero chamfer.
            .chamfer(length2 = m.insert_funnel.width, length = m.insert_funnel.height)

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
            .workplane(centerOption = "CenterOfMass")
            .cskHole(
                diameter = m.hole.diameter, 
                cskDiameter = m.hole.head_diameter, 
                cskAngle = m.hole.head_angle
            )
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

# Orientation is as if looking from the center of the guided plate.

measures = Measures(
    type = "left",
    width = 5.0,
    depth = 12.5,
    height = 35.0,
    corner_radius = Measures(
        upper = 5.0,
        case = 3.0,
        lower = 0.0
    ),
    insert_funnel = Measures(
        width = 4.99, # TODO: Fix that this cannot be the same as width due to a CAD kernel issue.
        height = 15.0
    ),
    hole = Measures(
        diameter = 3.3,
        # To make sure the bolt head is out of the way when inserting the plate, we make a bit 
        # larger and deeper hole than needed. 6.0 mm diameter would be needed for M3 bolts with 
        # countersunk head, DIN 7991.
        head_diameter = 6.2,
        head_angle = 90 # As per DIN 7991 for M20 and smaller.
    ),
)
show_options = {"color": "lightgray", "alpha": 0}

plate_guide_spacer = cq.Workplane("XY").part(PlateGuideSpacer, measures)
show_object(plate_guide_spacer, name = "plate_guide_spacer", options = show_options)
