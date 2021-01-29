import cadquery as cq
from cadquery import selectors
import logging
import importlib
from types import SimpleNamespace as Measures
import utilities # Local directory import.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)

# Register imported CadQuery plugins.
cq.Workplane.part = utilities.part
cq.Workplane.xGroove = utilities.xGroove
cq.Workplane.transformedWorkplane = utilities.transformedWorkplane

log = logging.getLogger(__name__)


class WallInsert:

    def __init__(self, workplane, measures):
        """
        A parametric, grooved wall element that can be integrated into thin panel walls.

        .. todo:: Parameter documentation.
        .. todo:: Add parameters for edge and corner rounding.
        """

        self.model = workplane
        self.measures = measures

        # Add optional measures if missing, using their default values.
        if not hasattr(measures, 'center_offset'):  measures.center_offset = cq.Vector(0, 0, 0)
        if not hasattr(measures, 'grooves'):        measures.grooves = Measures()
        if not hasattr(measures.grooves, 'left'):   measures.grooves.left = False
        if not hasattr(measures.grooves, 'right'):  measures.grooves.right = False
        if not hasattr(measures.grooves, 'top'):    measures.grooves.top = False
        if not hasattr(measures.grooves, 'bottom'): measures.grooves.bottom = False

        self.build()


    def build(self):
        m = self.measures

        # Determine how to place the center of the ungrooved part at center_offset.
        # Because, that point is being used as the "part center".
        offset = m.center_offset
        if m.grooves.right and not m.grooves.left: offset.x += m.groove_depth / 2
        if m.grooves.left and not m.grooves.right: offset.x -= m.groove_depth / 2
        if m.grooves.top and not m.grooves.bottom: offset.z += m.groove_depth / 2
        if m.grooves.bottom and not m.grooves.top: offset.z -= m.groove_depth / 2

        # Create the basic wall shape.
        wall_insert = (
            self.model
            .box(m.width, m.thickness, m.height)
            .translate(offset)
        )

        # Cut the grooves for the wall panels.
        for side in ("left", "right", "top", "bottom"):
            if getattr(m.grooves, side) == False: continue
            wall_insert = (
                wall_insert
                .faces(dict(left = "<X", right = ">X", top = ">Z", bottom = "<Z")[side])
                .transformedWorkplane(
                    invert = True, 
                    # Rotate so that the x axis points along the cut direction.
                    rotate_z = dict(left = 90, right = 90, top = 0, bottom = 0)[side]
                )
                .xGroove(m.groove_width, m.groove_depth)
            )

        self.model = wall_insert


# =============================================================================
# Part Creation (for testing only)
# =============================================================================

# measures = Measures(
#     width = 100,
#     height = 100,
#     thickness = 11,
#     groove_width = 3.0 * 1.1, # Wall panel thickness plus tolerance.
#     groove_depth = 8,
#     grooves = Measures(left = True, right = True, bottom = True)
# )
# show_options = {"color": "blue", "alpha": 0.9}

# wall_insert = cq.Workplane("XY").part(WallInsert, measures)
# show_object(wall_insert, name = "wall_insert", options = show_options)
