import cadquery as cq
import logging


# =============================================================================
# Implementation
# =============================================================================

def case(w, d, h, wall_thickness, offset = (0,0,0)):
    """
    @brief A generic cuboid case with horizontal walls overlapping all others, 
    as needed for stacking stability.
    @todo Support drawing the case with the left side wall opened 180°.
    """
    
    nothing = 0.01

    def x_wall(name):
        offset = (w - wall_thickness)/2 + nothing
        if name == "left": offset = -1 * offset
        
        return (cq.Workplane("YZ")
            .box(d, h - 2 * wall_thickness, wall_thickness)
            .translate((offset, 0, 0))  # In global coordinates!
        )
    
    def y_wall(name):
        offset = (d - wall_thickness)/2 + nothing
        # Indeed, front is negative direction from XZ plane!
        if name == "front": offset = -1 * offset
        
        return (cq.Workplane("XZ")
            .box(w - 2 * wall_thickness, h - 2 * wall_thickness, wall_thickness)
            .translate((0, offset, 0))  # In global coordinates!
        )
    
    def z_wall(name):
        offset = (h - wall_thickness)/2 + nothing
        if name == "top": offset = -1 * offset
        
        return (cq.Workplane("XY")
            .box(w, d, wall_thickness)
            .translate((0, 0, offset))  # In global coordinates!
        )
    
    return (
        x_wall("left"), x_wall("right"), 
        y_wall("front"), y_wall("back"),
        z_wall("top"), z_wall("bottom")
    )


# =============================================================================
# Test Code
# =============================================================================

# True to be able to export everything in a single STEP file. False to be 
# able to selectively show and hide objects in cq-editor.
union_results = False

log = logging.getLogger(__name__)

walls = case(w = 130, d = 350, h = 130, wall_thickness = 3)

if union_results:
    case = (cq.Workplane("XZ")
        .union(walls[0]).union(walls[1]).union(walls[2])
        .union(walls[3]).union(walls[4]).union(walls[5])
    )
else:
    (left_wall, right_wall, front_wall, back_wall, top_wall, bottom_wall) = walls
