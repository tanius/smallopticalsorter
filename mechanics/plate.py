import cadquery as cq
import logging, importlib
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

log = logging.getLogger(__name__)


class Plate:

    def __init__(self, workplane, measures):
        """
        A simple parametric plate with optionally chamfered corners.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``TODO``:** TODO.

        .. todo:: Add a parameter "holes" to the measures to specify any number of boreholes with 
            x coordinate, y coordinate, diameter, countersinking diameter, countersinking depth 
            and countersinking type (cylindrical or conical to hole diamater).
        .. todo:: Add a parameter "cutouts" that allows to create any number of rectangular holes 
            and cutouts.
        .. todo:: Add a parameter to support radii rather than chamfers at the corners. This should 
            include corners with different radii in x and y directions, which means elliptic ones.
        """
        cq.Workplane.optional_chamfer = utilities.optional_chamfer

        self.model = workplane
        self.debug = False
        self.measures = measures

        # TODO: Create optional measures.chamfers members with a value of (0, 0).

        self.build()


    def build(self):
        m = self.measures

        self.model = (
            self.model
            .box(m.width, m.height, m.thickness)
            
            .edges("|Y and >X and >Z")
            .optional_chamfer((m.chamfers.right_top[1], m.chamfers.right_top[0]))
            
            .edges("|Y and <X and >Z")
            .optional_chamfer((m.chamfers.left_top[0], m.chamfers.left_top[1]))
            
            .edges("|Y and <X and <Z")
            .optional_chamfer((m.chamfers.left_bottom[1], m.chamfers.left_bottom[0]))
            
            .edges("|Y and >X and <Z")
            .optional_chamfer((m.chamfers.right_bottom[0], m.chamfers.right_bottom[1]))
        )

# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

measures = Measures(
    width = 270,
    height = 215,
    thickness = 5,
    chamfers = Measures(
        # Tuples are given as "width, height", which means "local x extent, local y extent".
        right_top = (0, 0),
        left_top = (0, 0),
        left_bottom = (25, 25),
        right_bottom = (25, 25)
    )
)
show_options = {"color": "lightgray", "alpha": 0}

plate = cq.Workplane("XZ").part(Plate, measures)
show_object(plate, name = "plate", options = show_options)
