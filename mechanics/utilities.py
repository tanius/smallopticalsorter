import cadquery as cq
import cadquery.selectors as cqs
from math import sqrt, pi, sin, cos, tan, radians, degrees
from random import randrange
from typing import cast, List
import logging
from types import SimpleNamespace
from OCP.gp import gp_Pnt

log = logging.getLogger(__name__)

# TODO: De-register the plugins after use by code here. Otherwise there can be hard-to-debug issues 
#   as the plugin will still appear as registered for client code, and overwriting the registration 
#   is not easily possible from there.
# TODO: Switch from the pluginname_if() and optional_pluginnane() schemes of optional plugin 
#   execution to pluginnname(if = condition, …). "if" would be an optional parameter. If necessary, 
#   these plugins would overwrite default Workplane methods.

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
    Determine the names of user-defined attributes of the given SimpleNamespace object.
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
    :param then_method: Name of the Workplane class' method to execute if the condition applies. This 
        has to be provided as a string, as there is no variable referencing the current state of 
        a chained fluent API call before that chained call has been evaluated completely.
    :param then_args: Hash with keyword arguments to be provided to the specified method flor the 
        "then" case.
    :param else_method: Name of the Workplane class' method to execute if the condition applies. This 
        has to be provided as a string (see on then_method for details).
    :param else_args: Hash with keyword arguments to be provided to the specified method for the 
        "else" case.

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


def tag_if(self, condition, name):
    """
    Tag the current state of the stack if a condition matches; do noting otherwise.

    :param condition: The condition to determine if to execute the tagging operation.
    :param name: The name to use for the tagging.
    """
    if condition:
        return self.tag(name)
    else:
        return self.newObject([self.findSolid()])


