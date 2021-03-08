import cadquery as cq
import cadquery.selectors as cqs
from math import sin, cos, radians, sqrt
import logging
from types import SimpleNamespace
from OCP.gp import gp_Pnt

log = logging.getLogger(__name__)

# todo: De-register the plugins after use by code here. Otherwise there can be hard-to-debug issues 
#   as the plugin will still appear as registered for client code, and overwriting the registration 
#   is not easily possible from there.

# =============================================================================
# Constants and variables
# =============================================================================

# Semantic coordinate access helper for lists and Tuples.
(x, y, z) = (0, 1, 2)

# Semantic direction names.
dir2d = SimpleNamespace(
    pos_x   = ( 1,0),
    neg_x   = (-1,0),
    pos_y   = (0, 1),
    neg_y   = (0,-1),

    right   = ( 1,0),
    left    = (-1,0),
    up      = (0, 1),
    down    = (0,-1)
)
dir3d = SimpleNamespace(
    pos_x   = ( 1,0,0),
    neg_x   = (-1,0,0),
    pos_y   = (0, 1,0),
    neg_y   = (0,-1,0),
    pos_z   = (0,0, 1),
    neg_z   = (0,0,-1),

    right   = ( 1,0,0),
    left    = (-1,0,0),
    forward = (0, 1,0),
    back    = (0,-1,0),
    up      = (0,0, 1),
    down    = (0,0,-1)
)

# =============================================================================
# Simple functions
# =============================================================================

def circlePoint(radius, angle):
    """
    Get the coordinates of a point on the circle circumference.
    :param radius: Circle radius.
    :param angle: Angle of a radius line to the specified point, with the +y axis as 0°.
    
    .. todo:: Switch to using the +x axis as 0°, as that conforms to the CadQuery 2D coordinate 
        system.
    """
    angle = radians(angle)
    return (radius * sin(angle), radius * cos(angle))


def attr_names(obj):
    """
    Determine the names of user-defined attributes of the given SimpleName object.
    Source: https://stackoverflow.com/a/27532110

    :return: A list of strings.
    """
    return sorted(obj.__dict__)


# =============================================================================
# CadQuery plugins
# =============================================================================

def part(self, part_class, measures):
    """
    CadQuery plugin that provides a factory method for custom parts, allowing to create these in a 
    similar manner to how primitives are created in CadQuery's fluid (means, JQuery-like) API.
    
    The custom part has to be defined in a custom class that (1) stores the part geometry as a 
    CadQuery Workplane object in attribute `model` and (2) has a constructor with two required 
    parameters: `workplane` to hand the CadQuery workplane object to build on, and `measures` for 
    the part specs. The part will be created in the local coordinate system.

    Usage example:
    
    ```
    import utilities
    cq.Workplane.part = utilities.part
    my_part = cq.Workplane("XY").part(MyPart, measures).translate((0,0,5))
    ```

    :param self: The CadQuery Workplane object to which this plugin will be attached at runtime.
    :param part_class: Your class used to create your custom part. Provided not as a string, but 
        as the type. If your class has the name "MyPart", you write `MyPart`, not `"MyPart"`.
    :param measures: A class-specific object with the specifications defining the part, to be 
        provided to the constructor of the given class.

    .. todo:: Use the **kwargs mechanism to pass all parameters after part_class to the class, 
        instead of just measures.
    .. todo:: To help with interactive debugging in the console, add a mixin attribute to every 
        object in part.model.objects that has been added by doing part_class(self, measures). 
        Otherwise there is no way to access the underlaying model objects from a CQ Workplane object.
    """
    part = part_class(self, measures) # Dynamic instantiation from the type contained in part_class.

    # In CadQuery plugins, it is good practice to not modify self, but to return a new object linked 
    # to self as a parent: https://cadquery.readthedocs.io/en/latest/extending.html#preserving-the-chain
    return self.newObject(
        part.model.objects
    )


def optionalPolarLine(self, length, angle):
    """
    CadQuery plugin that draws a polar line, or nothing if line length is 0.
    
    To use this, import it and also add the following line: 
    `cq.Workplane.optionalPolarLine = optionalPolarLine`. Since imports only import types but don't 
    execute code, this cannot be done at import time.
    
    :param self: A CadQuery Workplane object, available after registering it as a Workplane plugin 
        method.
    :param length: Length of the line.
    :param length: Angle of the line, counting from the +x axis as zero.
    """
    if length == 0:
        return self
    else:
        return self.polarLine(length, angle)


def optional_chamfer(self, length):
    """
    CadQuery plugin that creates a chamfer, or does nothing if any chamfering length is zero.

    :param length: An int, float or tuple. A number specifies the chamfer side length of a 
        symetrical chamfer, like CadQuery's `Workplane.chamfer(length)`. A tuple specifies the side 
        lengths of the first and second chamfer lengths of a non-symmetrical chamfer. The first 
        length is the first one encountered in a CCW rotation when looking in parallel of the edge 
        to chamfer, from the positive axis side. This is equivalent to CadQuery's 
        `Workplane.chamfer(length, length2)`.
    """
    if isinstance(length, int) or isinstance(length, float):
        if float(length) == 0.0:
            return self.newObject([self.findSolid()])
        else:
            return self.newObject(self.chamfer(length).objects)

    elif isinstance(length, tuple):
        if float(length[0]) == 0 or float(length[1]) == 0:
            return self.newObject([self.findSolid()])
        else:
            return self.newObject(self.chamfer(length = length[0], length2 = length[1]).objects)


def test_optional_chamfer():
    cq.Workplane.optional_chamfer = optional_chamfer
    model = (
        cq.Workplane("XY")
        .box(24, 24, 6)
        .edges("|Z and >X and >Y").optional_chamfer(0)
        .edges("|Z and <X and >Y").optional_chamfer((0, 0))
        .edges("|Z and <X and <Y").optional_chamfer((6, 0))
        .edges("|Z and >X and <Y").optional_chamfer((6, 3))
    )
    show_object(model)

#test_optional_chamfer()


def sagittaArcOrLine(self, endPoint, sag):
    """
    CadQuery plugin that creates an arc that can also be a straight line, unlike with the CadQuery 
    core Workplane.sagittaArc().

    :param endPoint: End point for the arc. A 2-tuple, in workplane coordinates.
    :param sag: Sagitta of the arc, or zero to get a straight line. A float, indicating the 
        perpendicular distance from arc center to arc baseline.
    """
    if sag == 0:
        return self.lineTo(endPoint[0], endPoint[1])
    else:
        return self.sagittaArc(endPoint, sag)


