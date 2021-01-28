import cadquery as cq
from cadquery import selectors
import logging
import importlib
from math import sqrt, asin, degrees
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
            - **``tube.outer_diameter``:** Outer nominal diameter of the tube (means, at a normal 
                section, not in a wider section where tubes are connected to each other).
            - **``tube.wall_thickness``:** Shell thickness of the tube element.
            - **``tube.length_before_wall``:** How long the tube sticks out from the wall at the 
                input side. Measured along the tube center line to the center of the wall. Defaults 
                to ``0``.
            - **``tube.length_after_wall``:** How long the tube sticks out from the wall at the 
                output side. Measured along the tube center line to the center of the wall. Defaults 
                to ``0``.
            - **``tube.horizontal_angle``:** The angle of the tube, measured in a horizontal plane,
                relative to going straight through the wall. 0° is straight, positive angles tilr 
                the entry left (in its own natural orientation of "left"). This corresponds to the 
                default rotation direction ("rotating the x axis towards the y axis"). Defaults 
                to ``0``.
            - **``tube.vertical_angle``:** The angle of the tube, measured in a vertical plane, 
                relative to going straight through the wall. 0° is straight, positive angles lift 
                the entry opening. This corresponds to the default rotation direction ("rotating 
                the y axis towards the z axis"). Defaults to ``0``.
            - **``input.horizontal_angle``:** The angle of the plane cutting the tube on the 
                input side, measured in a horizontal plane, relative to a simple straight cut of 
                the tube end. Positive rotation direction is like rotating x axis towards y. 
                Defaults to ``0``.
            - **``input.vertical_angle``:** The angle of the plane cutting the tube on the 
                input side, measured in a vertical plane, relative to a simple straight cut of 
                the tube end. Positive rotation direction is like rotating y axis towards z. 
                Defaults to ``0``.
            - **``output.horizontal_angle``:** Like ``input_cut_angle_horizontal`` but for the 
                exit side.
            - **``output.vertical_angle``:** Like ``input_cut_angle_vertical`` but for the 
                exit side.
            - **``socket.clearance``:** Difference between outer diamater of inner tube and inner 
                diameter of the socket.
            - **``socket.depth``:** How far the tube can be inserted into the tube socket. Measured 
                along the tube centerline if the tube had been cut with a simple straight cut.
            - **``seal_cavity.position``:** 0 means "one ``tube_wall_thickness`` away from the tube input".
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

        .. too:: Add fillets to the edges where the tube goes through the wall.
        """

        self.model = workplane
        self.debug = False
        self.measures = measures

        # Add optional measures if missing, using their default values.
        # todo: Create a utility function for this using getattr() internally, called like this: 
        #   self.measures = fill_defaults(self.measures, Measures(…)).
        if not hasattr(measures.tube, 'length_before_wall'): measures.tube.length_before_wall = 0
        if not hasattr(measures.tube, 'length_after_wall'):  measures.tube.length_after_wall = 0
        if not hasattr(measures.tube, 'horizontal_angle'):   measures.tube.horizontal_angle = 0
        if not hasattr(measures.tube, 'vertical_angle'):     measures.tube.vertical_angle = 0
        if not hasattr(measures.input, 'horizontal_angle'):  measures.input.horizontal_angle = 0
        if not hasattr(measures.input, 'vertical_angle'):    measures.input.vertical_angle = 0
        if not hasattr(measures.output, 'horizontal_angle'): measures.output.horizontal_angle = 0
        if not hasattr(measures.output, 'vertical_angle'):   measures.output.vertical_angle = 0
        if not hasattr(measures.wall, 'grooves'):            measures.wall.grooves = Measures()
        if not hasattr(measures.wall.grooves, 'left'):       measures.wall.grooves.left = False
        if not hasattr(measures.wall.grooves, 'right'):      measures.wall.grooves.right = False
        if not hasattr(measures.wall.grooves, 'top'):        measures.wall.grooves.top = False
        if not hasattr(measures.wall.grooves, 'bottom'):     measures.wall.grooves.bottom = False
        
        self.measures.tube.length = \
            self.measures.tube.length_before_wall + self.measures.tube.length_after_wall

        self.build()


    def build(self):
        m = self.measures
        debug_appearance = {"color": "orange", "alpha": 0.5}

        # Create the tube as a solid (with no hole and no rotation).
        vertical_tube_solid = (
            self.model
            .circle(m.tube.outer_diameter / 2)
            .extrude(m.tube.length)
            .faces("|Z").tag("end_faces")
            # todo: Add the end thickening of the tube socket.
            .union(
                cq.Workplane("XY")
                .circle(m.seal_cavity.inner_diameter / 2 + 2 * m.tube.wall_thickness)
                .extrude(m.seal_cavity.depth + 2 * m.tube.wall_thickness)
                .translate((0, 0, m.tube.length - m.seal_cavity.depth - 2 * m.tube.wall_thickness - m.seal_cavity.position))
            )
        )
        if self.debug: show_object(vertical_tube_solid, name = "DEBUG: vertical_tube_solid", options = debug_appearance)
        if self.debug: show_object(vertical_tube_solid.faces(tag = "end_faces"), name = "DEBUG: vertical_tube_solid: end_faces", options = {"color": "red"})

        # Create the hollow tube (with no rotation).
        vertical_tube = (
            self.model
            .union(vertical_tube_solid)
            .faces(tag = "end_faces").shell(-3)
        )
        if self.debug: show_object(vertical_tube, name = "DEBUG: vertical_tube", options = debug_appearance)

        # Rotate and move the tube things into their final position.
        tube_solid = (
            vertical_tube_solid
            .translate((0, 0, -m.tube.length_after_wall / 2))
            .rotate((1,0,0), (-1,0,0), m.tube.vertical_angle)
            .rotate((0,0,1), (0,0,-1), m.tube.horizontal_angle)
        )
        if self.debug: show_object(tube_solid, name = "DEBUG: tube_solid", options = debug_appearance)
        tube = (
            # todo: Fix the rotation code duplication compared to above.
            vertical_tube
            .translate((0, 0, -m.tube.length_after_wall / 2))
            .rotate((1,0,0), (-1,0,0), m.tube.vertical_angle)
            .rotate((0,0,1), (0,0,-1), m.tube.horizontal_angle)
        )
        if self.debug: show_object(tube, name = "DEBUG: tube", options = debug_appearance)

        # Create a large, for-construction wall to use for measuring by intersection probing.
        # todo: The calculation below may fail for large m.tube.wall_thickness
        intersector_size = m.tube.outer_diameter * 5
        wall_intersector = (
            cq.Workplane("XZ")
            .box(intersector_size, intersector_size, m.wall.thickness)
        )
        if self.debug: show_object(wall_intersector, name = "DEBUG: wall_intersector", options = debug_appearance)

        # Determine the minimum size of the wall as necessary for the tube to go through only 
        # the front and back face of the wall.
        min_wall_size = (
            tube_solid # todo: Why does "self.model.add(tube_solid)" not work here?
            .intersect(wall_intersector)
            .val() # Unwrap the first stack item to get a CAD primitive from the CadQuery object.
            .BoundingBox()
        )

        # Calculate dynamic measures of the wall insert from the model built so far.
        m.wall.width = (
            min_wall_size.xlen
            # Extend the wall size by the space needed for grooves. For inclined tubes, a small 
            # part of the grooves could be cut into the minimum sized wall without cutting into the 
            # tube shape, but for simplicity we ignore that possibility.
            + (m.wall.groove_depth if m.wall.grooves.right else 0)
            + (m.wall.groove_depth if m.wall.grooves.left  else 0)
        )
        m.wall.height = (
            min_wall_size.zlen
            # Extend the wall size by the space needed for grooves. As above.
            + (m.wall.groove_depth if m.wall.grooves.top    else 0)
            + (m.wall.groove_depth if m.wall.grooves.bottom else 0)
        )

        # Create the wall element.
        wall_insert = cq.Workplane("XY").part(WallInsert, m.wall)
        # todo: Move the wall element in the xz plane; the original position works only if opposing 
        #     sides have either both grooves of both no grooves; maybe the part creation class has to 
        #     return it translated
        # todo: Move the wall element in the y direction so that the tube extends the right amount 
        #     on each side.
        if self.debug: show_object(wall_insert, name = "DEBUG: wall_insert", options = debug_appearance)

        # Cut the protruding parts at the entry of the wall element.
        # todo

        # Cut the specified angle to the end of the tube.
        # todo

        # Assemble the final model.
        self.model = (
            wall_insert
            .cut(tube_solid)
            .union(tube)
        )


# =============================================================================
# Part Creation
# =============================================================================

measures = Measures(
    tube = Measures(
        wall_thickness = 3,
        outer_diameter = 32,
        length_after_wall = 70,
        vertical_angle = 45
    ),
    input = Measures(vertical_angle = -45,),
    output = Measures(vertical_angle = 45),
    socket = Measures(clearance = 2, depth = 35), # todo:: Use correct measures for EN 1451 tubes.
    # todo: Make the seal cavity optional, and remove it from this part spec.
    seal_cavity = Measures(position = 50, depth = 4, inner_diameter = 34),
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