def show_local_axes(self, length = 20):
    """
    A CadQuery plugin to visualize the local coordinate system as a help for debugging.

    .. todo:: Fix that this plugin cannot be imported to another file, as then the error 
        message will be "name show_object is not defined", as this file utilities.py is not open in 
        cq-editor. To use this, right now you have to copy the code to your file.
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


def pushVertices(self, pntList):
    """
    Pushes a list of points onto the stack as Vertex objects.
    The points are in the 2D coordinate space of the workplane face.

    :param pntList: a list of points to push onto the stack
    :type pntList: list of 2-tuples of float, in *local* coordinates
    :return: a new workplane with the desired points on the stack as Vertex objects

    A common use is to provide a list of points for a subsequent operation, such as creating
    circles or holes. This example creates a cube, and then drills three holes through it,
    based on three points::

        s = Workplane().box(1,1,1).faces(">Z").workplane().\
            pushPoints([(-0.3,0.3),(0.3,0.3),(0,0)])
        body = s.circle(0.05).cutThruAll()

    Here the circle function operates on all three points, and is then extruded to create three
    holes. See :py:meth:`circle` for how it works.
    """
    vecs: List[cq.Vertex] = []

    for pnt in pntList:
        pnt_vector = self.plane.toWorldCoords(pnt)

        vecs.append(
            cq.Vertex.makeVertex(pnt_vector.x, pnt_vector.y, pnt_vector.z)
        )

    return self.newObject(vecs)


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


def bracket(self, thickness, height, width, offset = 0, angle = 90,
    holes_count = 0, holes_diameter = None, holes_tag = None,
    edge_fillet = None, edge_chamfer = None, 
    corner_fillet = None, corner_chamfer = None
):
    """
    A CadQuery plugin to create an angle bracket along an edge.

    Must be used on a workplane that (1) coincides with the face on which to build the bracket, 
    (2) has its origin at the center of the edge along which to build the bracket and (3) has its 
    x axis pointing along the edge along which to build the bracket and (4) has its y axis pointing 
    away from the center of the face on which to build the bracket.

    The holes are arranged as a line along the longer edge of the bracket.

    :param holes_diameter: The diameter to use for the holes in the bracket. When setting 
        ``holes_count`` to a non-zero value but not specifying holes_diameter, no holes will be 
        drilled but there will be vertices on the stack so that you can drill them yourself later. 
        See parameter ``holes_tag``.
    :param holes_tag: Name to give to the state where the vertices are on the stack as Vertex 
        objects. Can be used to cut the holes again after they have been obstructed by items created 
        after the bracket. Or to cut more custom holes than the plain cylindrical holes created 
        by this plugin. For that, you can select the vertices by tag like this:
        ``result.vertices(tag = holes_tag)``.
    :param …: TODO

    .. todo:: Change the specs for the workplane to provide for this plugin to one on which the 
        thickness (after refactoring: height) parameter goes into the z direction. That is also 
        the workplane for the holes in the bracket, which makes it much easier to tag and reuse 
        a workplane for cutting holes externally, after creating the bracket.
    .. todo:: Adjust the parameter naming to width, depth and height (or thickness). Because the 
        default plane of parts should be XY.
    .. todo:: Add a parameter to support filleting the outer edges, excluding the edges touching 
        the mounting face and edges of holes.
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
    .. todo:: Let this plugin determine its workplane by itself from the edge and face provided as 
        the top and second from top stack elements when called. That is however difficult because 
        the workplane has to be rotated so that the y axis points away from the center of the face 
        on which the bracket is being built.
    .. todo:: Perhaps let this plugin take an edge from the stack and create a bracket along it. 
        Would be easier than providing a workplane as specified now, but might limit its use since 
        sometimes a bracket is needed that does not simply go along a straight edge.
    .. todo:: Leave the cq.Workplane class in the same state as finding it. So if there was no 
        plugin fillet_if() or chamfer_if() registered at the start of the plugin, de-register these 
        again after using them in here. If one was registered, it might be something else by the 
        same name. So it should be renamed temporarily and that state should be restored at the 
        end.
    """

    def hole_coordinates(width, height, hole_count):
        line_length = max(width, height) # Arrange holes in a line along the longer edge.
        # TODO: Make the following two values configurable by a parameter to the plugin and this function.
        hole_hole_distance_factor = 1
        hole_edge_distance_factor = 0.5
        # Example: 5 holes have 4 spaces between them, 1 edge space before and 1 after them.
        distance_count = hole_hole_distance_factor * (hole_count - 1) + hole_edge_distance_factor * 2
        distance_unit = line_length / distance_count
        hole_hole_distance = hole_hole_distance_factor * distance_unit
        hole_edge_distance = hole_edge_distance_factor * distance_unit
        second_dimension_position = min(width, height) / 2

        # Go row-wise through all points from bottom to top and collect their coordinates.
        # (Origin is assumed in the lower left of the part's back surface.)
        points = []
        for column in range(hole_count): # range is 0 ... hole_count -1.
            # Points to be arranged along the width edge.
            if width > height:
                points.append((
                    hole_edge_distance + column * hole_hole_distance,
                    second_dimension_position
                ))
            # Points to be arranged along the height edge.
            else:
                points.append((
                    second_dimension_position,
                    hole_edge_distance + column * hole_hole_distance
                ))
                
        log.info("hole coordinates = %s", points)
        return points

    cq.Workplane.translate_last = translate_last
    cq.Workplane.fillet_if = fillet_if
    cq.Workplane.chamfer_if = chamfer_if
    cq.Workplane.tag_if = tag_if
    cq.Workplane.show_local_axes = show_local_axes
    cq.Workplane.pushVertices = pushVertices
    cq.Workplane.first_solid = first_solid

    # todo: Raise an argument error if both edge_fillet and edge_chamfer is given.
    # todo: Raise an argument error if both corner_fillet and corner_chamfer is given.

    result = self.newObject(self.objects)

    # Debug helper. Can only be used when executing utilities.py in cq-editor. Must be disabled 
    # when importing utilities.py, as it will otherwise cause "name 'show_object' is not defined".
    # result.show_local_axes()

    # Determine the CadQuery primitive "Plane" object wrapped by the Workplane object. See: 
    # https://cadquery.readthedocs.io/en/latest/_modules/cadquery/cq.html#Workplane
    plane = result.plane

    # Create a random holes tag name if none was supplied, as we'll need it also internally in this 
    # method.
    holes_tag_randomness = randrange(100000)
    holes_tag = holes_tag if holes_tag is not None else f"bracket_holes_{holes_tag_randomness}"

    # Calculate various local directions as Vector objects using global coordinates.
    # 
    # We want to convert a direction from local to global coordinates, not a point. A 
    # direction is not affected by coordinate system offsetting, so we have to undo that 
    # offset by subtracting the converted origin.
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
    )

    # Fillets and chamfers.
    # The difficulty here is that we can't use normal CadQuery string selectors, as these always 
    # refer to global directions, while inside this method we can only identify the direction 
    # towards the bracket in our local coordinates. So we have to use the underlying selector 
    # classes, and also convert from our local coordinates to the expected global ones manually.
    result = (
        result
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

    # Add the hole pattern as tagged Vertex objects.
    if holes_count > 0:
        result = (
            result
            # It's much easier to transform the workplane rather than creating a new one. Because for 
            # a new workplane, z and x are initially aligned with respect to global coordinates, so the 
            # coordinate system would have to be rotated for our needs, which is complex. Here we modify 
            # the workplane to originate in the local bottom left corner of the bracket base shape.
            .transformed(offset = (-width / 2, 0), rotate = (90, 0, 0))
            .pushVertices(hole_coordinates(width, height, holes_count))
            .tag_if(holes_tag is not None, holes_tag)
            .first_solid()
        )

    # Cut the hole pattern into the object, if desired.
    # Done last, as sometimes the holes might have to go through the main fillet added above. Also 
    # this order prevents CAD kernel issues, as OCCT cannot create a fillet that partially overlaps 
    # an existing hole.
    # TODO: If we had a circle_for_vertices() plugin that would only create a circle around vertices, 
    #   not around the origin in the absence of vertices, we'd not need an if statement here. Then, 
    #   if pushPoints() provides no points, no holes are cut. However, it is not yet clear if 
    #   cutThruAll() would indeed do nothing when no wire is in pendingWires.
    if holes_diameter is not None and holes_diameter > 0:
        result = (
            result
            .vertices(tag = holes_tag)
            .circle(holes_diameter / 2)
            .cutThruAll()
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
            thickness = 1, 
            height = 10, width = 5, # Also to test: height = 5, width = 10,
            holes_count = 2, holes_diameter = None, holes_tag = "bracket_hole_points_1",
            edge_fillet = 1.2,
            corner_fillet = 1.2
        )

        .faces("<Z").edges(">Y").transformedWorkplane(centerOption = "CenterOfMass", rotate_z = 180)
        .bracket(
            thickness = 1, height = 5, width = 10, 
            holes_count = 2, holes_diameter = 1, holes_tag = "bracket_hole_points_2",
            edge_fillet = 1.2,
            corner_fillet = 1.2
        )
    )
    show_object(result, name = "bracket")
    show_object(result.vertices(tag = "bracket_hole_points_1"), name = "bracket_hole_points_1")
    show_object(result.vertices(tag = "bracket_hole_points_2"), name = "bracket_hole_points_2")

#test_bracket()


def angle_sector(self, radius, start_angle, stop_angle, forConstruction = False):
    """
    A CadQuery plugin to create a 2D circle sector based on two angles, for each element on the 
    stack. The elements on the stack are converted to points, which are then used as the centers 
    for creating the sectors.

    .. todo:: Fix that the numerically smaller angle is always used as the start angle, independent 
        of which angle is given for the start_angle and which is given for the stop_angle 
        parameter. So when specifying "start_angle = 270, stop_angle = 90", this is interpreted as 
        "start_angle = 90, stop_angle = 270" and one has to use the workaround 
        "start_angle = -90, stop_angle = 90" to get the desired effect.
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
        outline = self.newObject(self.circle(radius).objects)
    
    # Case for a D-shaped shaft outline.
    else:
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