def uProfile(self, w, straight_h, rounded_h, wall_thickness):
    """
    CadQuery plugin that creates a configurable U-shaped profile that can be rounded or flat at the 
    bottom, open to +y.

    :param w: The width of the profile, measured between the outside of its two parallel legs.
    :param straight_h: Straight part of the wall height. Must be at least wall_thickness, as that 
        is the height of a flat sheet. If it is less, it is automatically corrected to 
        wall_thickness.
    :param rounded_h: Rounded portion of the wall height, measured as the arc height of convex 
        curvature on the inside.
    :param wall_thickness: The part wall thickness when measured orthogonal to the wall.
    """
        
    cq.Workplane.sagittaArcOrLine = sagittaArcOrLine

    # To create a non-zero but negligible surface, as offset2D() can't work with pure lines.
    nothing = 0.01
    
    # Automatically correct straight_h if needed, as the object is always at least as high as a 
    # flat sheet. Also, we have to make it a tiny bit larger than wall_thickness or else vLine() 
    # would trip because it gets a zero as argument.
    if straight_h <= wall_thickness: 
        straight_h = wall_thickness + nothing

    # Outside outline.
    # Draw the wall centerline. Mirroring half the line does not simplify anything as it complicated 
    # drawing the arc.
    profile = (
        self
        # Start position is the centerline of a wall_thickness thick, flat sheet touching the x axis.
        .move(- w / 2 + wall_thickness / 2, - wall_thickness / 2)
        # First straight wall. A straight_h value of just wall_thickness is a flat sheet, so draw no 
        # vertical walls in that case.
        .vLine(-straight_h + wall_thickness)
        # Without straight wall parts, the arc endpoint starts on the centerline of a flat sheet, 
        # so "- wall_thickness / 2".
        .sagittaArcOrLine(
            endPoint = (w / 2 - wall_thickness / 2, -straight_h + wall_thickness / 2), 
            sag = -rounded_h
        )
        # Second straight wall, drawn in the opposite direction as the first. See above.
        .vLine(straight_h - wall_thickness)
    )

    # Inside outline.
    # Draw in parallel to the centerline but in the other direction, to create a very thin U 
    # profile. Because offset2D() cannot deal with zero-width shapes yet due to a bug. See: 
    # https://github.com/CadQuery/cadquery/issues/508
    # todo:: Get the bug mentioned above fixed.
    profile = (
        profile
        .hLine(-nothing)
        .vLine(-straight_h + wall_thickness)
        .sagittaArcOrLine(
            endPoint = (
                - w / 2 + wall_thickness / 2 + nothing, 
                -straight_h + wall_thickness / 2 - nothing
            ), 
            sag = rounded_h
        )
        .vLine(straight_h - wall_thickness)
        .close()
    )
    
    # Offset to create a shape in wall_thickness and with rounded edges.
    profile = profile.offset2D(wall_thickness / 2, "arc")
    
    return profile


def boxAround(self):
    """
    CadQuery plugin that creates a solid box around the objects provided on the stack. The box 
    corresponds to the bounding box containing all objects on the stack (both 2D and 3D).
    """

    # Calculate a combined bounding box of all objects on the stack.
    bounding_box = self.objects[0].BoundingBox()
    for shape in self.objects:
        bounding_box.add(shape.BoundingBox())

    # log.info("\n")
    # log.info("xmin = %s, xmax = %s", bounding_box.xmin, bounding_box.xmax)
    # log.info("ymin = %s, ymax = %s", bounding_box.ymin, bounding_box.ymax)
    # log.info("zmin = %s, zmax = %s", bounding_box.zmin, bounding_box.zmax)

    # Create a solid bounding box sized box in a new object.
    box_around = (
        cq
        .Workplane("XY")
        .transformed(offset = bounding_box.center)
        .box(bounding_box.xlen, bounding_box.ylen, bounding_box.zlen)
    )

    # Not just "return box_around". We want CadQuery to link the modified stack object to the 
    # previous stack: https://cadquery.readthedocs.io/en/latest/extending.html#preserving-the-chain
    return self.newObject(box_around.objects)


def boxAroundTest(id):
    cq.Workplane.boxAround = boxAround

    if id == 1:
        inner_objects = cq.Workplane("XY").box(50, 10, 10).box(10, 50, 10).box(10, 10, 50)
    elif id == 2:
        inner_objects = cq.Workplane("XY").sphere(10).box(10, 50, 10)

    box_around = inner_objects.boxAround()

    show_object(inner_objects, name = "inner_objects", options = {"color": "blue", "alpha": 0})
    show_object(box_around, name = "box_around", options = {"color": "yellow", "alpha": 0.7})


def transformedWorkplane(
    self, offset = None, rotate = None, invert = False, 
    offset_x = None, offset_y = None, offset_z = None, 
    rotate_x = None, rotate_y = None, rotate_z = None,
    centerOption = "ProjectedOrigin", origin = None
):
    """
    CadQuery plugin that creates a new 2D workplane, located relative to the first face on the 
    stack, with additional 3D offset and rotation applied.

    This is a shorthand combining Workplane::workplane and Workplane::transformed.

    :param rotate: A 3-tuple giving rotate_x, rotate_y, rotate_z at once.
    :param offset: A 3-tuple giving offset_x, offset_y, offset_z at once.
    :param invert: Invert the z direction from that of the face.
    :param offset_x: Offset along the workplane's initial local x axis to transform the workplane 
        center relative to its initial location. Applied before the rotation.
    :param offset_y: Offset along the workplane's initial local y axis to transform the workplane 
        center relative to its initial location. Applied before the rotation.
    :param offset_z: Offset along the workplane's initial local z axis to transform the workplane 
        center relative to its initial location. Applied before the rotation.
    :param rotate_x: Rotation angle around the x axis to transform the workplane relative to its 
        initial orientation.
    :param rotate_y: Rotation angle around the y axis to transform the workplane relative to its 
        initial orientation.
    :param rotate_z: Rotation angle around the z axis to transform the workplane relative to its 
        initial orientation.
    :param centerOption: How the local origin of workplane is determined. Value must be one of 
        "CenterOfMass", "ProjectedOrigin", "CenterOfBoundBox", with the meaning as in the original 
        Workplane::workplane method.
    :param origin: The origin to use for plane's center. Requires 'ProjectedOrigin' centerOption.
        Usage as in the original Workplane::workplane method.

    .. todo:: Allow to give offset as a 2-tuple, with z assumed zero.
    .. todo:: Allow to start a workplane from a tagged workplane or object by adding a parameter "tag".
    .. todo:: Apply the three rotations all relative to the local coordinate system as it was at 
        the start of this method, not as it was after the previous rotation. Otherwise rotations 
        around more than one axis are very unintuitive. However, it is not yet clear how to 
        implement this as Workplane::copyWorkplane() would replace the workplane we're working on, 
        undoing the previous rotation completely.
    """

    if isinstance(offset, tuple):
        if offset_x == None and offset_y == None and offset_z == None:
            (offset_x, offset_y, offset_z) = offset
        else: 
            raise ValueError("A 3-tuple offset is redundant to per-axis offsets, and mutually exclusive.")
    elif offset == None:
        offset_x = 0 if offset_x == None else offset_x
        offset_y = 0 if offset_y == None else offset_y
        offset_z = 0 if offset_z == None else offset_z
    else:
        raise ValueError("Wrong type supplied for offset.")

    if isinstance(rotate, tuple):
        if rotate_x == None and rotate_y == None and rotate_z == None:
            (offset_x, offset_y, offset_z) = offset
        else:
            raise ValueError("A 3-tuple offset is redundant to per-axis rotations, and mutually exclusive.")
    elif rotate == None:
        rotate_x = 0 if rotate_x == None else rotate_x
        rotate_y = 0 if rotate_y == None else rotate_y
        rotate_z = 0 if rotate_z == None else rotate_z
    else:
        raise ValueError("Wrong type supplied for rotate.")

    return (
        self
        .workplane(invert = invert, centerOption = centerOption, origin = origin)
        .transformed(rotate = (rotate_x, rotate_y, rotate_z), offset = (offset_x, offset_y, offset_z))
    )

