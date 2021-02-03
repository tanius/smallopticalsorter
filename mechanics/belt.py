import logging
import importlib
import math
from math import sqrt, asin, degrees

import cadquery as cq
from cadquery import selectors

# Local directory imports.

# Selective reloading to pick up changes made between script executions.
# See: https://github.com/CadQuery/CQ-editor/issues/99#issue-525367146
import utilities
#import fdm_stud
#importlib.reload(utilities)
#importlib.reload(fdm_stud)

# In addition to importing whole packages as neededfor importlib.reload(), import some names.

class Belt:
    def __init__ (self,workplane,measures):
        """
         :param measures : measurement of the bracket:
             bw  : belt width, hence width between the sides
             bh  : bracket height. 
             bl  : bracket length. Since this is half bracket, half the length is used!
             t   : material thickness of the plates
             bd  : bearing diameter
             din : bolt size for connection halves and mounting
        """
        
        self.belt_bracket_motor   = cq.Workplane("XY")
        self.belt_bracket_roller  = cq.Workplane("XY")
        self.motor_roller         = cq.Workplane("XY")
        self.other_roller         = cq.Workplane("XY")
        self.tensioner_left       = cq.Workplane("XY")
        self.tensioner_right      = cq.Workplane("XY")
        self.axis_connector_left  = cq.Workplane("XY")
        self.axis_connector_right = cq.Workplane("XY")
        self.model = workplane

        self.m_din = (3,4,5,6,8,10)
        self.m_nut_size      = (6.1,7.7,8.8,11.1,14.4,18.9)
        self.m_nut_thickness = (2.4,3.2,4.0, 5.0,6.5,8.0)

        self.bw   = float(measures["belt_width"])
        self.bh   = float(measures["bracket_height"])
        self.bl   = float(measures["bracket_length"])/2
        self.t    = float(measures["material_thickness"])
        self.bd   = float(measures["bearing_diameter"])
        self.bt   = float(measures["bearing_thickness"])        
        self.din  = float(measures["bolt_size"])
        self.ad   = float(measures["axis_diameter"])
        self.asd  = float(measures["axis_slide_depth"])
        self.rd   = float(measures["roller_diameter"])
        self.mae  = float(measures["motor_axis_edges"])
        self.mad1 = float(measures["motor_axis_diameter_major"])
        self.mad2 = float(measures["motor_axis_diameter_minor"])
        self.mal  = float(measures["motor_axis_length"])
        self.e    = float(measures["roller_friction_edge"])        
        self.rg   = float(measures["roller_gap"])
        self.td   = int(measures["tensioner_diameter"])
        self.rl   = self.bw - 2*self.rg  # length or a roller
        self.nsp  = 0.2 # space around nut as % of nut size

        if (self.td in self.m_din):
           self.ns = self.m_nut_size[self.m_din.index(self.td)]
           self.nt = self.m_nut_thickness[self.m_din.index(self.td)]
           self.build()

    def build_side(self,name,purpose):
        offset = self.bw/2
        sign = 1
        if name == "left" : sign = -1 
        
        #bracket side plane
        side = cq.Workplane("XZ")\
            .moveTo(-self.bh/2,self.bl-self.bh/2)\
            .sagittaArc((self.bh/2,self.bl-self.bh/2),self.bh/2)\
            .lineTo(self.bh/2,0)\
            .lineTo(-self.bh/2,0)\
            .close()

        #extrude if over material thickness
        side = side.extrude(-sign*self.t)

        if (purpose == "motor"):
        #cut hole for bearing
            side = side\
                .moveTo(0,self.bl-self.bh/2)\
                .circle(self.bd/2)\
                .cutThruAll()\
                .rotate((0,-1,0),(0,1,0),180)                
        else:
            side = side.faces(">Y").workplane()\
                .moveTo(-self.ad/2,self.bl)\
                .line(0,-self.asd+self.ad/2)\
                .sagittaArc((self.ad/2,self.bl-self.asd+self.ad/2),-self.ad/2)\
                .line(0,self.asd-self.ad/2)\
                .close()\
                .cutThruAll()

        #translate it over half belt width to center bracket
        side = side.translate((0,sign*offset,0))
        return(side)
    
    def build_tensioner(self,name):
        adjuster_pos = self.bl - self.asd - self.ad 
        adjuster_size = 2*self.nt + (2*self.nsp+1)*self.ns
        adjuster = cq.Workplane("YZ")\
            .moveTo(-(2*self.nsp+1)*self.ns,0)\
            .line((2*self.nsp+1)*self.ns,0)\
            .line(0,-adjuster_size)\
            .line(-(2*self.nsp+1)*self.ns,(2*self.nsp+1)*self.ns)\
            .close()\
            .extrude(-(1+2*self.nsp)*self.ns)\
            .faces(">Z").workplane()\
            .moveTo(-(0.5+self.nsp)*self.ns,-(0.5+self.nsp)*self.ns)\
            .polygon(6,self.ns)\
            .hole(self.td)\
            .cutBlind(-self.nt)
        if (name == "left"):
            adjuster = adjuster\
                .translate(((0.5+self.nsp)*self.ns,-self.bw/2-self.t,adjuster_pos))
        elif (name == "right"):
            adjuster = adjuster\
                .rotate((0,0,-1),(0,0,1),180)\
                .translate((-(0.5+self.nsp)*self.ns,self.bw/2+self.t,adjuster_pos))            
        return(adjuster)
       
    
    def build_belt_rest(self,purpose):
        sign = 1
        if (purpose != "motor"):
            sign = -1 ;
        return(cq.Workplane("XY")\
            .moveTo(-self.bh/2,-self.bw/2)\
            .line(self.t,0)\
            .line(0,self.bw)\
            .line(-self.t,0)\
            .close()\
            .extrude(-sign*(self.bl - 1.2*self.bh))
            )
            
    def build_connector(self,purpose):
        sign = 1
        if (purpose != "motor"):
            sign = -1 ;        
        return(cq.Workplane("XY")\
            .moveTo(self.bh/2,self.bw/2)\
            .line(-self.bh+self.t,0)\
            .line(0,-self.bw)\
            .line(self.bh-self.t,0)\
            .close()\
            .extrude(-sign*self.t)\
            .faces(">Z").workplane()\
            .moveTo(0,0)\
            .hole(self.din)\
            .moveTo(0,-self.bw/4)\
            .hole(self.din)\
            .moveTo(0,self.bw/4)\
            .hole(self.din)
            )

    def build_roller(self,purpose):
        roll = cq.Workplane("XY")\
            .circle(self.rd/2)\
            .extrude(self.bw-2*self.rg)

        if ((purpose == "motor") & (self.mae > 0)):
            if (self.mae == 1):
                mar2 = self.mad2 - 0.5*self.mad1
                lFlat = math.sqrt(0.25*self.mad1**2 - mar2**2)
                endPoint = (-lFlat,mar2)
                midPoint = (0,-self.mad1/2)
                self.roll = self.roll.faces(">Z").workplane()\
                    .moveTo(endPoint[0],endPoint[1])\
                    .line(2*lFlat,0)\
                    .threePointArc(midPoint,endPoint)\
                    .close()\
                    .cutBlind(-self.mal)
            elif (self.mae == 2):
                mar2 = self.mad2/2 
                lFlat = math.sqrt(0.25*(self.mad1**2 - self.mad2**2))
                points = [(-mar2,lFlat),
                          (0,self.mad1/2),
                          (mar2,lFlat),
                          (mar2,-lFlat),
                          (0,-self.mad1/2),
                          (-mar2,-lFlat)]
                roll = roll.faces(">Z").workplane()\
                    .moveTo(points[0][0],points[0][1])\
                    .threePointArc(points[1],points[2])\
                    .lineTo(points[3][0],points[3][1])\
                    .threePointArc(points[4],points[5])\
                    .close()\
                    .cutBlind(-self.mal-self.rg)
        else:
            roll = roll.faces(">Z").workplane(offset=-self.mal)\
                .circle(self.mad1/2)\
                .cutBlind(self.mal-self.rg)

        roll = roll.faces("<Z").workplane()\
            .circle(self.ad/2)\
            .cutBlind(-(self.rl-self.mal-2*self.rg)+0.0001) 

        if (self.bd > 0) & (self.bt > 0):
            roll = roll.faces(">Z").workplane()\
                .circle(self.bd/2)\
                .cutBlind(-self.bt)\
                .faces("<Z").workplane()\
                .circle(self.bd/2)\
                .cutBlind(-self.bt)

        if (self.e > 0):
            roll = roll.faces(">Z").workplane()\
                .circle(self.rd/2-2)\
                .cutBlind(-self.e)\
                .faces("<Z").workplane()\
                .circle(self.rd/2-2)\
                .cutBlind(-1)    
                
        return(roll)


    def build_tensioner_axis_connector(self):
        side_length = self.ad/2 + self.t + self.td

        maincyl = cq.Workplane("XY")\
            .circle(self.ad/2+self.t)\
            .extrude(self.td*2)
            
        sidecyl = cq.Workplane("YZ")\
            .moveTo(0,self.td)\
            .circle(self.td/2+self.t)\
            .extrude(side_length)
            
        connector = cq.Workplane("YZ")\
            .union(maincyl)\
            .union(sidecyl)\
            .faces("<Z").workplane()\
            .circle(self.ad/2)\
            .cutThruAll()\
            .faces(">X").workplane()\
            .moveTo(0,self.td)\
            .circle(self.td/2)\
            .cutBlind(-side_length)
        return(connector)

    

    def build(self):
        self.left_plate_motor  = self.build_side("left","motor")
        self.right_plate_motor = self.build_side("right","motor")
        self.belt_rest_motor   = self.build_belt_rest("motor")
        self.connector_motor   = self.build_connector("motor")
        self.belt_bracket_motor = self.belt_bracket_motor\
            .union(self.left_plate_motor)\
            .union(self.right_plate_motor)\
            .union(self.belt_rest_motor)\
            .union(self.connector_motor)

        self.left_plate_roller  = self.build_side("left","roller")
        self.right_plate_roller = self.build_side("right","roller")
        self.belt_rest_roller   = self.build_belt_rest( "roller")
        self.connector_roller   = self.build_connector("roller")
        self.tensioner_left     = self.build_tensioner("left")
        self.tensioner_right    = self.build_tensioner("right")
        self.belt_bracket_roller = self.belt_bracket_roller\
            .union(self.left_plate_roller)\
            .union(self.right_plate_roller)\
            .union(self.belt_rest_roller)\
            .union(self.connector_roller)\
            .union(self.tensioner_left)\
            .union(self.tensioner_right)
            
        self.motor_roller = self.motor_roller\
            .union(self.build_roller("motor"))\
            .rotate((-1,0,self.rl/2),(1,0,self.rl/2),90)\
            .translate((0,0,self.bl-self.bh/2-self.rl/2+5))
            
        self.other_roller = self.other_roller\
            .union(self.build_roller("roller"))\
            .rotate((-1,0,self.rl/2),(1,0,self.rl/2),90)\
            .translate((0,0,-self.bl+self.bh/2-self.rl/2))
            
        self.axis_connector_left = self.axis_connector_left\
            .union(self.build_tensioner_axis_connector())\
            .rotate((0,-1,0),(0,1,0),90)\
            .rotate((0,0,-1),(0,0,1),90)\
            .translate((0,-self.bw/2-self.t-2*self.td-self.nsp*self.ns,self.bl-self.bh/2+5))

        self.axis_connector_right = self.axis_connector_right\
            .union(self.build_tensioner_axis_connector())\
            .rotate((0,-1,0),(0,1,0),90)\
            .rotate((0,0,-1),(0,0,1),90)\
            .translate((0,self.bw/2+self.t+self.nsp*self.ns,self.bl-self.bh/2+5))
            


