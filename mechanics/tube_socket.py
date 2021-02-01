import cadquery as cq
from cadquery import selectors
import logging
import importlib
from math import sqrt, cos, sin, asin, acos, degrees, radians
from types import SimpleNamespace as Measures
import utilities # Local directory import.
import wall_insert # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)
importlib.reload(wall_insert)

# In addition to importing whole packages as neededfor importlib.reload(), import some names.
from wall_insert import WallInsert

# Register imported CadQuery plugins.
cq.Workplane.part = utilities.part
cq.Workplane.boxAround = utilities.boxAround
cq.Workplane.multistep_cone = utilities.multistep_cone
cq.Workplane.splitcut = utilities.splitcut

log = logging.getLogger(__name__)


class TubeSocket:

    def __init__(self, workplane, measures):
        """
        A parametric tube socket embedded into a wall, and flush with its outside.
        
        The parameters allow to make this a socket for EN 1451 wastewater tubes.

        :param workplane: The CadQuery workplane to create the chute on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``shell_thickness``:** Shell thickness of the tube element.
            - **``length_before_wall``:** How long the tube sticks out from the wall at the 
                input side. Measured along the tube center line to the surface of the wall before 
                tilting the tube (i.e. while it is vertical to the wall). Defaults to ``0``.
            - **``length_after_wall``:** How long the tube sticks out from the wall at the 
                output side. Measured along the tube center line to the surface of the wall before 
                tilting the tube (i.e. while it is vertical to the wall). Defaults to ``0``.
            - **``angle``:** The angle of the tube, measured in a vertical plane, 
                relative to going straight through the wall. 0° is straight, positive angles lift 
                the entry opening. This corresponds to the default rotation direction ("rotating 
                the y axis towards the z axis"). Defaults to ``0``.
            - **``transition_pos``:** Center of the section where the tube diameter changes between 
                the input and output diameters.
            - **``transition_length``:** Length of the section where the tube diameter changes 
                between the input and output diameters.
            - **``input.inner_diameter``:** Inner diameter of the tube at the input side.
            - **``input.cut_angle``:** The angle of the plane cutting the tube on the 
                input side, measured in a vertical plane, relative to a simple straight cut of 
                the tube end. Positive rotation direction is like rotating y axis towards z. 
                Defaults to ``0``.
            - **``output.inner_diameter``:** Inner diameter of the tube at the output side.
            - **``output.cut_angle``:** Like ``input_cut_angle_vertical`` but for the 
                exit side.
            - **``seal_cavity``:** Measures group to create a cavity for a sealing ring in the tube. 
                Omit to not create a seal cavity.
            - **``seal_cavity.position``:** 0 means "one ``shell_thickness`` away from the tube input".
            - **``seal_cavity.depth``:** Defines the depth of the seal cavity.
            - **``seal_cavity.inner_diameter``:** Defines the inner diameter of the seal cavity.
            - **``wall.thickness``:** Thickness of the tube socket's integrated wall element.
            - **``wall.groove_width``:** Thickness of the panel elements to be inserted into the 
                tube socket's integrated wall element.
            - **``wall.groove_depth``:** How to deep to cut the grooves around the tube socket's 
                integrated wall element.
            - **``wall.grooves``:** Where to create grooves around the tube socket's integrated 
                wall element. A Dict with elements "left", "right", "top", "bottom", each with a 
                Boolean value. Values not supplied default to ``False``.

        .. todo:: Add fillets to the edges where the tube goes through the wall.
        .. todo:: Add parameters to round the edges of the input and output tube ends.
        .. todo:: Add parameters for minimum wall height and width (including grooves). That also 
            will require parameters to determine the position of the wall insert.
        .. todo:: Add parameters that allow a horizontal tube angle in addition to the vertical one.
        .. todo:: Add parameters that allow horizontal tube end cutting angles in addition to the 
            vertical ones. However, probably that's never needed in practice.
        """

        self.model = workplane
        self.debug = False
        self.measures = measures

        # Adaptation to count length before / after wall from the wall surface, not from the wall center.
        self.measures.length_before_wall += self.measures.wall.thickness / 2
        self.measures.length_after_wall += self.measures.wall.thickness / 2

        self.measures.length = \
            self.measures.length_before_wall + self.measures.length_after_wall

        self.measures.input.outer_diameter = self.measures.input.inner_diameter + 2 * self.measures.shell_thickness
        self.measures.output.outer_diameter = self.measures.output.inner_diameter + 2 * self.measures.shell_thickness

        # Add optional measures if missing, using their default values.
        # todo: Create a utility function for this using getattr() internally, called like this: 
        #   self.measures = fill_defaults(self.measures, Measures(…)).
        if not hasattr(measures, 'length_before_wall'):      measures.length_before_wall = 0
        if not hasattr(measures, 'length_after_wall'):       measures.length_after_wall = 0
        if not hasattr(measures, 'horizontal_angle'):        measures.horizontal_angle = 0
        if not hasattr(measures, 'angle'):                   measures.angle = 0
        if not hasattr(measures, 'transition_pos'):          measures.transition_pos = measures.length / 2
        if not hasattr(measures, 'transition_length'):       measures.transition_pos = measures.shell_thickness
        if not hasattr(measures.input, 'cut_angle'):         measures.input.cut_angle = 0
        if not hasattr(measures.output, 'cut_angle'):        measures.output.cut_angle = 0
        if not hasattr(measures, 'seal_cavity'):             measures.seal_cavity = None
        if not hasattr(measures.wall, 'grooves'):            measures.wall.grooves = Measures()
        if not hasattr(measures.wall.grooves, 'left'):       measures.wall.grooves.left = False
        if not hasattr(measures.wall.grooves, 'right'):      measures.wall.grooves.right = False
        if not hasattr(measures.wall.grooves, 'top'):        measures.wall.grooves.top = False
        if not hasattr(measures.wall.grooves, 'bottom'):     measures.wall.grooves.bottom = False
        
        self.build()


    def build(self):
        m = self.measures
        debug_appearance = {"color": "orange", "alpha": 0.5}

        # Create the tube as a solid (with no hole and no rotation).
        # todo: Modify to create a solid with different input and output diameters.
        vertical_tube_solid = (
            cq.Workplane("XY")
            .multistep_cone((
                (0, m.output.outer_diameter / 2), 
                (m.length - m.transition_pos - m.transition_length / 2, m.output.outer_diameter / 2),
                (m.transition_length, m.input.outer_diameter / 2),
                (m.transition_pos - m.transition_length / 2, m.input.outer_diameter / 2)
            ))
            .faces(">Z or <Z").tag("end_faces").end()
        )
        if not m.seal_cavity is None:
            vertical_tube_solid = vertical_tube_solid.union(
                # Seal cavity.
                # todo: Give slightly inclined outside walls to the seal cavity.
                cq.Workplane("XY")
                .circle(m.seal_cavity.inner_diameter / 2 + m.shell_thickness)
                .extrude(m.seal_cavity.depth + 2 * m.shell_thickness)
                .translate((0, 0, m.length - m.seal_cavity.depth - 2 * m.shell_thickness - m.seal_cavity.position))
            )
        if self.debug: show_object(vertical_tube_solid, name = "DEBUG: vertical_tube_solid", options = debug_appearance)
        if self.debug: show_object(vertical_tube_solid.faces(tag = "end_faces"), name = "DEBUG: vertical_tube_solid: end_faces", options = {"color": "red"})

        # Create the hollow tube (with no rotation).
        vertical_tube = vertical_tube_solid.faces(tag = "end_faces").shell(-m.shell_thickness)
        if self.debug: show_object(vertical_tube, name = "DEBUG: vertical_tube", options = debug_appearance)

        # Cut the specified angle to input of the tube. (Much easier before rotating the tube.)
        vertical_tube = (
            vertical_tube
            .faces(">Z")
            .transformedWorkplane(
                # We need to add 0.01 to not cut exactly through the tube edge, as that confuses the 
                # splitcut() method, making it return both parts.
                offset = (0, m.input.outer_diameter / 2 * (1 if m.input.cut_angle > 0 else -1) + 0.01, 0),
                rotate_x = m.input.cut_angle
            )
            .splitcut(keepBottom = True)
        )

        # Cut the specified angle to output of the tube.
        vertical_tube = (
            vertical_tube
            # .faces("<Z") does not work as expected for this solid, so we have to use this:
            .copyWorkplane(cq.Workplane("XY"))
            .transformedWorkplane(
                # We need to add 0.01 to not cut exactly through the tube edge, as that confuses the 
                # splitcut() method, making it return both parts.
                offset = (0, m.output.outer_diameter / 2 * (-1 if m.output.cut_angle > 0 else 1) + 0.01, 0),
                rotate_x = m.output.cut_angle
            )
            .splitcut(keepTop = True)
        )
        if self.debug: show_object(vertical_tube, name = "DEBUG: vertical_tube + end cuts", options = debug_appearance)

        # Rotate and move the tube things into their final position.
        tube_solid = (
            vertical_tube_solid
            .translate((0, 0, -m.length_after_wall))
            .rotate((1,0,0), (-1,0,0), 90 - m.angle)
            .rotate((0,0,1), (0,0,-1), m.horizontal_angle)
        )
        if self.debug: show_object(tube_solid, name = "DEBUG: tube_solid", options = debug_appearance)
        tube = (
            # todo: Fix the rotation code duplication compared to above.
            vertical_tube
            .translate((0, 0, -m.length_after_wall))
            .rotate((1,0,0), (-1,0,0), 90 - m.angle)
            .rotate((0,0,1), (0,0,-1), m.horizontal_angle)
        )
        if self.debug: show_object(tube, name = "DEBUG: tube", options = debug_appearance)

        # Create a large, for-construction wall to use for measuring by intersection probing.
        # todo: The calculation below may fail for large m.shell_thickness
        intersector_size = max(m.input.outer_diameter, m.output.outer_diameter) * 5
        wall_intersector = (
            cq.Workplane("XZ")
            .box(intersector_size, intersector_size, m.wall.thickness)
        )
        if self.debug: show_object(wall_intersector, name = "DEBUG: wall_intersector", options = debug_appearance)

        minimum_wall = tube_solid.intersect(wall_intersector).boxAround()
        if self.debug: show_object(minimum_wall, name = "DEBUG: minimum_wall", options = debug_appearance)

        # Determine the minimum size of the wall as necessary for the tube to go through only 
        # the front and back face of the wall.
        min_wall_spec = minimum_wall.val().BoundingBox()

        # Calculate dynamic measures of the wall insert from the model built so far.
        m.wall.width = (
            min_wall_spec.xlen
            # Extend the wall size by the space needed for grooves. For inclined tubes, a small 
            # part of the grooves could be cut into the minimum sized wall without cutting into the 
            # tube shape, but for simplicity we ignore that possibility.
            + (m.wall.groove_depth if m.wall.grooves.right else 0)
            + (m.wall.groove_depth if m.wall.grooves.left  else 0)
        )
        m.wall.height = (
            min_wall_spec.zlen
            # Extend the wall size by the space needed for grooves. As above.
            + (m.wall.groove_depth if m.wall.grooves.top    else 0)
            + (m.wall.groove_depth if m.wall.grooves.bottom else 0)
        )
        m.wall.center_offset = min_wall_spec.center

        # Create the wall element.
        wall_insert = cq.Workplane("XY").part(WallInsert, m.wall)
        if self.debug: show_object(wall_insert, name = "DEBUG: wall_insert", options = debug_appearance)

        # Assemble the final model.
        self.model = (
            wall_insert
            # todo: Cut with an elongated tube solid to also cover cases where the input is not 
            #   fully in front of the wall. This might also fix CadQuery hanging at times 
            #   (see above).
            .cut(tube_solid)
            .union(tube)
        )