def transformedWorkplaneTest():
    cq.Workplane.transformedWorkplane = transformedWorkplane

    return (
        cq
        .Workplane("XY")
        .transformedWorkplane(rotate_x = 45)
        .box(1, 1, 5)
    )

# show_object(transformedWorkplaneTest(), name = "workplane")


def xGroove(self, width, depth, length = None):
    """
    CadQuery plugin that cuts a groove into the first solid in the current stack, starting from the 
    center of the first object in the current stack, and into the local x direction.

    :param width: Width of the groove to cut.
    :param depth: Depth of the groove to cut.
    :param length: Length of the groove to cut. Half is cut into +x and half into -x direction. 
        If omitted, the groove is cut past the end of the face, so that all material that such a 
        groove can remove is removed. If the provided face is not on a convex part of the solid, 
        this may have unintended side effects.

    .. todo:: Add a parameter to allow rounding the bottom of the groove.
    """

    # If length is not given, determine it from the size of the face to cut into.
    if length == None:
        length = 3000 # temporary dumb implementation

        # Find the first item in the stack that is a face.
        # todo

        # Determine the dimensions of the face's bounding box.
        # todo

        # Set length from the largest dimension of the face's bounding box, times 3 to also cut 
        # through most inclines adjacent of the face to cut.
        # todo

    # Cut the groove into the solid.
    grooved = self.rect(length, width).cutBlind(depth)

    return self.newObject(grooved.objects)


def multistep_cone(self, steps):
    """
    CadQuery plugin that creates objects with varying circular cross-section from cone shapes.

    The plugin combines cone shapes obtained from pairwise lofting of subsequent cross-sections, 
    which leads to a longitudinal section made from straight lines only. This is different from 
    lofting all cross-sections in one operation, creating a curved longitudinal section.

    :param steps: A list of tuples `(float, float)`. Each tuple defines the circular cross-section 
        of one step. The first tuple element designates the distance relative to the last step's 
        cross-section. The second tuple second element designates the cross-section radius.

    .. todo:: Support a change in radius without a change in height. This is not possible with 
        pairwise lofting, as it does not create a solid but a zero-volume shape.
    .. todo:: Support a parameter for a curved longitudinal outline, by lofting all wires at once.
        This should be available as another element in the tuples defining a step, as that allows 
        to mix straightline and curved longitudinal outlines in one solid easily.
    """

    wires = self
    cones = self.newObject(self.objects)
    
    for step in steps:
        wires = wires.workplane(offset = step[0]).circle(step[1])

        # Once we have two wires, do a pairwise loft().
        if len(wires.ctx.pendingWires) == 2:
            cones.add(wires.loft())

            # Lofting removes all pending wires. Recreate the last one for the next step's lofting.
            wires = wires.circle(step[1])
    
    # Union and return all cones.
    return cones.combine(glue = True)


def test_multistep_cone():
    cq.Workplane.multistep_cone = multistep_cone

    cone = cq.Workplane("XY").multistep_cone(((0,2), (10,2), (10,4), (10,4)))
    # cone = cq.Workplane("XY").multistep_cone(((0,2), (3,2), (4,0.5), (1,2)))
    show_object(cone)

# test_multistep_cone()


def splitcut(self, keepTop = False, keepBottom = False):
    """
    A CadQuery plugin that splits the first solid on the stack along a workplane provided at the 
    top of the stack. If there is no workplane at the top of the stack, this method will 
    automatically create the default workplane for the first object on the stack and use that.

    This is a replacement for Workplane::split() using cut(), because split() does not work well 
    yet for more complex geometries and also can take much longer (as of 2021-01). Due to the way 
    this is implemented, there will be a small loss of material (0.001 thick) along the cutting plane.

    :param keepTop: Whether to return the top part of the cut operation, measured in z coordinates 
        of the workplane used for cutting.
    :param keepTop: Whether to return the bottom part of the cut operation, measured in z coordinates 
        of the workplane used for cutting.

    .. todo:: Fix that when cutting with an inclined plane through only one point of the outer 
        circular edge of a tube, no cut is performed. The returned single solid is the original tube 
        but with an added line for the intended cut.
    """

    result = self.workplane().tag("split_plane")
    result = (
        self
        .cut(
            cq.Workplane("XY")
            .copyWorkplane(result.workplaneFromTagged("split_plane"))
            # todo: Use a square plane with an edge length larger than the bounding box diagonal of 
            #   the object to split, to make sure it will be cut through completely.
            .box(500, 500, 0.001)
        )
    )

    if result.solids().size() == 2:
        if keepTop and keepBottom:     return self.newObject(result.solids().objects)
        if keepTop and not keepBottom: return self.newObject(result.solids(">Z").objects)
        if not keepTop and keepBottom: return self.newObject(result.solids("<Z").objects)
    else:
        return self.newObject(result.solids().objects)


def test_splitcut():
    cq.Workplane.splitcut = splitcut

    cylinder = cq.Workplane("XY").circle(10).extrude(100)
    split_cylinder = (
        cylinder
        .faces(">Z")
        .workplane()
        .transformed(rotate = (45,0,0), offset = (0,0,-50))
        .splitcut(keepTop = True, keepBottom = True)
    )

    show_object(split_cylinder)

#test_splitcut()


def combine_wires(self):
    """
    CadQuery plugin that replaces all wires on the stack with their 2D union. It requires all wires 
    on the stack to be co-planar.
    
    To use this, you must place multiple wires on the stack. That is only possible with 
    Workplane::add(), as .rect() etc. will clear the stack before adding a single new wire. Example:

    ```
    model = (
        cq.Workplane("XY")
        .add( cq.Workplane("XY").rect(40, 40, forConstruction = True) )
        .add( cq.Workplane("XY").rect(20, 16, forConstruction = True).translate((0,20)) )
        .combine_wires()
        .toPending()
        .extrude(12)
    )
    ```

    A shortcuts for this technique, Workplane::add_rect() and Workplane::add_circle() are provided 
    as part of this library.

    :return: A Workplane object with the combined wire on the stack (besides nothing else) but not 
        yet in its pending wires.

    .. todo:: Remove this method and its uses. It is now replaced by union_pending().
    """

    #log.info("DEBUG: combine_wires: stack size: %s", self.size())
    #log.info("DEBUG: combine_wires: pending wires: %s", len(self.ctx.pendingWires))

    wires = [obj for obj in self.objects if isinstance(obj, cq.Wire)]
    if len(wires) < 2: return self # Nothing to union for 0 or 1 pending wires.

    extrude_direction = wires[0].normal()
    solids = (
        cq.Workplane("XY")
        # Create a workplane coplanar with the wires, as this will define the extrude() direction.
        .add(cq.Face.makeFromWires(wires[0]))
        .workplane()
    )

    # Extrude all wires into solids.
    # This detour via 3D union'ing is the only way right now to reliably union wires.
    for wire in wires:
        solids = solids.add(wire).toPending().extrude(1)

    combined_wire = (
        solids
        .combine() # 3D union of all the solids.
        # Select the bottom face, as that contains the wires in their original local z position.
        .faces(cq.DirectionMinMaxSelector(extrude_direction, directionMax = False))
        .wires()
    )

    return self.newObject(combined_wire.objects)