def nut_hole(self, size, length, rotation = None, condition = None):
    """
    CadQuery plugin to cut a hole for inserting a hexagonal nut.

    .. todo:: Rename "length" to "depth", since it's about the depth of a hole.
    .. todo:: Make the (then called) depth parameter optional. If not given, the hole would go 
        through the hole part. See the CadQuery cskHole() plugin for how to do that.
    """

    if condition is not None and condition == False:
        return self.newObject([self.findSolid()])

    if rotation is None: rotation = 0

    # polygon() requires the excircle diameter exd, which we have to calculate from nut size ns:
    # (1) Nut size ns is twice the height h of the six equilateral triangles making up the 
    # hexagon: ns = 2 * h
    # (2) The height of the triangles is, with s the side length of the triangles, according 
    # to https://math.stackexchange.com/a/1766919 : h = sqrt(3)/2 * s
    # (3) Resolving (2) for s yields: s = 2 * h / sqrt(3)
    # (4) Equation (1) in (3) yields: s = ns / sqrt(3)
    # (5) Excircle diameter is twice the side length s in a regular polygon: exr = 2 * s
    # (6) Equation (4) in (5) yields: exr = 2 * ns / sqrt(3)

    # The cutting object must be created in a position prepare to be used by cutEach() below.
    # Namely, in a local coordinate system, with the origin at the center top of the part.
    nut = (
        cq.Workplane("XY")
        .polygon(6, 2 * size / sqrt(3))
        .extrude(-length)
        .rotate(axisStartPoint = (0.0, 0.0, -1.0), axisEndPoint = (0.0, 0.0, 1.0), angleDegrees = rotation)
    )
    #show_object(nut)
    nut_solid = nut.findSolid()

    # Use the cutter shape to cut at the position of every item on the stack.
    return self.cutEach(lambda loc: nut_solid.moved(loc), useLocalCoords = True)


