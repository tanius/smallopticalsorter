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
        A simple parametric plate with optionally chamfered or filleted corners.

        :param workplane: The CadQuery workplane to create this part on.
        :param measures: The measures to use for the parameters of this design. Expects a nested 
            [SimpleNamespace](https://docs.python.org/3/library/types.html#types.SimpleNamespace) 
            object, which may have the following attributes:
            - **``corners.back_right``:** An n-tuple specifying the type and measures of the corner 
                treatment of the back right corner. For a corner radius of 5 mm, use `("fillet", 5.0)`. 
                For a symmetric chamfer 5 mm, use `("chamfer", 5.0). For a non-symmetric chamfer 
                of width 5 mm and height 2 mm, use `("chamfer", 5.0, 2.0)`.
            - **``corners.back_left``:** As `corners.back_right`, but for the back left corner.
            - **``corners.front_right``:** As `corners.back_right`, but for the front right corner.
            - **``corners.front_left``:** As `corners.back_right`, but for the front left corner.
            - **``TODO``:** TODO.

        .. todo:: Add the input hole and a finger hole for extracting the sorter module to the top plate.
        .. todo:: Add all bolt holes to the base plate.
        .. todo:: Add a parameter "holes" to the measures to specify any number of boreholes with 
            x coordinate, y coordinate, diameter, countersinking diameter, countersinking depth 
            and countersinking type (cylindrical or conical to hole diamater).
        .. todo:: Add a parameter "cutouts" that allows to create any number of rectangular holes 
            and cutouts.
        .. todo:: Support corner radii with different radii in x and y directions, which means 
            elliptic ones.
        """

        self.model = workplane
        self.debug = False
        self.measures = measures

        if (not hasattr(measures.corner_cuts, "back_right")): measures.corner_cuts.back_right = None
        if (not hasattr(measures.corner_cuts, "back_left")): measures.corner_cuts.back_left = None
        if (not hasattr(measures.corner_cuts, "front_left")): measures.corner_cuts.front_left = None
        if (not hasattr(measures.corner_cuts, "front_right")): measures.corner_cuts.front_right = None

        self.build()


    def build(self):

        def corner_cut(self, spec):
            """
            CadQuery plugin to create a chamfer or fillet for the edge or edges on the stack, using 
            the given specification. See class Plate for the spec format.
            """

            if spec is None:
                # Nothing to do, leave the corner as it is.
                return self.newObject([self.findSolid()])

            cut_type = spec[0]
            cut_length_1 = spec[1]
            cut_length_2 = spec[2] if len(spec) >= 3 else None

            if cut_type == "fillet":
                return self.newObject(
                    self
                    .fillet(radius = cut_length_1)
                    .objects
                )
            elif cut_type == "chamfer":
                return self.newObject(
                    self
                    .chamfer(length = cut_length_1, length2 = cut_length_2)
                    .objects
                )

        cq.Workplane.corner_cut = corner_cut
        m = self.measures

        # Determine the CadQuery primitive "Plane" object wrapped by the Workplane object. See: 
        # https://cadquery.readthedocs.io/en/latest/_modules/cadquery/cq.html#Workplane
        plane = self.model.plane

        # Calculate various local directions as Vector objects using global coordinates.
        # 
        # We want to convert a direction from local to global coordinates, not a point. A 
        # direction is not affected by coordinate system offsetting, so we have to undo that 
        # offset by subtracting the converted origin.
        # 
        # TODO: Rather use these as functions from utilities.py once they are available there. 
        #   So far, these are only used in bracket() in utilities.py.
        dir_min_x  = plane.toWorldCoords((-1, 0, 0))  - plane.toWorldCoords((0,0,0))
        dir_max_x  = plane.toWorldCoords(( 1, 0, 0))  - plane.toWorldCoords((0,0,0))
        dir_min_y  = plane.toWorldCoords(( 0,-1, 0))  - plane.toWorldCoords((0,0,0))
        dir_max_y  = plane.toWorldCoords(( 0, 1, 0))  - plane.toWorldCoords((0,0,0))
        dir_min_z  = plane.toWorldCoords(( 0, 0,-1))  - plane.toWorldCoords((0,0,0))
        dir_max_z  = plane.toWorldCoords(( 0, 0, 1))  - plane.toWorldCoords((0,0,0))
        dir_min_xz = plane.toWorldCoords((-1, 0,-1))  - plane.toWorldCoords((0,0,0))

        parallel_local_z = cq.selectors.ParallelDirSelector(dir_max_z)
        min_local_x = cq.selectors.DirectionMinMaxSelector(dir_max_x, directionMax = False)
        max_local_x = cq.selectors.DirectionMinMaxSelector(dir_max_x, directionMax = True)
        min_local_y = cq.selectors.DirectionMinMaxSelector(dir_max_y, directionMax = False)
        max_local_y = cq.selectors.DirectionMinMaxSelector(dir_max_y, directionMax = True)

        parallel_z_max_x_max_y = cq.selectors.AndSelector(
            parallel_local_z,
            cq.selectors.AndSelector(max_local_x, max_local_y)
        )
        parallel_z_max_x_min_y = cq.selectors.AndSelector(
            parallel_local_z,
            cq.selectors.AndSelector(max_local_x, min_local_y)
        )
        parallel_z_min_x_min_y = cq.selectors.AndSelector(
            parallel_local_z,
            cq.selectors.AndSelector(min_local_x, min_local_y)
        )
        parallel_z_min_x_max_y = cq.selectors.AndSelector(
            parallel_local_z,
            cq.selectors.AndSelector(min_local_x, max_local_y)
        )

        self.model = (
            self.model
            .box(m.width, m.height, m.thickness)
            
            .edges(parallel_z_max_x_max_y)
            .corner_cut(m.corner_cuts.back_right)
            
            .edges(parallel_z_min_x_max_y)
            .corner_cut(m.corner_cuts.back_left)
            
            .edges(parallel_z_min_x_min_y)
            .corner_cut(m.corner_cuts.front_left)

            .edges(parallel_z_max_x_min_y)
            .corner_cut(m.corner_cuts.front_right)
        )

# =============================================================================
# Part Creation
# =============================================================================
cq.Workplane.part = utilities.part

# Currently, base plate and top plate are identical. That will be different later, for example 
# when sorter modules become narrower.

base_plate_measures = Measures(
    width = 268, # To slide easily into a 270 mm wide Eurobox case.
    height = 180,
    thickness = 5,
    corner_cuts = Measures(
        front_right = ("fillet", 4.0),
        front_left = ("fillet", 4.0)
    )
)

top_plate_measures = Measures(
    width = 268, # To slide easily into a 270 mm wide Eurobox case.
    height = 180,
    thickness = 5,
    corner_cuts = Measures(
        front_right = ("fillet", 4.0),
        front_left = ("fillet", 4.0)
    )
)

base_plate = cq.Workplane("XZ").part(Plate, base_plate_measures)
top_plate = (
    cq.Workplane("XY")
    .part(Plate, top_plate_measures)
    .translate((
        0,
        -0.5 * top_plate_measures.height + 0.5 * base_plate_measures.thickness, 
        0.5 * base_plate_measures.height + 0.5 * top_plate_measures.thickness
    ))
)

show_options = {"color": "lightgray", "alpha": 0}
show_object(base_plate, name = "base_plate", options = show_options)
show_object(top_plate, name = "top_plate", options = show_options)