def test_combine_wires():
    cq.Workplane.combine_wires = combine_wires
    log.info("")

    # without combine_wires()
    result_before = (
        cq.Workplane("XY")
        .add( cq.Workplane("XY").rect(40, 40, forConstruction = True) ).toPending()
        .add( cq.Workplane("XY").rect(20, 16, forConstruction = True).translate((0,20)) ).toPending()
        .extrude(12)
        .translate((0,0,-20))
    )
    show_object(result_before, name = "without combine_wires()")

    # with combine_wires()
    result_after = (
        cq.Workplane("XY")
        .add( cq.Workplane("XY").rect(40, 40, forConstruction = True) )
        .add( cq.Workplane("XY").rect(20, 16, forConstruction = True).translate((0,20)) )
        .combine_wires()
        .toPending()
        .extrude(12)
    )
    show_object(result_after, name = "with combine_wires()")

#test_combine_wires()


def union_pending(self):
    """
    CadQuery plugin that replaces all pending wires with their 2D union. It requires all pending 
    wires to be co-planar.
    
    This supplements the CadQuery methods Workplane::combine() and Workplane::consolidateWires() and 
    Wire::combine(), which cannot deal with intersecting wires yet. Example usage:

    ```
    model = (
        cq.Workplane("XY")
        .rect(40, 40)
        .rect(20, 16, forConstruction = True).translate((0,20)).toPending()
        .union_pending()
        .extrude(12)
    )
    ```

    :return: A Workplane object with the combined wire on the stack (besides nothing else) and in 
        its pending wires (besides nothing else).

    .. todo:: Enforce that all wires must be co-planar, raising an error otherwise. Or maybe in that 
        case only union those that are coplanar. This can be checked by making sure all normals are 
        parallel and the centers are all in one plane.
        https://cadquery.readthedocs.io/en/latest/classreference.html#cadquery.occ_impl.shapes.Mixin1D.normal
    """

    # It is also possible to union the wires on the stack rather than in pendingWires. However, that 
    # is not a good idea, as it prevents the use of construction geometry as originally intended, 
    # namely as helpers to create 2D objects before adding them to pendingWires. Because then, 
    # "forConstruction = True" would already have the task to keep objects out of pendingWires, so 
    # could not be used to mean "will only be used as temporary shape, don't create something yet" 
    # at the same time.

    wires = self._consolidateWires()
    if len(wires) < 2: return self # Nothing to union for 0 or 1 pending wires.

    extrude_direction = wires[0].normal()
    solids = (
        cq.Workplane("XY")
        # Create a workplane coplanar with the wires, as this will define the extrude() direction.
        .add(cq.Face.makeFromWires(wires[0]))
        .workplane()
    )
    # Extrude all wires into solids.
    # This detour via 3D union'ing is the only way right now to reliably union wires.
    for wire in wires:
        solids = solids.add(wire).toPending().extrude(1)
    
    combined_wire = (
        solids
        .combine() # 3D union of all the solids.
        # Select the bottom face, as that contains the wires in their original local z position.
        .faces(cq.DirectionMinMaxSelector(extrude_direction, directionMax = False))
        .wires()
    )

    self.ctx.pendingEdges = []
    self.ctx.pendingWires = [combined_wire.val()]

    return self.newObject(combined_wire.vals())


def test_union_pending():
    cq.Workplane.union_pending = union_pending
    log.info("")

    # without union_pending()
    result_before = (
        cq.Workplane("XY")
        .rect(40, 40)
        .rect(20, 16, forConstruction = True).translate((0,20)).toPending()
        .extrude(12)
        .translate((0,0,-20))
    )
    show_object(result_before, name = "without union_pending()")

    # with combine_wires()
    result_after = (
        cq.Workplane("XY")
        .rect(40, 40)
        .rect(20, 16, forConstruction = True).translate((0,20)).toPending()
        .union_pending()
        .extrude(12)
        .translate((0,0,8))
    )
    show_object(result_after, name = "with union_pending()")

#test_union_pending()


def difference_pending(self):
    """
    CadQuery plugin that replaces all pending wires with their 2D difference of the first in 
    pendingWires minus all the others. It requires all pending wires to be co-planar. Example usage:

    ```
    model = (
        cq.Workplane("XY")
        .rect(40, 40)
        .rect(20, 16, forConstruction = True).translate((0,20)).toPending()
        .subtract_pending()
        .extrude(12)
    )
    ```

    :return: A Workplane object with the resulting wire on the stack (besides nothing else) and in 
        its pending wires (besides nothing else).

    .. todo:: Enforce that all wires must be co-planar, raising an error otherwise. Or maybe in that 
        case only union those that are coplanar. This can be checked by making sure all normals are 
        parallel and the centers are all in one plane.
        https://cadquery.readthedocs.io/en/latest/classreference.html#cadquery.occ_impl.shapes.Mixin1D.normal
    """

    wires = self._consolidateWires()
    if len(wires) < 2: return self # Nothing to difference for 0 or 1 pending wires.

    first_wire = wires[0]
    other_wires = wires[1:]
    extrude_direction = first_wire.normal()

    solid = (
        cq.Workplane("XY")
        # Create a workplane coplanar with the wires, as this will define the extrude() direction.
        .add(cq.Face.makeFromWires(wires[0]))
        .workplane()
        .add(first_wire).toPending().extrude(1)
    )
    # Cut Extrude all wires into solids.
    # This detour via 3D union'ing is the only way right now to reliably union wires.
    for other_wire in other_wires:
        cutter = cq.Workplane("XY").add(other_wire).toPending().extrude(1)
        solid = solid.cut(cutter)
    
    difference_wires = (
        solid
        # Select the bottom face, as that contains the wires in their original local z position.
        .faces(cq.DirectionMinMaxSelector(extrude_direction, directionMax = False))
        .wires()
    )

    self.ctx.pendingEdges = []
    self.ctx.pendingWires = difference_wires.vals() # Will be multiple if there are holes in the shape.

    return self.newObject(difference_wires.vals())


def test_difference_pending():
    cq.Workplane.difference_pending = difference_pending
    log.info("")

    # without union_pending()
    result_before = (
        cq.Workplane("XY")
        .rect(40, 40)
        .rect(5, 5)
        .rect(20, 16, forConstruction = True).translate((0,20)).toPending()
        .extrude(12)
        .translate((0,0,-20))
    )
    show_object(result_before, name = "without difference_pending()")

    # with combine_wires()
    result_after = (
        cq.Workplane("XY")
        .rect(40, 40)
        .rect(5, 5)
        .rect(20, 16, forConstruction = True).translate((0,20)).toPending()
        .difference_pending()
        .extrude(12)
        .translate((0,0,8))
    )
    show_object(result_after, name = "with difference_pending()")

#test_difference_pending()


def clear_pending_wires(self):
    """
    A CadQuery plugin to delete all currently pending wires, while keeping the same wires in the 
    current stac. Note that it is better to use a forConstruction parameter when creating the wires, 
    where available. It's effect is simply to preven the wire from automatically being added to 
    the pending wires.
    """
    result = self.newObject(self.objects)
    result.ctx.pendingWires = []

    return result

def test_clear_pending_wires():
    cq.Workplane.clear_pending_wires = clear_pending_wires

    model = (
        cq.Workplane("XY")
        .rect(10, 10)
        .clear_pending_wires()
        .translate((0, 20))
        .toPending()
        .extrude(1)
    )
    show_object(model)

#test_clear_pending_wires()