def test_nut_hole():
    cq.Workplane.nut_hole = nut_hole

    result = (
        cq.Workplane("XY")
        .box(20, 20, 20)
        
        .faces(">Z").workplane()
        .nut_hole(size = 10, length = 7, rotation = 15)

        .faces(">Z").workplane()
        .rect(15, 15, forConstruction = True)
        .vertices()
        .nut_hole(condition = 1<2, size = 3, length = 20)
    )
    show_object(result)

#test_nut_hole()
            

def bolt(self, bolt_size, head_size, nut_size, 
    clamp_length, head_length, nut_length = 0, protruding_length = 0, 
    head_shape = "cylindrical", head_angle = None
):
    """
    CadQuery plugin that provides a bolt shape including a nut, but without a thread. For mockups 
    and to cut holes into parts for inserting parts later.

    :param self: The CadQuery stack, with a workplane origin through which the bolt should go in 
        z direction (i.e. orthogonal to the workplane) and so that half the ``clamp_length`` is 
        above and half below this workplane.
    :param bolt_size: TODO
    :param head_size: TODO
    :param nut_size: TODO
    :param clamp_length: The cylindrical part of the bolt between bolt head and nut, or bolt end. 
        The conical part of a countersunk bolt is not part of clamp_length but of head_length.
    :param head_length: TODO
    :param nut_length: TODO
    :param protruding_length: TODO
    :param head_shape: The type of bolt head to use. Either "cylindrical", "conical" (for a countersunk 
        bolt) or "hexagonal".

    .. todo:: Allow specifying head_length = 0 to create a bolt without a head, for example to cut 
        a cylindrical hole with added nut hole.
    .. todo:: Add rendering of threads, but optionally so that one can also still use the shape for 
        cutting bolt holes or for simplified renderings.
    """

    def bolthead(self, size, length, shape = "hexagonal", angle = None, bolt_size = None):
        """
        A CadQuery plugin to generate a bolthead shape.

        :param self: The CadQuery stack, with a workplane that represents the upper surface of the 
            bolt to be created, with the positive Z axis pointing into the bolt direction.
        :param size: The nut size (measure between flats) for a hexagonal bolt head, or the diamater 
            for a cylindrical or conical bolt head.
        :param length: Length of the bolt head. If a conical bolt head is desired and the length 
            is longer than can be fit in a truncated cone with diameters ``size`` and ``bolt_size`` 
            and tip angle ``angle``, then a part of the bolt head will be cylindrical.
        :param shape: Shape of the bolt head. Can be "hexagonal", "cylindrical", "conical".
        :param angle: Only needed for a conical bolt head. The head angle of a conical bolt, 
            measured at the tip of the cone.
        :param bolt_size: Only needed for a conical bolt head. The diameter of the bolt.
        """

        if shape == "cylindrical":
            return self.newObject(
                self
                .circle(size / 2)
                .extrude(length)
                .objects
            )
        elif shape == "conical":
            taper_angle = angle / 2
            # The length for the conical part of the extrusion is the height of a truncated cone, 
            # with diameters "size" and "bolt_size". Which itself is the height difference of 
            # a cone with diameter "size" and a cone with diameter "bolt_size". And for the cones, 
            # we can substitute their cross-section triangles.
            bolthead_cone_height = tan(radians(90 - taper_angle)) * size / 2
            boltsize_cone_height = tan(radians(90 - taper_angle)) * bolt_size / 2
            conical_length = bolthead_cone_height - boltsize_cone_height
            # Length of a tapered extrusion is measured along the shape's tapered surface, not along 
            # the extrusion direction. To get a part that measures "length" in extrusion direction, 
            # we have to adapt length accordingly.
            conical_length_for_extrude = conical_length / cos(radians(taper_angle))
            cylindrical_length = length - conical_length
            bolthead = (
                self
                .tag("top_plane")
            )

            if cylindrical_length > 0:
                bolthead = (
                    bolthead
                    .circle(size / 2)
                    .extrude(cylindrical_length)
                    .workplaneFromTagged("top_plane")
                    .workplane(offset = cylindrical_length)
                )
            
            return self.newObject(
                bolthead
                .circle(size / 2)
                .extrude(conical_length_for_extrude, taper = taper_angle) # taper angle is measured against the default, straight extrusion direction.
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
        # Create the cylindrical bolt shape between head and nut.
        .circle(bolt_size / 2)
        .extrude(clamp_length / 2, both = True)
        # Create the bolt head.
        .faces(cqs.DirectionMinMaxSelector(dir_max_z))
        # Note that offset is negative because it has to use the already-inverted workplane.
        .workplane(invert = True, offset = -head_length)
        .bolthead(head_size, head_length, head_shape, head_angle, bolt_size)
        # Create the bolt nut.
        .faces(cqs.DirectionMinMaxSelector(dir_min_z))
        # With workplane(), a workplane will be created on the selected face, with its normal 
        # aligned with that face's normal, which is essential for the extrusion direction of what 
        # follows. Without workplane(), something similar will be called internally, moving the 
        # existing workplane to the selected face but WITHOUT changing the normal. That may be a bug.
        # TODO: If the situation above is a bug, get it fixed in CadQuery.
        .workplane()
        .nut_if(nut_size is not None and nut_length != 0, nut_size, nut_length)
        # Create the bolt part protruding from the nut.
        .faces(cqs.DirectionMinMaxSelector(dir_min_z))
        .circle(bolt_size / 2)
        .extrude_if(protruding_length > 0, protruding_length)
    )

    return self.newObject(bolt.objects)


