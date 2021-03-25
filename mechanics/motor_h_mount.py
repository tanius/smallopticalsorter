import cadquery as cq
import logging, importlib
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class MotorHMount:

    def __init__(self, workplane, measures):
        """
        A parametric stepper motor mount where the motor axis is mounted horizontally.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``motor_width``:** todo
            - **``motor_height``:** todo
            - **``motor_depth``:** todo
            - **``wall_thickness``:** todo
            - **``faceplate.mounthole_distance``:** todo
            - **``faceplate.mounthole_diameter``:** todo
            - **``faceplate.mainhole_diameter``:** todo
            - **``faceplate.mainhole_cbore_diameter``:** todo
            - **``faceplate.mainhole_cbore_depth``:** todo
            - **``brackets.width``:** todo
            - **``brackets.hole_count``:** todo
            - **``brackets.hole_diameter``:** todo
            - **``brackets.fillet_radius``:** todo

        .. todo:: Reimplement the construction of the wall mount brackets using bracket() from 
            utilities.py.
        .. todo:: Build the object into the opposite y direction, so that its faceplate faces 
            into the "front" (positive y) direction.
        .. todo:: As an alternative to a central countersunk hole in the faceplate, when configured 
            use two Slot2D elements instead, allowing to mount the motor without removing the mount.
        .. todo:: Add a parameter for triangular braces to connect the wall mount brackets to the 
            motor enclosure in a more durable manner.
        .. todo:: Add a parameter for cooling holes throughout the side walls and lower wall. Or 
            even better, add vertical ribs on the inside of the vertical walls (so the air can rise) 
            and holes to the bottom, esp. to the bottom of the spaces between the ribs.
        """

        cq.Workplane.combine_wires = utilities.combine_wires
        cq.Workplane.add_rect = utilities.add_rect
        cq.Workplane.translate_last = utilities.translate_last

        self.model = workplane
        self.debug = False
        self.measures = measures

        self.measures.width = measures.motor_width + 2 * measures.wall_thickness
        self.measures.height = measures.motor_height + measures.wall_thickness
        self.measures.depth = measures.motor_depth + 2 * measures.wall_thickness

        self.measures.width_over_all = self.measures.width + 2 * measures.brackets.width

        # todo: Initialize missing measures with defaults.

        self.build()


    def brackethole_points(self):
        m = self.measures

        # Calculate an offset to use for both the vertical and horizontal distance from the outer 
        # edges of holes in the brackets.
        offset = m.brackets.width / 2
        v_spacing = (m.height - 2 * offset) / (m.brackets.hole_count - 1)
        h_spacing = m.width_over_all - 2 * offset
        points = []

        # Go row-wise through all points from bottom to top and collect their coordinates.
        # (Origin is assumed in the lower left of the part's back surface.)
        for row in range(m.brackets.hole_count):
            for column in range(2):
                points.append((
                    offset + column * h_spacing,
                    offset + row * v_spacing
                ))

        return points


    def build(self):
        m = self.measures

        self.model = (
            self.model

            # First create an U profile, with two flaps at the upper end pointing outwards.

            # Front wall profile
            .add_rect(m.width, m.wall_thickness)
            .translate_last((0, m.wall_thickness / 2))

            # Side wall profiles
            .add_rect(m.wall_thickness, m.depth)
            .translate_last((m.width / 2 - m.wall_thickness / 2, m.depth / 2))
            .add_rect(m.wall_thickness, m.depth)
            .translate_last((-m.width / 2 + m.wall_thickness / 2, m.depth / 2))

            # Back wall bracket profiles
            .add_rect(m.brackets.width, m.wall_thickness, centered = False)
            .translate_last((m.width / 2, m.depth - m.wall_thickness))
            .add_rect(m.brackets.width, m.wall_thickness, centered = False)
            .translate_last((-m.width / 2 - m.brackets.width, m.depth - m.wall_thickness))

            # Union the wires to create the desired U profile, then extrude it.
            .combine_wires().toPending()
            .extrude(m.height)

            # Add the bottom wall.
            .union(
                cq.Workplane("XY")
                .box(m.width, m.depth, m.wall_thickness)
                .translate((0, m.depth / 2, m.wall_thickness / 2))
            )

            # Cut the main hole for the motor axle into the faceplate.
            # Select the inner face of the front wall and mark its center.
            .faces("<<Y[-2]").workplane().center(0, m.wall_thickness + m.motor_height / 2)
            .cboreHole(
                m.faceplate.mainhole_diameter,
                m.faceplate.mainhole_cbore_diameter,
                m.faceplate.mainhole_cbore_depth
            )

            # Cut the four motor mount holes.
            .workplane()
            .rect(m.faceplate.mounthole_distance, m.faceplate.mounthole_distance, forConstruction = True)
            .vertices()
            .circle(m.faceplate.mounthole_diameter / 2)
            .cutThruAll()

            # Add the bolt holes on the brackets.
            # Create a workplane on the lower right corner of the back face. See:
            # https://cadquery.readthedocs.io/en/latest/examples.html#locating-a-workplane-on-a-vertex
            .faces(">Y").vertices(">(1,0,-1)").workplane(centerOption="CenterOfMass")
            .pushPoints(self.brackethole_points())
            .circle(m.brackets.hole_diameter / 2)
            .cutThruAll()

            # Add fillets to the edges between motor case and wall mount brackets.
            .faces("<X[-2] or >X[-2]")
            .edges(">Y")
            .fillet(m.brackets.fillet_radius)

            # Add chamfers along the inner side edges, filling in the space left 
            # by the corresponding edge chamfers of NEMA stepper motors.
            .faces("<Z[-2]")
            .edges("<X or >X")
            .chamfer(m.motor_chamfer)

            # Add a chamfer around the lower edge to remove sharp edges and corners.
            .faces("<Z")
            .edges()
            .chamfer(m.lower_chamfer)

            # Add a chamfer around the upper edge to remove sharp edges and corners.
            .faces(">Z")
            .edges()
            .chamfer(m.upper_chamfer)
        )


# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

measures = Measures(
    motor_width = 42.8, # NEMA17: 42.3; NEMA23: 60
    motor_height = 42.3, # NEMA17: 42.3; NEMA23: 60
    motor_depth = 40.5,
    motor_chamfer = 3, # NEMA17: not standardized, but 4 mm is typical
    wall_thickness = 2.4, # 2.4 mm = 6 shells; next option 3.2 mm = 8 shells
    # Chamfer around the bottommost edges. Must be smaller than 0.5 * wall_thickness.
    # When using this, print with a brim to prevent adhesion issues for the brackets.
    lower_chamfer = 0.8,
    # Chamfer around the topmost edges. Must be smaller than 0.5 * wall_thickness.
    upper_chamfer = 0.8,
    faceplate = Measures(
        # rectangular distance between stepper mounting holes (NEMA 23 = 47.1)
        mounthole_distance = 31.0, # NEMA17: 31.0; NEMA23: 47.1
        mounthole_diameter = 3.5, # NEMA17: 3.5 for M3; NEMA23: 5.0 for M4
        mainhole_diameter = 22.1, # NEMA17: ≥5.0; NEMA23: TODO
        mainhole_cbore_diameter = 22.1, # NEMA17: 22.0; NEMA23: 40.0
        mainhole_cbore_depth = 2.0
    ),
    brackets = Measures(
        width = 20,
        hole_count = 2,
        hole_diameter = 3.3, # hole for M3
        fillet_radius = 7
    )
)
show_options = {"color": "lightgray", "alpha": 0}

motor_h_mount = cq.Workplane("XY").part(MotorHMount, measures)
show_object(motor_h_mount, name = "motor_h_mount", options = show_options)