def add_rect(self, xLen, yLen, centered = True):
    """
    A CadQuery plugin that creates a rectangle, adds it to the stack but not to pendingWires, and 
    does not clear the stack.

    .. todo:: Remove this method and its uses. 2D objects should be aggregated in pendingWires, not 
        on the stack, as the latter prevents the proper use of construction geometry. See on 
        combine_wires() for details.
    """
    result = (
        self
        .newObject(self.objects)
        # By wrapping in add(), we avoid rect() clearing the stack.
        .add(
            cq.Workplane()
            .copyWorkplane(self)
            # By using "forConstruction", we avoid adding the rectangle to pendingWires.
            .rect(xLen, yLen, centered, forConstruction = True)
        )
    )

    return result


def test_add_rect():
    cq.Workplane.add_rect = add_rect
    cq.Workplane.combine_wires = combine_wires

    result = (
        cq.Workplane("XY")
        .add_rect(10, 10).translate((20, 0))
        .add_rect(5, 5).translate((3, 0))
        .add_rect(7, 7)
        .combine_wires()
        .toPending()
        .extrude(1)
    )

    show_object(result)

# test_add_rect()


def add_circle(self, radius):
    """
    A CadQuery plugin that creates a circle, adds it to the stack but not to pendingWires, and 
    does not clear the stack.

    .. todo:: Remove this method and its uses. 2D objects should be aggregated in pendingWires, not 
        on the stack, as the latter prevents the proper use of construction geometry. See on 
        combine_wires() for details.
    """
    result = (
        self
        .newObject(self.objects)
        # By wrapping in add(), we avoid circle() clearing the stack.
        .add(
            cq.Workplane()
            .copyWorkplane(self)
            # By using "forConstruction", we avoid adding the circle to pendingWires.
            .circle(radius, forConstruction = True)
        )
    )

    return result


def test_add_circle():
    cq.Workplane.add_circle = add_circle
    cq.Workplane.combine_wires = combine_wires

    result = (
        cq.Workplane("XY")
        .add_circle(10).translate((15, 0))
        .add_circle(10)
        .combine_wires()
        .toPending()
        .extrude(1)
    )

    show_object(result)

#test_add_circle()


def add_polygon(self, nSides, diameter):
    """
    A CadQuery plugin that creates a polygon, adds it to the stack but not to pendingWires, and 
    does not clear the stack.

    .. todo:: Remove this method and its uses. 2D objects should be aggregated in pendingWires, not 
        on the stack, as the latter prevents the proper use of construction geometry. See on 
        combine_wires() for details.
    """
    result = (
        self
        .newObject(self.objects)
        # By wrapping in add(), we avoid polygon() clearing the stack.
        .add(
            cq.Workplane()
            .copyWorkplane(self)
            # By using "forConstruction", we avoid adding the polygon to pendingWires.
            .polygon(nSides, diameter, forConstruction = True)
        )
    )

    return result


def test_add_polygon():
    cq.Workplane.add_polygon = add_polygon
    cq.Workplane.combine_wires = combine_wires

    result = (
        cq.Workplane("XY")
        .add_polygon(3, 12)
        .add_polygon(6, 9)
        .combine_wires()
        .toPending()
        .extrude(1)
    )

    show_object(result)

#test_add_polygon()


def translate_last(self, vec):
    """
    A CadQuery plugin that translates only the topmost item on the stack (the one added last before 
    calling this plugin).
    """
    result = self.newObject(self.objects)

    to_translate = result.objects.pop()
    result.objects.append(to_translate.translate(vec))

    return result


def test_translate_last():
    cq.Workplane.add_circle = add_circle
    cq.Workplane.combine_wires = combine_wires
    cq.Workplane.translate_last = translate_last

    result = (
        cq.Workplane("XY")
        .add_circle(2)
        .add_circle(10).translate_last((15, 0))
        .combine_wires()
        .toPending()
        .extrude(1)
    )

    show_object(result)

#test_translate_last()


def ifelse(self, condition, then_method, then_args, else_method, else_args):
    """
    A CadQuery plugin to execute any other CadQuery plugin if a condition applies. This allows to 
    integrate "if" statements without breaking out of the fluid API call chain.

    However, the calling syntax is not great, as the method to call has to be provided via a string 
    for technical reasons. So it seems better to break the chained methods calls and use "if". Or 
    create variants of the method to call that include a condition. fillet_if() and chamfer_if() 
    are provided as part of this library.

    :param condition: The condition that has to be met to execute the specified method call.
    :param method: Name of the Workplane class' method to execute if the condition applies. This 
        has to be provided as a string, as there is no variable referencing the current state of 
        a chained fluent API call before that chained call has been evaluated completely.
    :param *pos_args: Positional arguments to be provided to the specified method. Write them 
        one after another just as you would in an actual call of that method.
    :param *kw_args: Keyword arguments to be provided to the specified method. Write them 
        one after another just as you would in an actual call of that method.

    .. todo:: Move this to a file with CadQuery experiments. It's not suitable for practical use.
    .. todo:: Allow to also provide positional parameters, not just keyword parameters, to the 
        methods to call.
    .. todo:: The call syntax is not readable or practically useful for this generic case. But 
        it would work to provide several variants for the most used cases: .union_if(), .cut_if() 
        etc..
    """
    if condition:
        method = getattr(self, then_method) # Convert string method name to callable reference.
        return method(**then_args)
    else:
        method = getattr(self, else_method) # Convert string method name to callable reference.
        return method(**else_args)


def test_ifelse():
    cq.Workplane.ifelse = ifelse

    result = cq.Workplane("XY")
    result = (
        result
        .box(10, 10, 1)
        .edges("|Z")
        .ifelse(1<2, "fillet", {"radius": 2}, "end", {"n": 1})
    )
    show_object(result)

#test_ifelse()


def fillet_if(self, condition, radius):
    """
    .. todo:: Documentation.
    """

    # solid = self.findSolid()

    # edgeList = cast(List[Edge], self.edges().vals())
    # if len(edgeList) < 1:
    #     raise ValueError("Fillets requires that edges be selected")

    # s = solid.fillet(radius, edgeList)
    # return self.newObject([s.clean()])

    if condition:
        return self.fillet(radius)
    else:
        return self.newObject([self.findSolid()])


def test_fillet_if():
    cq.Workplane.fillet_if = fillet_if

    result = cq.Workplane("XY")
    result = (
        result
        .box(10, 10, 1)
        .edges("|Z")
        .fillet_if(1<2, 2)
    )
    show_object(result)

#test_fillet_if()


def chamfer_if(self, condition, length, length2 = None):
    """
    .. todo:: Documentation.
    """
    if condition:
        return self.chamfer(length, length2)
    else:
        return self.newObject([self.findSolid()])


def test_chamfer_if():
    cq.Workplane.chamfer_if = chamfer_if

    result = cq.Workplane("XY")
    result = (
        result
        .box(10, 10, 1)
        .edges("|Z")
        .chamfer_if(1<2, 2)
    )
    show_object(result)

#test_chamfer_if()


def extrude_if(self, condition, length):
    """
    .. todo:: Documentation.
    """
    if condition:
        return self.extrude(length)
    else:
        return self.newObject([self.findSolid()])


def test_extrude_if():
    cq.Workplane.extrude_if = extrude_if

    model = (
        cq.Workplane("XY")
        .box(4,4,4)
        .circle(5)
        .extrude_if(1<2, 1)
    )
    show_object(model)