def test_bolt():
    cq.Workplane.bolt = bolt

    box = cq.Workplane("XY").box(24, 24, 24)
    bolt_shape = cq.Workplane("XZ").bolt(
        bolt_size = 6, 
        head_size = 14,
        nut_size = 9, 
        clamp_length = 20, 
        head_length = 6,
        nut_length = 4, 
        protruding_length = 6, 
        head_shape = "conical", # "cylindrical", "conical" or "hexagonal"
        head_angle = 90
    )
    show_object(bolt_shape.translate((0,0,20)))
    show_object(box.cut(bolt_shape))

#test_bolt()


def distribute_circular(self, distributable, radius, copies, align):
    """
    CadQuery plugin that can distribute copies of a given object in a circle, placing them at the 
    centers of a regular polygon and optionally aligning them to face the center.

    :param distributable: A CadQuery Workplane object containing the solid to distribute on its stack.
    :param radius: Circumradius of the regular polygon to use for distributing the object.
    :param copies: The number of copies to distribute around the circle.
    :param align: Alignment type. Either "default" to use the original orientation of the 
        distributable object, or "center" to let every copy of the object face the center.
    """
    log = logging.getLogger(__name__)

    # Determine the CadQuery primitive "Plane" object wrapped by the Workplane object. See: 
    # https://cadquery.readthedocs.io/en/latest/_modules/cadquery/cq.html#Workplane
    plane = self.plane

    # Positions and rotations for the distributable object when placed at the corners of a regular polygon.
    # Consists of a list of (x, y, center_angle) elements, using local coordinates and degrees.
    transformations = []
    for corner_num in range(copies): # Range 0 to copies - 1.
        delta_angle = 2 * pi / copies # Center angle between two corners. In radians.
        corner_angle = delta_angle * corner_num
        transformation = (
            cos(corner_angle) * radius,
            sin(corner_angle) * radius,
            degrees(corner_angle)
        )
        transformations.append(transformation)
        # log.info("new position: %s", position)

    # Collect a translated and rotated copy of the distributable object for every corner.
    result = self
    for t in transformations:
        angle = t[2] if align == "center" else 0
        position = plane.toWorldCoords((t[0], t[1], 0))

        result = result.union(
            distributable
            .rotate((0, 0, -1), (0, 0, 1), angle)
            .translate(cq.Vector(position))
        )

    # In CadQuery plugins, it is good practice to not modify self, but to return a new object linked 
    # to self as a parent: https://cadquery.readthedocs.io/en/latest/extending.html#preserving-the-chain
    return self.newObject(result.objects)


