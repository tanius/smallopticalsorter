import cadquery as cq
import logging
import importlib
import utilities # Local directory imports.

# Selectively reload imports to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
importlib.reload(utilities)


class Case:
    def __init__(self, workplane, measures):
        """
        A generic cuboid case with horizontal walls overlapping all others, as needed for stacking 
        stability.

        :param workplane: The workplane to use as a base plate for creating the case on.
        :param measures: The measures to use for the parameters of this design. Keys and defaults:
            - **``w``:** Outer width (x axis measure) of the case.
            - **``d``:** Outer depth (y axis measure) of the case.
            - **``h``:** Outer height (z axis measure) of the case.
            - **``wall_thickness``:** Wall thickness of the panel material to use for the case.

        .. todo:: Implement an option to create a case with the left side wall opened 180°.
        """

        self.model = workplane

        # Save directly specified measures.
        self.w = float(measures["w"])
        self.d = float(measures["d"])
        self.h = float(measures["h"])
        self.wall_thickness = float(measures["wall_thickness"])
        self.nothing = 0.01 # Used as a small gap to prevent overlaps of objects.

        self.build()

    def build_x_wall(self, name):
        offset = (self.w - self.wall_thickness) / 2 + self.nothing
        if name == "left": offset = -1 * offset
        
        return (cq.Workplane("YZ")
            .box(self.d, self.h - 2 * self.wall_thickness, self.wall_thickness)
            .translate((offset, 0, 0))  # In global coordinates!
        )
    
    def build_y_wall(self, name):
        offset = (self.d - self.wall_thickness) / 2 + self.nothing
        # Indeed, front is negative direction from XZ plane!
        if name == "front": offset = -1 * offset
        
        return (cq.Workplane("XZ")
            .box(self.w - 2 * self.wall_thickness, self.h - 2 * self.wall_thickness, self.wall_thickness)
            .translate((0, offset, 0))  # In global coordinates!
        )
    
    def build_z_wall(self, name):
        offset = (self.h - self.wall_thickness) / 2 + self.nothing
        if name == "top": offset = -1 * offset
        
        return (cq.Workplane("XY")
            .box(self.w, self.d, self.wall_thickness)
            .translate((0, 0, offset))  # In global coordinates!
        )

    def build(self):
        self.left_wall   = self.build_x_wall("left")
        self.right_wall  = self.build_x_wall("right")
        self.front_wall  = self.build_y_wall("front")
        self.back_wall   = self.build_y_wall("back")
        self.top_wall    = self.build_z_wall("top")
        self.bottom_wall = self.build_z_wall("bottom")

        self.model = (
            self.model
            .union(self.left_wall)
            .union(self.right_wall)
            .union(self.front_wall)
            .union(self.back_wall)
            .union(self.top_wall)
            .union(self.bottom_wall)
        )


# =============================================================================
# Part Creation
# =============================================================================

cq.Workplane.part = utilities.part

# True to be able to export everything in a single STEP file. False to be able to selectively show 
# and hide objects in cq-editor.
union_results = False
show_options = {"color": "orange", "alpha": 0}
measures = dict(
    w = 130,
    d = 350, 
    h = 130, 
    wall_thickness = 3
)

if union_results:
    # Create case as a cq.Workplane object.
    case = cq.Workplane("XY").part(Case, measures)
    show_object(case,             name = "case",        options = show_options)
else:
    # Create case as a Case object to get access to its parts.
    case = Case(cq.Workplane("XY"), measures)
    
    show_object(case.left_wall,   name = "left_wall",   options = show_options)
    show_object(case.right_wall,  name = "right_wall",  options = show_options)
    show_object(case.front_wall,  name = "front_wall",  options = show_options)
    show_object(case.back_wall,   name = "back_wall",   options = show_options)
    show_object(case.top_wall,    name = "top_wall",    options = show_options)
    show_object(case.bottom_wall, name = "bottom_wall", options = show_options)
