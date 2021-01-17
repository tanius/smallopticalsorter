def m(id, part = None):
    """
    Provide any measure (that we know of) about this design. This acts as a 
    central registry for measures to not clutter the global namespace. "m" for "measure".
    Most numbers can be adjusted, allowing customization beyond the rather simple parameters in 
    the OpenSCAD Customizer.

    Keeping all measures in one file is the simplest way to ensure we'll not have 
    conflicting definitions of `m()` when using `include <>` to import a base design. It also 
    allows any measure to depend on any other measure, since they are all defined here.
    
    :param id: String identifier of the dimension to retrieve. Look into the source to see 
        which are available.
    :param part: A string identifying the part for which the measure ID is specified. If not given, 
        the value will be taken from special variable `$part`. This allows you to set a default 
        part context as `$part = …;` for all subsequent `m()` calls in a file, or as `let($part = …)`
        for a few subsequent calls. For any of these calls, you can override the part context using 
        `m(part = "{partname}", "{id}").
   
    .. todo:: For more readable calls, use a string that combines part name and ID. So 
        m("socket: w") instead of m(part = "socket", "w"). But keep the $part mechanism, which makes 
        it unnecessary to specify the part name in the string when setting $part before.
    .. todo:: If part != undef, prepend "$part: " to id. This implements the calls of the style 
        m("part: measure").
    """

    # Global measures of standard materials used.

    # 3 mm polycarbonate walls are enough for this small machine.
    if   id == "general: panel t":        return 3
    # Default wall thickness for 3D printing (6 shells of 0.4 mm).
    elif id == "general: fdm wall t":     return 3
    # M4 as standard bolt size.
    elif id == "general: bolt t":         return 4
    # Outer diameter of EN 1451 DN32 tubes.
    elif id == "general: tube r":         return 32
    # Using EN 1451 DN32 tubes.
    elif id == "general: tube wall t":    return 3
    
    # Measures for the case and its edge profiles.

    # Width to fit 4 into 600x400 mm Euroboxes, usually ≥550 mm wide inside but with rounded corners.
    elif id == "case: w":                 return 135
    # Depth to fit into 600x400 mm Euroboxes, usually ≥360 mm deep inside but with rounded corners.
    elif id == "case: d":                 return 350
    # 20 mm max. space for protruding elements.
    elif id == "case: h":                 return m("case: cuboid h") + 20
    # todo:: Calculate as "max w - protruding parts".
    elif id == "case: cuboid w":          return m("case: w") - 15
    # todo:: Calculate as "max d - protruding parts".
    elif id == "case: cuboid d":          return m("case: d") - 20
    # Wall height is calculated so that side and top walls are of the same size. 
    # (Top walls overlap side walls.)
    elif id == "case: cuboid h":          return m("case: cuboid w") + 2 * m("general: panel t")
    elif id == "case: cuboid inner w":    return m("case: cuboid w") - 2 * m("general: panel t")
    elif id == "case: cuboid inner d":    return m("case: cuboid d") - 2 * m("general: panel t")
    elif id == "case: cuboid inner h":    return m("case: cuboid h") - 2 * m("general: panel t")
    # Based on how the walls overlap, this results in different measures for the individual pairs 
    # of walls. (Top walls overlap side walls, left and right walls overlap front and back walls.)
    # todo:: Outsource these calculations into generic_case.scad, where they are contained 
    #     redundantly right now.
    elif id == "case: leftright walls w": return m("case: cuboid d")
    elif id == "case: leftright walls h": return m("case: cuboid h") - 2 * m("general: panel t")
    elif id == "case: frontback walls w": return m("case: cuboid w") - 2 * m("general: panel t")
    elif id == "case: frontback walls h": return m("case: cuboid h") - 2 * m("general: panel t")
    elif id == "case: topbottom walls w": return m("case: cuboid w")
    elif id == "case: topbottom walls h": return m("case: cuboid d")
                                          
    # Measures for the case hinges.
    # @todo

    # Measures for the power inlet.
    # @todo

    # Measures for the control panel.
    # @todo

    # Measures for the inlet tube.
    # @todo

    # Measures for the upper belt.
    # @todo Use named parameters in the calculation. 1 + 1 are gaps of 1 mm between belt and 
    #   guide / wall.
    # @todo Use m("upper belt: sidewall t") instead of m("general: panel t").
    #
    # The actual belt width should not be larger than the input tube width, as any wider belt only leads 
    # to possibilities for more beans falling at the same time, which is what we want to minimize.
    elif id == "upper belt: belt w":      return m("general: tube r")
    elif id == "upper belt: w":           return (
        m("general: panel t") + 1 + m("upper belt: belt w") + 1 + m("general: panel t")
    )

    # Measures for the funnel between upper and lower belt.
    elif id == "funnel: h":               return m("case: cuboid inner h") * 0.5
    # 2 mm gaps on each side to the belt structure.
    elif id == "funnel: upper w":         return (
        m("general: fdm wall t") + 2 + m("upper belt: w") + 2 + m("general: fdm wall t")
    )
    elif id == "funnel: lower w":         return m("lower belt: belt w")
    elif id == "funnel: input cutout w":  return 1 + m("upper belt: w") + 1
    elif id == "funnel: input cutout h":  return 30
    # x axis offset of the output relative to being centered below the input.
    elif id == "funnel: output w offset": return 0
    # y axis offset of the output relative to a vertical wall going down from the input.
    elif id == "funnel: output d offset": return 30

    # Measures for the lower belt.
    # To keep the design and spare part management simple, all belts have the same width, allowing 
    # to share roller parts, belt material etc. between them.
    elif id == "lower belt: w":           return m("upper belt: w")
    elif id == "lower belt: belt w":      return m("upper belt: belt w")
    # @todo

    # Measures for the camera.
    # @todo

    # Measures for the manipulator.
    # @todo

    # Measures for the side outputs.
    # @todo

    # Measures for the center output.
    # @todo

    # Measures for the electronics enclosure.
    # @todo