# =============================================================================
# Part Creation
# =============================================================================

measures = Measures(
    shell_thickness = 3, # todo: Use correct measures for EN 1451 tubes.
    # Do not visually optimize the tube end of an inclined tube to coincide with the wall or be 
    # behind the wall's surface. That lets CadQuery hang depending on added grooves.
    # Let it stick out at least 0.1 mm more.
    # todo: Fix the hang condition when the tube end is not fully in front of the wall surface.
    length_before_wall = 17.7, # 21.3 at 45°, 17.7 at 40°
    length_after_wall = 60,
    # todo: Fix that the geometry construction fails for angles >28° and <31°.
    angle = 40,
    # todo: Count position_pos from the wall center, to make it independent of length_before_wall.
    transition_pos = 48,
    transition_length = 5,
    input = Measures(
        inner_diameter = 32, # todo: Use correct measures for EN 1451 tubes.
        cut_angle = -30
    ),
    output = Measures(
        inner_diameter = 26, # todo: Use correct measures for EN 1451 tubes.
        # There can be some issues with incorrect cuts and hangs at certain angles, esp. those 
        # that make the cut go through edges. Just try slightly different angles then.
        cut_angle = 49
    ),
    wall = Measures(
        thickness = 11,
        groove_width = 3.0 * 1.1,  # Wall panel thickness and tolerance.
        groove_depth = 8,
        grooves = Measures(left = True, right = True, bottom = True)
    )
)
show_options = {"color": "lightgray", "alpha": 0}

tube_socket = cq.Workplane("XY").part(TubeSocket, measures)
show_object(tube_socket, name = "tube_socket", options = show_options)
