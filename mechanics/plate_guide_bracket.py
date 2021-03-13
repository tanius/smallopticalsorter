import cadquery as cq
import logging, importlib
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class PlateGuideBracket:

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
        """

        cq.Workplane.bracket = utilities.bracket
        cq.Workplane.fillet_if = utilities.fillet_if

        self.model = workplane
        self.debug = False
        self.measures = measures

        # todo: Initialize missing measures with defaults.

        self.build()


    def build(self):
        m = self.measures
        if m.type == "left":
            bracketplane_offset_distance = (- m.guide_thickness / 2, 0, m.height / 2)
            bracketplane_offset_angle = (0, -90, 0) 
            funnel_edge_selector = ">X"
            corner_edge_selector = "<Y or <X"
        else:
            bracketplane_offset_distance = (m.guide_thickness / 2, 0, m.height / 2)
            bracketplane_offset_angle = (0, 90, 0)
            funnel_edge_selector = "<X"
            corner_edge_selector = "<Y or >X"

        self.model = (
            self.model

            # Create the base shape part that is in parallel with the plate.
            .rect(m.guide_thickness, m.depth)
            .extrude(m.height)
            .translate((0, - m.depth / 2, 0))

            # Cut the guides that help like a funnel to insert the plate.
            .faces(">Z")
            .edges(funnel_edge_selector)
            # TODO: Better use chamfer_if() to allow a zero chamfer.
            .chamfer(length2 = m.insert_funnel.width, length = m.insert_funnel.height)

            # Create the wall mount bracket.
            .transformed(offset = bracketplane_offset_distance, rotate = bracketplane_offset_angle)
            .bracket(
                thickness = m.bracket_thickness,
                height = m.width - m.guide_thickness,
                width = m.height,
                offset = m.holes.vertical_offset,
                hole_count = m.holes.count,
                hole_diameter = m.holes.diameter,
                edge_fillet = m.profile_fillet
            )

            # Add corner radii to the upper and lower corners.
            # (Not done via bracket() as we need different radii for the upper and lower corners.)
            .faces(">Z").edges(corner_edge_selector)
            .fillet_if(m.corner_radius.upper > 0, m.corner_radius.upper)
            .faces("<Z").edges(corner_edge_selector)
            .fillet_if(m.corner_radius.lower > 0, m.corner_radius.lower)
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

# Orientation is as if looking from the center of the guided plate.

measures = Measures(
    type = "left",
    width = 20.0,
    depth = 12.5,
    height = 35.0,
    guide_thickness = 5.0,
    bracket_thickness = 3.0,
    profile_fillet = 5.0,
    corner_radius = Measures(
        upper = 5.0,
        lower = 0.0
    ),
    holes = Measures(
        count = 2,
        diameter = 3.3,
        vertical_offset = 7.5
    ),
    insert_funnel = Measures(
        width = 3.0,
        height = 15.0
    ),
)
show_options = {"color": "lightgray", "alpha": 0}

plate_guide_bracket = cq.Workplane("XY").part(PlateGuideBracket, measures)
show_object(plate_guide_bracket, name = "plate_guide_bracket", options = show_options)