#test_extrude_if()


def show_local_axes(self, length = 20):
    """
    A CadQuery plugin to visualize the local coordinate system as a help for debugging.

    .. todo:: Fix that this plugin cannot be imported from another file, as then the error 
        message will be "name show_object is not defined", as that other file is not opened in 
        cq-editor.
    .. todo:: Allow to specify a prefix for the show_object() name to show.
    .. todo:: Render arrowheads at the tops of the axes, as seen in cq-editor.
    .. todo:: Render a small white sphere at the center of the axes, as seen in cq-editor itself.
    """
    x_axis = (
        cq.Workplane().copyWorkplane(self)
        # No idea why rotating 90° is needed, as -90° would be expected.
        .transformed(rotate = (0, 90, 0))
        .circle(length / 20).extrude(length)
    )
    y_axis = (
        cq.Workplane().copyWorkplane(self)
        .transformed(rotate = (-90, 0, 0))
        .circle(length / 20).extrude(length)
    )
    z_axis = (
        cq.Workplane().copyWorkplane(self)
        .circle(length / 20).extrude(length)
    )

    show_object(x_axis, name = "local X", options = {"color": "red"})
    show_object(y_axis, name = "local Y", options = {"color": "green"})
    show_object(z_axis, name = "local Z", options = {"color": "blue"})

    return self


def test_show_local_axes():
    cq.Workplane.show_local_axes = show_local_axes

    # Workplane on an ege.
    result = (
        cq.Workplane()
        .box(10, 10, 1)
        .faces(">Z")
        .edges(">Y")
        .workplane(centerOption = "CenterOfMass")
        .show_local_axes(3)
        .end(3)
    )
    show_object(result)

    # Workplane on a vertex.
    result = (
        cq.Workplane().transformed(offset = (0,0,20))
        .box(10, 10, 1)
        .faces(">Z")
        .edges(">Y")
        .vertices("<X")
        .workplane(centerOption = "CenterOfMass")
        .show_local_axes(3)
        .end(4)
    )
    show_object(result)

# test_show_local_axes()


def bracket(self, thickness, height, width, offset = 0, angle = 90,
    hole_count = 0, hole_diameter = None, 
    edge_fillet = None, edge_chamfer = None, corner_fillet = None, corner_chamfer = None
):
    """
    A CadQuery plugin to create an angle bracket along an edge.

    Must be used on a workplane that (1) coincides with the face on which to build the bracket, 
    (2) has its origin at the center of the edge along which to build the bracket and (3) has its 
    x axis pointing along the edge along which to build the bracket and (4) has its y axis pointing 
    away from the center of the face on which to build the bracket.

    :param …: todo

    .. todo:: Support to create only one hole in the bracket. Currently this results in "division 
        by float zero".
    .. todo:: Change the edge filleting so that it is done before cutting the holes, and so that 
        the holes are only cut into the non-filleted space. Otherwise the OCCT will often refuse, 
        as the fillet would interfere with an existing hole.
    .. todo:: Allow to specify fillets as "0", which should be converted to "None" in the constructor.
    .. todo:: Reimplement hole_coordinates() using Workplane::rarray(), see 
        https://cadquery.readthedocs.io/en/latest/classreference.html#cadquery.Workplane.rarray
    .. todo:: Extend the hole_coordinates() mechanism to also be able to generated two-dimensional
        hole patterns. A way to specify this would be hole_count = (2,3), meaning 2×3 holes. This 
        also requires to introduce a parameter "hole_margins", because margins between holes and 
        edges can no longer be automatically calculates as for a single line of holes.
    .. todo:: Make it possible to pass in two different lengths for the chamfer. That will allow 
        to create a better support of the core below it, where needed.
    .. todo:: Implement behavior for the angle parameter.
    .. todo:: Implement behavior for the offset parameter.
    .. todo:: Fix that the automatic hole positioning algorithm in hole_coordinates() does not work 
        well when the bracket's footprint is approaching square shape, or higher than wide.
    .. todo: Let this plugin determine its workplane by itself from the edge and face provided as 
        the top and second from top stack elements when called. That is however difficult because 
        the workplane has to be rotated so that the y axis points away from the center of the face 
        on which the bracket is being built.
    """

    def hole_coordinates(width, height, hole_count):
        v_offset = height / 2
        h_offset = width / 2 if hole_count == 1 else v_offset
        h_spacing = 0 if hole_count == 1 else (width - 2 * offset) / (hole_count - 1)
        points = []

        # Go row-wise through all points from bottom to top and collect their coordinates.
        # (Origin is assumed in the lower left of the part's back surface.)
        for column in range(hole_count):
            points.append((
                h_offset + column * h_spacing,
                v_offset
            ))

        log.info("hole coordinates = %s", points)
        return points

    cq.Workplane.translate_last = translate_last
    cq.Workplane.fillet_if = fillet_if
    cq.Workplane.chamfer_if = chamfer_if
    cq.Workplane.show_local_axes = show_local_axes

    # todo: Raise an argument error if both edge_fillet and edge_chamfer is given.
    # todo: Raise an argument error if both corner_fillet and corner_chamfer is given.

    result = self.newObject(self.objects)

    # Debug helper. Can only be used when executing utilities.py in cq-editor. Must be disabled 
    # when importing utilities.py, as it will otherwise cause "name 'show_object' is not defined".
    # result.show_local_axes()

    # Determine the CadQuery primitive "Plane" object wrapped by the Workplane object. See: 
    # https://cadquery.readthedocs.io/en/latest/_modules/cadquery/cq.html#Workplane
    plane = result.plane

    # Calculate various local directions as Vector objects using global coordinates.
    # 
    # We want to convert a direction from local to global coordinates, not a point. A 
    # direction is not affected by coordinate system offsetting, so we have to undo that 
    # offset by subtracting the converte origin.
    #
    # todo: Put these as lambdas / functions into the global namespace of this file, as they are 
    #     generally useful.
    dir_min_x  = plane.toWorldCoords((-1, 0, 0))  - plane.toWorldCoords((0,0,0))
    dir_max_x  = plane.toWorldCoords(( 1, 0, 0))  - plane.toWorldCoords((0,0,0))
    dir_min_y  = plane.toWorldCoords(( 0,-1, 0))  - plane.toWorldCoords((0,0,0))
    dir_max_y  = plane.toWorldCoords(( 0, 1, 0))  - plane.toWorldCoords((0,0,0))
    dir_min_z  = plane.toWorldCoords(( 0, 0,-1))  - plane.toWorldCoords((0,0,0))
    dir_max_z  = plane.toWorldCoords(( 0, 0, 1))  - plane.toWorldCoords((0,0,0))
    dir_min_xz = plane.toWorldCoords((-1, 0,-1))  - plane.toWorldCoords((0,0,0))

    result = (
        result
        
        # Create the bracket's cuboid base shape.
        .union(
            cq.Workplane()
            .copyWorkplane(result)
            .center(0, -thickness / 2)
            .box(width, thickness, height)
            # Raise the created box (dir_max_z in local coordinates). Since translate() requires 
            # global coordinates, we have to use converted ones.
            .translate_last(dir_max_z * (height / 2))
        )

        # Cut the hole pattern into the bracket.
        # It's much easier to transform the workplane rather than creating a new one. Because for 
        # a new workplane, z and x are initially aligned with respect to global coordinates, so the 
        # coordinate system would have to be rotated for our needs, which is complex. Here we modify 
        # the workplane to originate in the local bottom left corner of the bracket base shape.
        .transformed(offset = (-width / 2, 0), rotate = (90,0,0))
        .pushPoints(hole_coordinates(width, height, hole_count))
        .circle(hole_diameter / 2)
        .cutThruAll()

        # Fillets and chamfers.
        # The difficulty here is that we can't use normal CadQuery string selectors, as these always 
        # refer to global directions, while inside this method we can only identify the direction 
        # towards the bracket in our local coordinates. So we have to use the underlying selector 
        # classes, and also convert from our local coordinates to the expected global ones manually.

        # Add a fillet along the bracketed edge if desired.
        .faces(cqs.DirectionNthSelector(dir_max_y, -2))
        # As a bracket on the other side might be present, we have to filter the selected faces 
        # further to exclude that.
        .faces(cqs.DirectionMinMaxSelector(dir_max_z))
        .edges(cqs.DirectionMinMaxSelector(dir_min_z))
        .fillet_if(edge_fillet is not None, edge_fillet)

        # Add a chamfer along the bracketed edge if desired.
        .faces(cqs.DirectionNthSelector(dir_max_y, -2))
        .edges(cqs.DirectionMinMaxSelector(dir_min_z))
        .chamfer_if(edge_chamfer is not None, edge_chamfer)

        # Treat the bracket corners with a fillet if desired.
        .faces(cqs.DirectionMinMaxSelector(dir_max_z))
        .edges( # String selector equivalent in local coords: "<X or >X"
            cqs.SumSelector(
                cqs.DirectionMinMaxSelector(dir_min_x),
                cqs.DirectionMinMaxSelector(dir_max_x)
            )
        )
        .fillet_if(corner_fillet is not None, corner_fillet)

        # Treat the bracket corners with a chamfer if desired.
        .faces(cqs.DirectionMinMaxSelector(dir_max_z))
        .edges( # String selector equivalent in local coords: "<X or >X"
            cqs.SumSelector(
                cqs.DirectionMinMaxSelector(dir_min_x),
                cqs.DirectionMinMaxSelector(dir_max_x)
            )
        )
        .chamfer_if(corner_chamfer is not None, corner_chamfer)
    )
    return result