# =============================================================================
# Part Creation
# =============================================================================

cq.Workplane.part = utilities.part

# True to be able to export everything in a single STEP file. False to be able to selectively show 
# and hide objects in cq-editor.
union_results = False
show_options = {"color": "grey", "alpha": 0}
measures = dict(
        belt_width            = 50,
        bracket_height        = 35,
        bracket_length        = 150,
        material_thickness    = 2,
        bearing_diameter      = 24,
        bearing_thickness     = 0,         #thickness of the bearing. Set 0 if none
        bolt_size             = 6,
        axis_diameter         = 5,              #diameter of axis opposite to motor axis
        axis_slide_depth      = 20,
        motor_axis_edges      = 2,               #number of flat sides on motor axis (0,1 or 2)
        motor_axis_diameter_major = 5,  #major diameter of motor axis
        motor_axis_diameter_minor = 4,  #minor diameter of motor axis. Ignored if number of flat sides = 0
        motor_axis_length = 30,         #depth of motor axis in roller 
        roller_diameter = 40,
        roller_friction_edge = 1,               #create edge to reduce friction between roller and bracket (0 = no, 1 = yes)        
        roller_gap = 1,                  #gap between roller and bracket, 1mm should be enough
        tensioner_diameter = 4
        )

    # Create case as a Case object to get access to its parts.
belt = Belt(cq.Workplane("XY"), measures)
    
show_object(belt.belt_bracket_motor,   name = "belt_bracket_motor",   options = show_options)
show_object(belt.belt_bracket_roller,  name = "belt_bracket_roller",  options = show_options)
show_object(belt.motor_roller,  name = "motor_roller",  options = show_options)
show_object(belt.other_roller,  name = "other_roller",  options = show_options)
show_object(belt.axis_connector_left,  name = "axis_connector_left",  options = show_options)
show_object(belt.axis_connector_right,  name = "axis_connector_right",  options = show_options)