def toTuple2D(self):
    """
    Extension for cadquery.Vector that provides a 2D tuple rather than a 3D tuple as provided by 
    Vector.toTuple().
    """
    tuple_3d = self.toTuple()
    return (tuple_3d[0], tuple_3d[1])


def cbore_csk_hole(self, diameter, cboreDiameter, cboreDepth, cskDiameter, cskAngle, depth = None, clean = True):
    """
    CadQuery plugin that combines counterbored and countersunk holes into one. It allows to create 
    a hole starting with a cylindrical counterbore, then having a conical countersunk hole, then 
    having the hole for the bolt shaft.

    The surface of the hole is at the current workplane. One hole is created for each item on the 
    stack. With this plugin, both Workplane::cskHole() and Workplane::cboreHole() are unnecessary.
    (At least after teaching this plugin to work with zero depth for either counterbore or countersink.)

    :param diameter: The diameter of the hole for the bolt shaft.
    :param cboreDiameter: The diameter of the cylindrical counterbore hole.
    :param cboreDepth: The depth of the cylinrical counterbore hole.
    :param cskDiameter: The diameter of the conical countersink hole.
    :param cskAngle: The angle (in degrees) of the conical countersink hole, corresponding to the 
        angle at the (imagined) cone tip. Typical values are 90° for metric bolts an 82° for imperial.
    :param depth: The complete depth of the hole, including the counterbore and countersink. Use 
        0 or None to drill thrugh the entire part.
    :param clean: Whether to call `Workplane::clean()` afterwards to have a clean shape.

    .. todo:: Rename to bolt_hole(), since that is what this plugin is about.
    .. todo:: Implement that this plugin can produce also pure counterbore holes or pure countersunk 
        holes.
    .. todo:: Add the ability to also include a nut shape, starting from a certain depth and going 
        until the end of the bolt because that's needed to insert the nut into the part.
    .. todo:: Add the ability to als include a space for a washer below the nut, which means a 
        cylindrical shape rather than a hexagonal one at the end of the bolt.
    """

    if depth is None:
        depth = self.largestDimension()

    center = cq.Vector()
    boreDir = cq.Vector(0, 0, -1)
    csk_position = cq.Location(cq.Vector(0, 0, - cboreDepth))

    # Create the hole shape.
    hole = cq.Solid.makeCylinder(
        diameter / 2.0, depth, center, boreDir  # Uses local coordinates!
    )

    # Create and position the countersink cone shape.
    csk_radius = cskDiameter / 2.0
    csk_height = csk_radius / tan(radians(cskAngle / 2.0))
    csk = (
        cq.Solid
        .makeCone(csk_radius, 0.0, csk_height, center, boreDir)
        .moved(csk_position)
    )

    # Create the counterbore shape.
    cbore = cq.Solid.makeCylinder(cboreDiameter / 2.0, cboreDepth, center, boreDir)

    # Fuse everything together.
    cutter = hole.fuse(cbore).fuse(csk)

    # Use the cutter shape to cut every item on the stack.
    return self.cutEach(lambda loc: cutter.moved(loc), True, clean)