def test_bracket():
    cq.Workplane.bracket = bracket
    cq.Workplane.transformedWorkplane = transformedWorkplane

    result = (
        cq.Workplane()
        .box(10, 10, 2)

        # Provide the expected workplane to bracket().
        # Creating a workplane on an edge puts the origin at the center of the edge, as needed here.
        # Different options are provided to test brackets on all edges of the top and bottom faces.
        #
        #.faces(">Z").edges("<X").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 90)
        #.faces(">Z").edges(">X").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 270)
        #.faces(">Z").edges("<Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 180)
        .faces(">Z").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 0)
        #
        #.faces("<Z").edges("<X").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 90)
        #.faces("<Z").edges(">X").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 270)
        #.faces("<Z").edges("<Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 0)
        #.faces("<Z").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 180)
        #
        #.faces("<X").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 90)
        #.faces("<X").edges("<Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 270)
        #.faces("<X").edges("<Z").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 180)
        #.faces("<X").edges(">Z").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 0)

        .bracket(
            thickness = 1, height = 5, width = 10, 
            hole_count = 2, hole_diameter = 1,
            edge_fillet = 1.2,
            corner_fillet = 1.2
        )

        .faces("<Z").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 180)
        .bracket(
            thickness = 1, height = 5, width = 10, 
            hole_count = 2, hole_diameter = 1,
            edge_fillet = 1.2,
            corner_fillet = 1.2
        )
    )
    show_object(result)

#test_bracket()


def first_solid(self):
    return self.newObject([self.findSolid()])


def test_first_solid():
    cq.Workplane.first_solid = first_solid

    result = (
        cq.Workplane("XY")
        .box(10,10,5)
        .faces(">Z")
        .workplane()
        .first_solid()
        .faces("<Z")
    )
    show_object(result)

#test_first_solid()


def angle_sector(self, radius, start_angle, stop_angle, forConstruction = False):
    """
    A CadQuery plugin to create a 2D circle sector based on two angles, for each element on the 
    stack. The elements on the stack are converted to points, which are then used as the centers 
    for creating the sectors.
    """

    center_angle = (start_angle + stop_angle) / 2

    origin =     cq.Vector(0, 0, 0)
    arc_start =  cq.Vector(cos(radians(start_angle)) * radius, sin(radians(start_angle)) * radius, 0)
    arc_center = cq.Vector(cos(radians(center_angle)) * radius, sin(radians(center_angle)) * radius, 0)
    arc_end =    cq.Vector(cos(radians(stop_angle)) * radius, sin(radians(stop_angle)) * radius, 0)

    sector = cq.Wire.assembleEdges([
        cq.Edge.makeLine(origin, arc_start),
        cq.Edge.makeThreePointArc(arc_start, arc_center, arc_end),
        cq.Edge.makeLine(origin, arc_end),
    ])
    sector.forConstruction = forConstruction

    return self.eachpoint(lambda vector: sector.moved(vector), True)


def test_angle_sector():
    cq.Workplane.angle_sector = angle_sector

    result = (
        cq.Workplane("XY")
        .pushPoints([(0,0,0), (0,6,0)])
        .angle_sector(5, 45, 135)
        .extrude(1)
    )
    show_object(result)

#test_angle_sector()


def point_sector(self, arc_angle, forConstruction = False):
    """
    A CadQuery plugin to create 2D circle sectors based on (1) the center of the workplane, used as 
    the center of the sector circle, (2) a given point at the center of the arc and (3) a given 
    angle. One sector is created for each element on the stack. The elements on the stack are 
    converted to points, which are then used as the arc center points for creating the sectors.
    """

    def make_point_sector(arc_center_loc):

        # Convert arc_center_loc from type Location to Vector.
        # This is a complex conversion: cq.Location → TopLoc_Location → gp_Trsf → gp_Pnt → cq.Vector
        # Documentation:
        #   https://dev.opencascade.org/doc/refman/html/class_top_loc___location.html
        #   https://dev.opencascade.org/doc/refman/html/classgp___trsf.html
        #   https://dev.opencascade.org/doc/refman/html/classgp___pnt.html
        arc_center_transf = arc_center_loc.wrapped.Transformation()
        arc_center_point = gp_Pnt() # Create a point at the origin.
        arc_center_point.Transform(arc_center_transf)
        arc_center = cq.Vector(arc_center_point)

        angle = radians(arc_angle)
        origin = cq.Vector(0, 0, 0)

        # arc_start and arc_end are arc_center point rotated by 1/2 the arc's angle.
        # Using point rotation formula from https://matthew-brett.github.io/teaching/rotation_2d.html
        arc_start = cq.Vector(
            cos(-angle / 2) * arc_center.x - sin(-angle / 2) * arc_center.y,
            sin(-angle / 2) * arc_center.x + cos(-angle / 2) * arc_center.y,
            0
        )
        arc_end = cq.Vector(
            cos(angle / 2) * arc_center.x - sin(angle / 2) * arc_center.y,
            sin(angle / 2) * arc_center.x + cos(angle / 2) * arc_center.y,
            0
        )

        sector = cq.Wire.assembleEdges([
            cq.Edge.makeLine(origin, arc_start),
            cq.Edge.makeThreePointArc(arc_start, arc_center, arc_end),
            cq.Edge.makeLine(origin, arc_end),
        ])
        sector.forConstruction = forConstruction

        return sector

    return self.eachpoint(make_point_sector, True)


