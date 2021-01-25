import cadquery as cq
from cadquery import selectors
import logging
import importlib
from math import sqrt, asin, degrees
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

# Register imported CadQuery plugins.
cq.Workplane.boxAround = utilities.boxAround


class TubeSocket:

    def __init__(self, workplane, measures):
        """
        A parametric tube socket embedded into a wall, and flush with its outside.
        
        The parameters allow to make this a socket for EN 1451 wastewater tubes.

        :param workplane: The CadQuery workplane to create the chute on.
        :param measures: The measures to use for the parameters of this design. Keys and defaults:
            - **``tube_outer_diameter``:** Outer nominal diameter of the tube (means, at a normal 
                section, not in a wider section where tubes are connected to each other).
            - **``tube_wall_thickness``:** Shell thickness of the tube element.
            - **``tube_length_before_wall``:** How long the tube sticks out from the wall at the 
                input side. Measured along the tube center line to the center of the wall. Defaults 
                to ``0``.
            - **``tube_length_after_wall``:** How long the tube sticks out from the wall at the 
                output side. Measured along the tube center line to the center of the wall. Defaults 
                to ``0``.
            - **``tube_angle_horizontal``:** The angle of the tube, measured in a horizontal plane,
                relative to going straight through the wall. 0° is straight, positive angles tilr 
                the entry left (in its own natural orientation of "left"). This corresponds to the 
                default rotation direction ("rotating the x axis towards the y axis"). Defaults 
                to ``0``.
            - **``tube_angle_vertical``:** The angle of the tube, measured in a vertical plane, 
                relative to going straight through the wall. 0° is straight, positive angles lift 
                the entry opening. This corresponds to the default rotation direction ("rotating 
                the y axis towards the z axis"). Defaults to ``0``.
            - **``input_cut_angle_horizontal``:** The angle of the plane cutting the tube on the 
                input side, measured in a horizontal plane, relative to a simple straight cut of 
                the tube end. Positive rotation direction is like rotating x axis towards y. 
                Defaults to ``0``.
            - **``input_cut_angle_vertical``:** The angle of the plane cutting the tube on the 
                input side, measured in a vertical plane, relative to a simple straight cut of 
                the tube end. Positive rotation direction is like rotating y axis towards z. 
                Defaults to ``0``.
            - **``exit_cut_angle_horizontal``:** Like ``input_cut_angle_horizontal`` but for the 
                exit side.
            - **``exit_cut_angle_vertical``:** Like ``input_cut_angle_vertical`` but for the 
                exit side.
            - **``socket_clearance``:** Difference between outer diamater of inner tube and inner 
                diameter of the socket.
            - **``socket_depth``:** How far the tube can be inserted into the tube socket. Measured 
                along the tube centerline if the tube had been cut with a simple straight cut.
            - **``seal_position``:** 0 means "one ``tube_wall_thickness`` away from the tube input".
            - **``seal_outer_diameter``:** Defines the inner diameter of the seal cavity.
            - **``seal_depth``:** Defines the depth of the seal cavity.
            - **``wall_thickness``:** Thickness of the tube socket's integrated wall element.
            - **``panel_thickness``:** Thickness of the panel elements to be inserted into the 
                tube socket's integrated wall element.
            - **``groove_positions``:** Where to create grooves around the tube socket's integrated 
                wall element. A Dict with elements "left", "right", "top", "bottom", each with a 
                Boolean value. Values not supplied default to ``False``.
            - **``groove_depth``:** How to deep to cut the grooves around the tube socket's 
                integrated wall element.
        """
        self.model = workplane

        self.tube_outer_diameter = float(measures.get("tube_outer_diameter"))
        self.tube_wall_thickness = float(measures.get("tube_wall_thickness"))
        self.tube_length_before_wall = float(measures.get("tube_length_before_wall", 0))
        self.tube_length_after_wall = float(measures.get("tube_length_after_wall", 0))
        self.tube_length = self.tube_length_before_wall + self.tube_length_after_wall
        self.tube_angle_horizontal = float(measures.get("tube_angle_horizontal", 0))
        self.tube_angle_vertical = float(measures.get("tube_angle_vertical", 0))
        self.input_cut_angle_horizontal = float(measures.get("input_cut_angle_horizontal", 0))
        self.input_cut_angle_vertical = float(measures.get("input_cut_angle_vertical", 0))
        self.exit_cut_angle_horizontal = float(measures.get("exit_cut_angle_horizontal", 0))
        self.exit_cut_angle_vertical = float(measures.get("exit_cut_angle_vertical", 0))
        self.socket_clearance = float(measures.get("socket_clearance"))
        self.socket_depth = float(measures.get("socket_depth"))
        self.seal_position = float(measures.get("seal_position"))
        self.seal_outer_diameter = float(measures.get("seal_outer_diameter"))
        self.seal_depth = float(measures.get("seal_depth"))
        self.wall_thickness = float(measures.get("wall_thickness"))
        self.panel_tickness = float(measures.get("panel_thickness"))
        self.groove_positions = measures.get("groove_positions", {"left": True, "right": True, "top": False, "bottom": True})
        self.groove_depth = float(measures.get("groove_depth"))

        self.build()


    def build(self):

        # Create the tube as a solid (with no hole).
        tube_solid = (
            self.model
            .circle(self.tube_outer_diameter / 2)
            .extrude(self.tube_length)
            .translate((0, 0, -self.tube_length_after_wall / 2))
            # todo: use rotate(), as we don't want to rotate about the object's center.
            .rotateAboutCenter((0, 0, 1), self.tube_angle_horizontal)
            .rotateAboutCenter((1, 0, 0), self.tube_angle_vertical)
        )

        intersector_size = self.tube_outer_diameter * 10
        wall_intersector = (
            cq
            .Workplane("XZ")
            .box(intersector_size, intersector_size, self.wall_thickness)
        )

        # Create the minimum wall element (the part that must not be cut by any grooves) by 
        # creating a bouning box around the intersection of the tube and a hypothetical large 
        # wall element.
        minimum_wall = (
            self.model
            .add(tube_solid)
            .intersect(wall_intersector)
            .boxAround()
        )
        show_object(minimum_wall, name = "minimum_wall", options = {"color": "blue", "alpha": 0.3})

        # Temp code.
        self.model = self.model.add(tube_solid).union(wall_intersector)
        
        

        # Construct the grooves for the panel inserts by adding to minimum_wall.
        #   – Select the front face of that box and create a wire offset2D() from it, 
        #     to make space for the wall slots. Same with the back face.
        #   – loft() the two wires into a new box.
        #   – Select the four small faces of that box in turn, and either cut in a groove 
        #     as wide as a wall panel (plus tolerance) or cut off a whole part as deep as a 
        #     groove normally is, depending on the configuration.

        # Merge the wall element with the solid tube.

        # Cut a hole through the solid tube.

        # Cut the protruding parts at the entry of the wall element.

        # Cut the specified angle to the end of the tube.


# =============================================================================
# Part Creation
# =============================================================================

cq.Workplane.part = utilities.part

# todo:: Find a CAD model or measures of the EN 1451 wastewater tube to ensure compatibility.
measures = dict(
    tube_wall_thickness = 3,
    tube_outer_diameter = 32,
    tube_length_after_wall = 70, # Measured along the tube center line to the center of the wall.
    tube_angle_vertical = -45, # 0° means straight, positive angles go up from the entry.
    input_cut_angle_vertical = 45,
    exit_cut_angle_vertical = 45, # 0-180°, 90° is a straight cut of the tube

    socket_clearance = 2, # todo:: Use the right measure for EN 1451 tubes.
    socket_depth = 35,
    seal_position = 5, # 0 meaning "directly at the tube entry"
    seal_outer_diameter = 5,
    seal_depth = 5,

    wall_thickness = 11,
    panel_thickness = 3,
    groove_positions = {"left": True, "right": True, "top": False, "bottom": True},
    groove_depth = 8
)
show_options = {"color": "yellow", "alpha": 0.8}

tube_socket = cq.Workplane("XY").part(TubeSocket, measures)
show_object(tube_socket, name = "tube_socket", options = show_options)