def test_cbore_csk_hole():
    cq.Workplane.cbore_csk_hole = cbore_csk_hole

    result = (
        cq.Workplane("XY")
        .box(24,24,24)
        .faces(">Z")
        .workplane()
        .cbore_csk_hole(
            diameter = 4,
            cboreDiameter = 8,
            cboreDepth = 4,
            cskDiameter = 6,
            cskAngle = 90
        )
    )
    show_object(result)

#test_cbore_csk_hole()


def eachpointAdaptive(
    self,
    callback,
    callback_extra_args = None,
    useLocalCoords = False
):
    """
    Same as each(), except each item on the stack is converted into a point before it
    is passed into the callback function. And it also allows to pass in lists of additional 
    arguments to use for each of the objects to process.

    The resulting object has a point on the stack for each object on the original stack.
    Vertices and points remain a point.  Faces, Wires, Solids, Edges, and Shells are converted
    to a point by using their center of mass.

    If the stack has zero length, a single point is returned, which is the center of the current
    workplane/coordinate system

    :param callback_extra_args: Array of dicts for keyword arguments that will be 
        provided to the callback in addition to the obligatory location argument. The outer array 
        level is indexed by the objects on the stack to iterate over, in the order they appear in 
        the Workplane.objects attribute. The inner arrays are dicts of keyword arguments, each dict 
        for one call of the callback function each. If a single dict is provided, then this set of 
        keyword arguments is used for every call of the callback.
    :param useLocalCoords: Should points provided to the callback be in local or global coordinates.

    :return: CadQuery object which contains a list of vectors (points) on its stack.

    .. todo:: Implement that callback_extra_args can also be a single dict.
    .. todo:: Implement that empty dicts are used as arguments for calls to the callback if not 
        enough sets are provided for all objects on the stack.
    """

    # Convert the objects on the stack to a list of points.
    pnts = []
    plane = self.plane
    loc = self.plane.location
    if len(self.objects) == 0:
        # When nothing is on the stack, use the workplane origin point.
        pnts.append(cq.Location())
    else:
        for o in self.objects:
            if isinstance(o, (cq.Vector, cq.Shape)):
                pnts.append(loc.inverse * cq.Location(plane, o.Center()))
            else:
                pnts.append(o)

    # If no extra keyword arguments are provided to the callback, provide a list of empty dicts as 
    # structure for the **() deferencing to work below without issues.
    if callback_extra_args is None:
        callback_extra_args = [{} for p in pnts]

    # Call the callback for each point and collect the objects it generates with each call.
    res = []
    for i, p in enumerate(pnts):
        p = (p * loc) if useLocalCoords == False else p
        extra_args = callback_extra_args[i]
        p_res = callback(p, **extra_args)
        p_res = p_res.move(loc) if useLocalCoords == True else p_res
        res.append(p_res)

    # For result objects that are wires, make them pending if necessary.
    for r in res:
        if isinstance(r, cq.Wire) and not r.forConstruction:
            self._addPendingWire(r)

    return self.newObject(res)


