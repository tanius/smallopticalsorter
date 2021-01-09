import cadquery as cq
import logging
from math import sqrt, asin, degrees

# @todo Create a rectangular shape at the input to allow a good combination 
#   with a belt (which is flat at the bottom and not curved).
# @todo Add a parametric mounting bracket to the wall. Can be drawn as part of 
#   the profiles and then be extruded together with the chute shape.
# @todo Adapt the depth calculation. Currently, the part in front of the 
#   tip protrudes over the specified depth.
# @todo If necessary, cut off the upper chute end somewhat (but not vertically 
#   down, that would be too much).
# @todo If necessary, add that a width offset of the output can be configured.

def chute(h, d, wall_thickness, upper_w, lower_w, lower_straight_wall_h, upper_straight_wall_h, wall_h):
    
    def chute_profile(w, straight_wall_h, offset_h):
        nothing = 0.01  # To create a non-zero but negligible 2D width.
        
        return (cq
            .Workplane("XY")
            .transformed(offset = cq.Vector(0, 0, offset_h))
            
            # Draw the wall centerline. Mirroring half the line does not simplify 
            # anything as it complicated drawing the arc.
            .move(w / 2 - wall_thickness / 2, wall_thickness / 2)
            .vLine(straight_wall_h - wall_thickness / 2)
            .threePointArc( # @todo: Somehow use relative coordinates here.
                (0, wall_h - wall_thickness / 2), 
                (- w / 2 + wall_thickness, straight_wall_h)
            )
            .vLine(- straight_wall_h + wall_thickness / 2)
            
            # Draw in parallel to the centerline to create a very thin U profile. 
            # Because offset2D() cannot deal with zero-width shapes yet due to a 
            # bug. See: https://github.com/CadQuery/cadquery/issues/508
            
            .hLine(nothing)
            .vLine(straight_wall_h - wall_thickness / 2)
            .threePointArc( # @todo: Somehow use relative coordinates here.
                (0, wall_h - wall_thickness / 2 - nothing), 
                (w / 2 - wall_thickness / 2 - nothing, straight_wall_h)
            )
            .vLine(- straight_wall_h + wall_thickness / 2)
            .close()
            
            # Offset to wall_tickness
            .offset2D(wall_thickness / 2)
        )
    
    log = logging.getLogger(__name__)
    
    # Since we'll cut off the chute horizontally and vertically, its 
    # slide length is simply based on Pythagoras of is depth and height:
    slide_length = sqrt(d*d + h*h)
    # Drop angle at entry to the chute, same as exit angle.
    slide_angle = degrees(asin(h / slide_length))
    
    lower_profile = chute_profile(lower_w, lower_straight_wall_h, 0)
    upper_profile = chute_profile(upper_w, upper_straight_wall_h, slide_length)
    
    # return upper_profile
    
    # Lofting with a special technique for independently created wires. See:
    # https://github.com/CadQuery/cadquery/issues/327#issuecomment-616127686
    chute = cq.Workplane("XY")
    chute.ctx.pendingWires.extend(lower_profile.ctx.pendingWires)
    chute.ctx.pendingWires.extend(upper_profile.ctx.pendingWires)
    chute = chute.loft(combine = True)
    
    # Rotate the chute as needed.
    chute = chute.rotate((-1,0,0), (1,0,0), -(90 - slide_angle))
    
    # Cut off the lower chute end horizontally.
    # output_shape width is generous to cut off a widening chute properly.
    output_shape = cq.Workplane("XY").box(lower_w * 2, d * 2, h).translate((0,0,-h/2))
    chute = chute.cut(output_shape)

    return chute


result = chute(
    h = 50.0, d = 35.0, wall_thickness = 4, upper_w = 50.0, lower_w = 24.0, 
    wall_h = 20.0, lower_straight_wall_h = 12, upper_straight_wall_h = 17.9
)