def test_point_sector():
    cq.Workplane.point_sector = point_sector

    model = (
        cq.Workplane("XY")
        .polygon(nSides = 7, diameter = 30, forConstruction = True)
        .vertices()
        .point_sector(30)
        .extrude(1)
    )
    show_object(model)


    model = (
        cq.Workplane("XY")
        .pushPoints([(5,0,0), (0,10,0), (-15,0,0), (0,-20,0)])
        .point_sector(30)
        .extrude(1)
        .translate([0,0,20])
    )
    show_object(model)

#test_point_sector()


def shaft_outline(self, diameter, flatten = 0):
    radius = diameter / 2

    # Case for a circular shaft outline.
    if flatten == 0:
        return self.newObject(self.circle(radius).objects)
    
    # Case for a D-shaped shaft outline.

    flatten_start_x = radius - flatten
    flatten_start_y = sqrt(radius ** 2 - (radius - flatten) ** 2) # Applied Pythagoras.
    flatten_start_point = (flatten_start_x,  flatten_start_y)
    flatten_end_point =   (flatten_start_x, -flatten_start_y)

    outline = (
        self
        .newObject(self.objects)
        .moveTo(*flatten_start_point)
        .threePointArc((-radius, 0), flatten_end_point)
        .close()
    )

    return outline


def test_shaft_outline():
    cq.Workplane.shaft_outline = shaft_outline
    #show_object(cq.Workplane("XY").shaft_outline(10, 1.5))
    show_object(cq.Workplane("XY").shaft_outline(10, 0))

#test_shaft_outline()


def shaft(self, height, diameter, flatten, top_diameter = None):
    """
    CadQuery plugin to create a shaft or shaft hole shape.

    :param height: todo
    :param diameter: todo
    :param flatten: todo
    :param top_diameter: When specifying this, a flat top section of this reduced diameter will be 
        generated so that it has a 45° edge towards the lower outline of full diameter. This allows 
        to create FDM 3D printable shaft holes, with top_diameter being the printer's max. bridging 
        distance; the shaft cannot be inserted to the very end of such a hole, obviously, as there 
        is a conical section at its end.
    """
    cq.Workplane.shaft_outline = shaft_outline

    top_height = None
    if top_diameter is not None:
        top_height = (diameter - top_diameter) / 2
        height = height - top_height
        top_flatten = flatten - (diameter - top_diameter)
        # When generating a lofted shape, having matching edge counts on outlines helps the 
        # algorithm to create the desired shape as it can match edges between lower and upper outline.
        # So we never use a circular upper outline, but one with a very small flattened part.
        if top_flatten < 0: top_flatten = 0.001

    shaft = (
        self
        .shaft_outline(diameter, flatten)
        .extrude(height)
    )

    if top_height is not None:
        shaft = (
            shaft
            .faces(">Z").wires().toPending()
            .workplane(top_height)
            .shaft_outline(top_diameter, top_flatten)
            .loft()
        )

    return self.newObject(shaft.objects)


def test_shaft():
    cq.Workplane.shaft = shaft
    show_object(cq.Workplane("XY").shaft(height = 25, diameter = 10, flatten = 1.5, top_diameter = 4))

#test_shaft()


def bolt_dummy(self, bolt_size, head_size, nut_size, 
    clamp_length, head_length, nut_length = 0, protruding_length = 0, head_shape = "round"
):
    def bolthead(self, size, length, shape = "round"):
        if shape == "round":
            return self.newObject(
                self
                .circle(size / 2)
                .extrude(length)
                .objects
            )
        else:
            # polygon() requires the excircle diameter exd, which we have to calculate from nut size ns:
            # (1) Nut size ns is twice the height h of the six equilateral triangles making up the 
            # hexagon: ns = 2 * h
            # (2) The height of the triangles is, with s the side length of the triangles, according 
            # to https://math.stackexchange.com/a/1766919 : h = sqrt(3)/2 * s
            # (3) Resolving (2) for s yields: s = 2 * h / sqrt(3)
            # (4) Equation (1) in (3) yields: s = ns / sqrt(3)
            # (5) Excircle diameter is twice the side length s in a regular polygon: exr = 2 * s
            # (6) Equation (4) in (5) yields: exr = 2 * ns / sqrt(3)
            #return self.newObject(self.polygon(6, 2 * size / sqrt(3)).extrude(length).objects)
            return self.newObject(
                self
                .polygon(6, 2 * size / sqrt(3))
                .extrude(length)
                .objects
            )

    def nut_if(self, condition, size, length):
        if condition:
            nut = self.polygon(6, 2 * size / sqrt(3)).extrude(length) # See bolthead() why size / sqrt(3).
            return self.newObject(nut.objects)
        else:
            return self.newObject([self.findSolid()])

    cq.Workplane.extrude_if = extrude_if
    cq.Workplane.bolthead = bolthead
    cq.Workplane.nut_if = nut_if

    # Determine the CadQuery primitive "Plane" object wrapped by the Workplane object. See: 
    # https://cadquery.readthedocs.io/en/latest/_modules/cadquery/cq.html#Workplane
    plane = self.plane
    # Determine local directions to use in selectors. ">Z" and "<Z" string selectors cannot be used 
    # as they always refer to global coordinates.
    dir_min_z  = plane.toWorldCoords(( 0, 0,-1))  - plane.toWorldCoords((0,0,0))
    dir_max_z  = plane.toWorldCoords(( 0, 0, 1))  - plane.toWorldCoords((0,0,0))

    bolt = (
        self
        .circle(bolt_size / 2)
        .extrude(clamp_length / 2, both = True)
        # Create the bolt head.
        #.faces(">Z").workplane()
        .faces(cqs.DirectionMinMaxSelector(dir_max_z)).workplane()
        .bolthead(head_size, head_length, head_shape)
        # Create the bolt nut and bolt beyond the nut.
        # With workplane(), a workplane will be created on the <Z face, with its normal aligned with 
        # that face's normal, which is essential for the extrusion direction of what follows. Without 
        # workplane(), the existing workplane will be moved to that face, not changing the normal.
        #.faces("<Z").workplane()
        .faces(cqs.DirectionMinMaxSelector(dir_min_z)).workplane()
        .nut_if(nut_size is not None and nut_length != 0, nut_size, nut_length)
        #.faces("<Z")
        .faces(cqs.DirectionMinMaxSelector(dir_min_z))
        .circle(bolt_size / 2)
        .extrude_if(protruding_length > 0, protruding_length)
    )

    return self.newObject(bolt.objects)


def test_bolt_dummy():
    cq.Workplane.bolt_dummy = bolt_dummy

    box = cq.Workplane("XY").box(24,24,24)
    bolt = cq.Workplane("XZ").bolt_dummy(
        bolt_size = 6, head_size = 9, nut_size = 9, clamp_length = 20, head_length = 4, 
        nut_length = 4, protruding_length = 6, head_shape = "round"
    )
    show_object(bolt.translate((0,0,20)))
    show_object(box.cut(bolt))

#test_bolt_dummy()
