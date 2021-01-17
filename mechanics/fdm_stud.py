import cadquery as cq
from math import sin, cos, radians, sqrt
import logging
import importlib

# Local directory imports.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
import utilities
importlib.reload(utilities)
# In addition to importing whole packages as neededfor importlib.reload(), import some names.
from utilities import circlePoint, optionalPolarLine


class FdmStud:

    def __init__(self, workplane, measures):
        """
        A parametric stud with integrated support that allows FDM 3D printing with any printer 
        capable of 45° overhangs.
        
        :param workplane: The workplane defining the orientation in space to give the stud.
        :param measures: The measures to use for the parameters of this design. Available values and 
            defaults:
            - **``radius``**: The radius to use for the stud profile outline.
            - **``height``**: The height to use for the stud.
        
        .. todo:: Make the overhang angle configurable, as the studs might not always be printed in 
            horizontal orientation.
        .. todo:: Make it configurable if the bottom (on the xy plane) should be the large or small 
            face. Both can be useful. It's the small face now. However, better let client code 
            rotate the part as needed using rotateAboutCenter().
        """
        
        def profile(self, radius, support_d):
            """
            A CadQuery plugin used exclusively inside FdmStud to create the profile outlines of the 
                stud.
            :param self: The CadQuery parent Workplane object to work with. This is NOT our FdmStud 
                object, as we're an inner function, not a method.
            :param radius: Radius to use for the stud profile outline.
            :param support_d: Depth of the rectangular part of the stud profile outline, used as 
                support for FDM 3D printing.
            """
        
            # Width of the straight line at the bottom of the support.
            # Imagine the circle with two tangents that meet at 90°. support_w is the line between 
            # the points where the tangents meet, forming a triangle with them. The other two sides 
            # of the triangle are of length radius, so Pythagoras lets us solve for support_w.
            support_w = sqrt(2 * radius * radius)
            
            profile = (
                self
                # Workplane transformation relative to global coordinates, to provide the result 
                # along the depth axis(y) while allowing to work with a more comfortable local 
                # coordinate system in this method.
                .transformed(rotate = cq.Vector(0, 0, 45))
                .moveTo(0, -radius)
                .threePointArc(circlePoint(radius, 45), (-radius, 0))
                .optionalPolarLine(support_d, -135)
                .optionalPolarLine(support_w, -45)
                .close()
            )
            
            # In CadQuery plugins, it is good practice to not modify self, but to return a new 
            # object linke to self as a parent: 
            # https://cadquery.readthedocs.io/en/latest/extending.html#preserving-the-chain . Among 
            # other things, this prevents side effects for the calling code when a plugin transforms 
            # its coordinate system (as above). Note tat profile.objects includes all objects on the 
            # stack, not ctx.pendingWires. However by executing .profile(), a wire is added to the 
            # stack, and CadQuery then adds it automatically to the calling Workplane's 
            # ctx.pendingWires.
            return self.newObject(profile.objects)
        
        self.radius = float(measures["radius"])
        self.height = float(measures["height"])
        self.model = workplane
        
        cq.Workplane.optionalPolarLine = optionalPolarLine
        cq.Workplane.profile = profile
        
        self.build()


    def build(self):
        self.model = (
            self.model
            # We need a minimal support height to guarantee that the upper and lower stud profile 
            # have an identical number of edges. That makes lofting predictable, like an extrusion 
            # with a cutoff in this case. With unequal numbers of edges, loft() would choose by 
            # itself which to combine, resulting in a weird shape.
            .profile(radius = self.radius, support_d = 0.01) # lower profile
            # support height == stud height to get a 45° angle
            .transformed(offset = cq.Vector(0, 0, self.height))
            .profile(radius = self.radius, support_d = self.height) # upper profile
            .loft(combine = True)
        )


# =============================================================================
# Demo usage
# =============================================================================

# cq.Workplane.part = utilities.part
# fdm_stud = cq.Workplane("XY").part(FdmStud, {"radius": 10, "height": 30})
# show_object(fdm_stud, name = "fdm_stud", options = {"color": "blue", "alpha": 0.9})
