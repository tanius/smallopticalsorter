import cadquery as cq
from cadquery import selectors
import logging
import importlib
from math import sqrt, asin, degrees
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

# Register imported CadQuery plugins.
cq.Workplane.part = utilities.part
cq.Workplane.boxAround = utilities.boxAround

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
            - **``seal_cavity.outer_diameter``:** Defines the inner diameter of the seal cavity.
            - **``wall.thickness``:** Thickness of the tube socket's integrated wall element.
            - **``wall.groove_width``:** Thickness of the panel elements to be inserted into the 
                tube socket's integrated wall element.
            - **``wall.groove_depth``:** How to deep to cut the grooves around the tube socket's 
                integrated wall element.
            - **``wall.grooves``:** Where to create grooves around the tube socket's integrated 
                wall element. A Dict with elements "left", "right", "top", "bottom", each with a 
                Boolean value. Values not supplied default to ``False``.

        .. todo:: Add a debug mode, controlled via a class attribute. If True, the build() method 
            would render additional, transparent helper objects to assist in debugging.
        """

        self.model = workplane
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

        # Create the tube as a solid (with no hole).
        tube_solid = (
            self.model
            .circle(m.tube.outer_diameter / 2)
            .extrude(m.tube.length)
            .translate((0, 0, -m.tube.length_after_wall / 2))
            .rotate((1,0,0), (-1,0,0), m.tube.vertical_angle)
            .rotate((0,0,1), (0,0,-1), m.tube.horizontal_angle)
        )

        # todo: The calculation below may fail for large m.tube.wall_thickness
        intersector_size = m.tube.outer_diameter * 5
        wall_intersector = (
            cq.Workplane("XZ")
            .box(intersector_size, intersector_size, m.wall.thickness)
        )
        #show_object(wall_intersector, name = "DEBUG: wall_intersector", options = debug_appearance)

        # Create the minimum wall element (the part that must not be cut by any grooves) by 
        # creating a bouning box around the intersection of the tube and a hypothetical large 
        # wall element.
        wall = (
            self.model
            .add(tube_solid)
            .intersect(wall_intersector)
            .boxAround()
        )
        #show_object(wall, name = "DEBUG: wall: (1) minimum size", options = debug_appearance)

        # Construct the grooves for the panel inserts by adding to the minimum_wall's edge faces.
        for wall_facename in utilities.attr_names(m.wall.grooves):
            face_selector = dict(left = "<X", right = ">X", top = ">Z", bottom = "<Z")
            workplane_rotation = dict(left = (0,0,90), right = (0,0,-90), top = (0,0,0), bottom = (0,0,0))
            #log.info("m.wall.grooves.%s = %s", groove_position, getattr(m.wall.grooves, groove_position))
            if getattr(m.wall.grooves, wall_facename):
                wall = (
                    wall
                    # Select the face to extend.
                    .faces(face_selector[wall_facename])
                    # Convert the face to a wire, add it to pending wires, then return to the CadQuery 
                    # object provided after .faces() so that .workplane() will work. Returning to that 
                    # will affect the stack only, not the set of pending wires.
                    .wires().toPending().end()
                    # Create a workplane on the selected face, as otherwise extruding might happen in the 
                    # wrong direction. See: https://github.com/CadQuery/cadquery/issues/439#issuecomment-674157352
                    .workplane()
                    # Extrude the part of the wall that will hold the groove on this edge.
                    .extrude(15)
                    # A working alternative to all the above is: 
                    # cq.Workplane("XY").add(wall).faces("<Z").wires().toPending().extrude(-20)

                    # Select the faces that should get grooves and cut a groove as deep as the 
                    # previous extrucsion and as wide as the wall panel (plus tolerance).
                    .faces(face_selector[wall_facename])
                    .workplane(invert = True)
                    .transformed(rotate = workplane_rotation[wall_facename])
                    .rect(200, 3)
                    .cutBlind(15)
                )

        show_object(wall, name = "DEBUG: wall: (2) with grooves", options = debug_appearance)

        # Cut the protruding parts at the entry of the wall element.
        # todo

        # Cut the specified angle to the end of the tube.
        # todo

        # Assemble the final model:
        # – Merge the wall element with the solid tube.
        # – Cut a hole through the solid tube.
        # todo
        self.model = self.model.add(tube_solid).union(wall)


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
    seal_cavity = Measures(position = 5, depth = 5, outer_diameter = 5),
    wall = Measures(
        thickness = 11,
        groove_width = 3,
        groove_depth = 8,
        grooves = Measures(left = True, right = True, bottom = True)
    )
)
show_options = {"color": "steelgray", "alpha": 0.9}

tube_socket = cq.Workplane("XY").part(TubeSocket, measures)
show_object(tube_socket, name = "tube_socket", options = show_options)
