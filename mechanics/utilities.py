import cadquery as cq
from math import sin, cos, radians
import logging
from types import SimpleNamespace

log = logging.getLogger(__name__)


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
    Get the coordinates of apoint on the circle circumference.
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
    Factory method that lets you create objects from a custom class relative to the current 
    CadQuery workplane, just like you create any other objects in CadQuery's fluid (i.e. 
    JQuery-like) API.

    To use this method, register it as a CadQuery plugin, and supply it with a custom class and 
    a set of class-specific measures defining the part to create. It works for all classes that (1) 
    store the part geometry as a CadQuery Workplane object in attribute `model` and (2) have a 
    constructor with two required parameters: `workplane` to hand the CadQuery workplane to build 
    on, and `measures` to define the part. Usage example: 
    
    ```
    import utilities
    cq.Workplane.part = utilities.part
    my_part = cq.Workplane("XY").part(MyPart, measures).translate((0,0,5))
    ```

    :param self: The CadQuery Workplane object to which this plugin will be attached at runtime.
    :param part_class: Your class used to create your custom part. Provided not as a string, but 
        as the type. If your class has the name "MyPart", you write `MyPart`, not `"MyPart"`.
    :param measures: A dict with the parameters defining the part, to be provided to the constructor 
        of the given class.

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


def sagittaArcOrLine(self, endPoint, sag):
    """
    An arc that can also be a straight line, unlike with the CadQuery core Workplane.sagittaArc().

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
    A configurable U-shaped profile that can be rounded or flat at the bottom, open to +y.

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
    profile = (self
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
    profile = (profile
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
    Creates a solid box around the objects provided on the stack. The box corresponds to the 
    bounding box containing all objects on the stack (both 2D and 3D).
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
    Creates a new 2-D workplane, located relative to the first face on the stack, with additional 
    3D offset and rotation applied.

    This is a shorthand combining Workplane::workplane and Workplane::transformed.

    :param rotate: A 3-tuple giving rotate_x, rotate_y, rotate_z at once.
    :param offset: A 3-tuple giving offset_x, offset_y, offset_z at once.
    :param invert: Invert the z direction from that of the face.
    :param offset_x: Offset along the x axis to transform the workplane center relative to its 
        initial location.
    :param offset_y: Offset along the y axis to transform the workplane center relative to its 
        initial location.
    :param offset_z: Offset along the z axis to transform the workplane center relative to its 
        initial location.
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

    .. todo:: Apply the three rotations all relative to the local coordinate system as it was at 
        the start of this method, not as it was after the previosu rotation. Otherwise rotations 
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
    Cut a groove into the first solid in the current stack, starting from the center resp. location 
    of the first object in the current stack, and into its local x direction.

    :param width: Width of the groove to cut.
    :param depth: Depth of the groove to cut.
    :param length: Length of the groove to cut. Half is cut into +x and half into -x direction. 
        If omitted, the groove is cut past the end of the face, so that all material that such a 
        groove can remove is removed. If the provided face is not on a convex part of the solid, 
        this may have unintended side effects.
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