def test_eachpointAdaptive():
    cq.Workplane.eachpointAdaptive = eachpointAdaptive

    def coin(location, size):
        """
        Create a coin at the given location, with the given size. Suitable as a callback for 
        Workplane::eachpointAdaptive().
        :param location: A cq.Location object defining where to place the center of the coin.
        :param size: A float defining the diameter of the coin.
        """
        return cq.Workplane().circle(size / 2).extrude(-size / 8).val().located(location)

    result = (
        cq.Workplane()
        .workplane(offset = 10)
        .pushPoints([(0, 0), (-2, -5), (10, 10)])
        .eachpointAdaptive(
            coin,
            callback_extra_args = [{"size": 1}, {"size": 5}, {"size": 8}],
            useLocalCoords = False
        )
    )

    show_object(result)

# test_eachpointAdaptive()


def cutEachAdaptive(
    self, 
    callback, 
    callback_extra_args,
    useLocalCoords = False, 
    clean = True
):
    """
    Evaluates the provided function at each point on the stack (using ``eachpoint()``) and then cuts 
    the result from the context solid. In contrast to the normal Workplane::cutEach(), it allows 
    to provide additional arguments to the callback.

    :param callback: A function suitable for use in the eachpoint method: ie, that accepts a 
        Vector object as first parameter, 
    :param useLocalCoords: same as for :py:meth:`eachpoint`
    :param boolean clean: call :py:meth:`clean` afterwards to have a clean shape
    :raises ValueError: if no solids or compounds are found in the stack or parent chain
    :return: a CQ object that contains the resulting solid
    """
    cq.Workplane.eachpointAdaptive = eachpointAdaptive

    context_solid = self.findSolid()

    # Combine all cutter objects into a single compound object.
    results = cast(
        List[cq.Shape], 
        self.eachpointAdaptive(
            callback,
            callback_extra_args,
            useLocalCoords
        ).vals()
    )

    new_solid = context_solid.cut(*results)
    if clean: new_solid = new_solid.clean()

    return self.newObject([new_solid])


def test_cutEachAdaptive():
    cq.Workplane.cutEachAdaptive = cutEachAdaptive

    def cylinder_at(location, diameter, height):
        """
        Create a cylinder at the given location, with the given size. Suitable as a callback for 
        Workplane::eachpointAdaptive().
        :param location: A cq.Location object defining where to place the center of the coin.
        :param diameter: A float defining the diameter of the cylinder.
        :param height: A float defining the heigt of the cylinder.
        """
        return cq.Workplane().circle(diameter / 2).extrude(-height).val().located(location)

    result = (
        cq.Workplane()
        .box(30, 30, 5)
        .translate((0, 0, -2.5))
        .pushPoints([(0, 0), (-2, -5), (10, 10)])
        .cutEachAdaptive(
            cylinder_at,
            callback_extra_args = [{"diameter": 1, "height": 10}, {"diameter": 5, "height": 4}, {"diameter": 8, "height": 10}],
            useLocalCoords = False
        )
    )

    show_object(result)

# test_cutEachAdaptive()
