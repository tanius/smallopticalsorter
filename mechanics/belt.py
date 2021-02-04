import logging
import importlib
import math
from math import sqrt, asin, degrees

import cadquery as cq
from cadquery import selectors

import utilities
importlib.reload(utilities)


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
        self.mtb  = float(measures["material_thickness_bracket"])
        self.mto  = float(measures["material_thickness_other"])
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
        self.fe   = float(measures["roller_friction_edge"])        
        self.rg   = float(measures["roller_gap"])
        self.rbew = float(measures["roller_belt_edge_width"])
        self.rbeh = float(measures["roller_belt_edge_height"])
        self.td   = int(measures["tensioner_bolt_size"])
       
        self.rl   = self.bw + 2*self.rbew  # length or a roller
        self.bwi  = self.rl + 2*self.rg    # inner width of bracket
        self.nsp  = 0.2 # space around nut as % of nut size
        

        if (self.td in self.m_din):
           self.ns = self.m_nut_size[self.m_din.index(self.td)]
           self.nt = self.m_nut_thickness[self.m_din.index(self.td)]
           self.tp = self.bl - self.asd - self.ad        #position of the tensioner
           self.ts = 2*self.nt + (2*self.nsp+1)*self.ns  #size (in belt direction) of tensioner           
           self.build()

    def build_side(self,name,purpose):
        offset = self.bwi/2
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
        side = side.extrude(-sign*self.mtb)

        #cut hole for mounting
        side = side.faces(">Y").workplane()\
            .moveTo(0,(self.tp-self.ts-2*self.din))\
            .hole(self.din)

        if (purpose == "motor"):
        # 1) cut hole for bearing
        # 2) from the outside extrude cilinder bearing diameter - bracket material thickness
        # 3) cut out hole for bearing
        # 4) from outide put the "lid" on
        # 5) cut hole in lid twice the axis diameter
            side = side\
                .moveTo(0,self.bl-self.bh/2)\
                .circle(self.bd/2)\
                .cutThruAll()\
                .faces(">Y").workplane()\
                .moveTo(0,self.bl-self.bh/2)\
                .circle(self.bd/2+self.mto)\
                .extrude(self.bt-self.mtb)\
                .faces(">Y").workplane()\
                .moveTo(0,self.bl-self.bh/2)\
                .circle(self.bd/2)\
                .cutThruAll()\
                .moveTo(0,self.bl-self.bh/2)\
                .circle(self.bd/2+self.mto)\
                .extrude(self.mto)\
                .faces(">Y").workplane()\
                .moveTo(0,self.bl-self.bh/2)\
                .circle(self.ad)\
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
                
        #rotate along its axis if it's the left half
        if (name == "left"):
            side = side.rotate((0,-self.mtb/2,1),(0,-self.mtb/2,-1),180)
        
        #translate it over half belt width to center bracket
        side = side.translate((0,sign*offset,0))
        
       
        return(side)

    #build the little block on the side for the belt tensioning bolt
    def build_tensioner(self,name):
        #1) draw the side surface in YZ plane
        #2) extrude it into X-direction
        #3) get the top surface
        #   a) create the round hole for the screw
        #   b) creat 6-sides hole for the nut to fit in
        adjuster = cq.Workplane("YZ")\
            .moveTo(-(2*self.nsp+1)*self.ns,0)\
            .line((2*self.nsp+1)*self.ns,0)\
            .line(0,-self.ts)\
            .line(-(2*self.nsp+1)*self.ns,(2*self.nsp+1)*self.ns)\
            .close()\
            .extrude(-(1+2*self.nsp)*self.ns)\
            .faces(">Z").workplane()\
            .moveTo(-(0.5+self.nsp)*self.ns,-(0.5+self.nsp)*self.ns)\
            .polygon(6,self.ns)\
            .hole(self.td)\
            .cutBlind(-self.nt)
        #left side : translate if from origina to position
        #righ side : rotate it 180 degrees, then translate it
        if (name == "left"):
            adjuster = adjuster\
                .translate(((0.5+self.nsp)*self.ns,-self.bw/2-self.mtb,self.tp))
        elif (name == "right"):
            adjuster = adjuster\
                .rotate((0,0,-1),(0,0,1),180)\
                .translate((-(0.5+self.nsp)*self.ns,self.bw/2+self.mtb,self.tp))            
        return(adjuster)
       
    # build the plate on the top side of the belt bracket on which the belt rests
    def build_belt_rest(self,purpose):
        # 1) reate cross section in XY plane
        # 2) extrude in z-direction 
        sign = 1
        if (purpose != "motor"):
            sign = -1 ;
        return(cq.Workplane("XY")\
            .moveTo(-self.bh/2,-self.bwi/2)\
            .line(self.mtb,0)\
            .line(0,self.bwi)\
            .line(-self.mtb,0)\
            .close()\
            .extrude(-sign*(self.bl - self.bh - self.rbeh))
            )
            
    # build the plate to connect the 2 bracket halves
    def build_connector(self,purpose):
        #1) create the plate in XY plane
        #2) extrude over material thickness in Z-direction
        #3) create 3 holes for connection
        sign = 1
        if (purpose != "motor"):
            sign = -1 ;        
        return(cq.Workplane("XY")\
            .moveTo(self.bh/2,self.bwi/2)\
            .line(-self.bh+self.mtb,0)\
            .line(0,-self.bwi)\
            .line(self.bh-self.mtb,0)\
            .close()\
            .extrude(-sign*self.mtb)\
            .faces(">Z").workplane()\
            .moveTo(self.mtb/2,0)\
            .hole(self.din)\
            .moveTo(self.mtb/2,-self.bwi/4)\
            .hole(self.din)\
            .moveTo(self.mtb/2,self.bwi/4)\
            .hole(self.din)
            )

    #build the belt rollers
    def build_roller(self,purpose):
        # start with just vertical cyliner
        roll = cq.Workplane("XY")\
            .circle(self.rd/2)\
            .extrude(self.rl)
        
        # make ridges on the rollers to guide the belt
        if (self.rbeh > 0) & (self.rbew > 0):
            roll = roll\
                .faces("<Z").workplane()\
                .circle(self.rd/2+self.rbeh)\
                .extrude(-self.rbeh)\
                .faces(">Z").workplane()\
                .circle(self.rd/2+self.rbeh)\
                .extrude(-self.rbeh)            

        # if it's the motor roller and the motor has
        # an axis that is not round we should make
        # on one side of the role the correct hole for the motor axis
        # it can be round axis with 1 flat side (mae==1) or 2 flat sides (mae==2)

        if (purpose == "motor"):
            if (self.mae == 0):
            # it's a motor with a round axis
                self.roll = self.roll.faces(">Z").workplane(offset=-self.mal)\
                    .circle(self.mad1/2)\
                    .cutBlind(self.mal)
            elif (self.mae == 1):
            # define the axis hole as flat part + 3-point arc
            # cut the whole over the motor axis length (mal)
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
              # define the axis whole by going around
              # three point arc, flat part, three point arc and close
              # cut the hole over the motor axis length (mal)
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
                    .cutBlind(-self.mal)
        else:
            # it's the non-motor roller, henace it should have
            # a big hole to avoid the axis touching the roll
            roll = roll.faces(">Z").workplane(offset=-self.mal)\
                .circle(self.mad1)\
                .cutBlind(self.mal)
                
           # if bearing diameter and bearing thickness > 0
           # space should be made to fit a bearing in the roller ends
            if (self.bd > 0) & (self.bt > 0):
               roll = roll.faces(">Z").workplane()\
                    .circle(self.bd/2)\
                    .cutBlind(-self.bt)\
                    .faces("<Z").workplane()\
                    .circle(self.bd/2)\
                    .cutBlind(-self.bt)


        # cut the remaing hole from the other side
        # just round, to fit in an axis
        roll = roll.faces("<Z").workplane()\
            .circle(self.ad/2)\
            .cutBlind(-(self.rl-self.mal-2*self.rg)) 


       # if an anti-friction edge is wanted, emboss the roller ends 1 mm
        if (self.fe > 0):
            roll = roll.faces(">Z").workplane()\
                .circle(self.rd/2-2)\
                .cutBlind(-self.fe)\
                .faces("<Z").workplane()\
                .circle(self.rd/2-2)\
                .cutBlind(-1)    
                
        return(roll)

    # build the connection piece for belt tensioning bolt and axis
    def build_tensioner_axis_connector(self):
        side_length = self.ad/2 + self.mto + self.td

        # the sold cilinder that fits over the axis
        maincyl = cq.Workplane("XY")\
            .circle(self.ad/2+self.mto)\
            .extrude(self.td*2)

        #the solid cilinder that fits over the tensioning bold
        sidecyl = cq.Workplane("YZ")\
            .moveTo(0,self.td)\
            .circle(self.td/2+self.mto)\
            .extrude(side_length)
        
        # now combine the 2 solid cylinbers and cut the holes
        # first the axis hole through and through
        # second the tensioner hole from the center of the axis outwards
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

    
    #build the full model
    def build(self):
        # build the motor half of the bracket from its pieces
        # and combine the pieces into one.
        self.left_plate_motor  = self.build_side("left","motor")
        self.right_plate_motor = self.build_side("right","motor")
        self.belt_rest_motor   = self.build_belt_rest("motor")
        self.connector_motor   = self.build_connector("motor")
        self.belt_bracket_motor = self.belt_bracket_motor\
            .union(self.left_plate_motor)\
            .union(self.right_plate_motor)\
            .union(self.belt_rest_motor)\
            .union(self.connector_motor)

        # build the other half of the bracket from its pieces
        # and combine the pieces into one.
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

        # create the roller on the motor side of the bracket
        # it will by default be in the XY plane in Z-direction
        # so it hsa to be rotated and translated in place            
        self.motor_roller = self.motor_roller\
            .union(self.build_roller("motor"))\
            .rotate((-1,0,self.rl/2),(1,0,self.rl/2),-90)\
            .translate((0,0,-self.bl+self.bh/2-self.rl/2))

        #same for the other rolder 
        self.other_roller = self.other_roller\
            .union(self.build_roller("roller"))\
            .rotate((-1,0,self.rl/2),(1,0,self.rl/2),90)\
            .translate((0,0,self.bl-self.bh/2-self.rl/2+5))
       
        # create the axis - belt tensioner connectors 
        # and rotate and translate them into place
        self.axis_connector_left = self.axis_connector_left\
            .union(self.build_tensioner_axis_connector())\
            .rotate((0,-1,0),(0,1,0),90)\
            .rotate((0,0,-1),(0,0,1),90)\
            .translate((0,-self.bw/2-self.mtb-2*self.td-self.nsp*self.ns,self.bl-self.bh/2+5))

        self.axis_connector_right = self.axis_connector_right\
            .union(self.build_tensioner_axis_connector())\
            .rotate((0,-1,0),(0,1,0),90)\
            .rotate((0,0,-1),(0,0,1),90)\
            .translate((0,self.bw/2+self.mtb+self.nsp*self.ns,self.bl-self.bh/2+5))



# =============================================================================
# Part Creation
# =============================================================================

cq.Workplane.part = utilities.part

# True to be able to export everything in a single STEP file. False to be able to selectively show 
# and hide objects in cq-editor.
union_results = False
show_options = {"color": "grey", "alpha": 0}
measures = dict(
        belt_width                 = 50,  #desired belt width 
        bracket_height             = 35,  #height of the brackt
        bracket_length             = 150, #total length of the bracket
        material_thickness_bracket = 3,   #material thickness of sides, belt rest and connection plate
        material_thickness_other   = 1.5, #material thickness of anything else
        bearing_diameter           = 24,  #outer diameter of ball bearings. Set zero if none
        bearing_thickness          = 10,   #thickness of the bearing. Set 0 if none
        bolt_size                  = 6,   #bolt size (DIN) of mounting bolts
        axis_diameter              = 5,   #diameter of axes not being the motor axis
        axis_slide_depth           = 20,  #length of sliding gap for roller that can be used for tightening belt
        motor_axis_edges           = 2,   #number of flat sides on motor axis (0,1 or 2)
        motor_axis_diameter_major  = 5,   #major diameter of motor axis
        motor_axis_diameter_minor  = 4,   #minor diameter of motor axis. Ignored if number of flat sides = 0
        motor_axis_length          = 30,  #depth of motor axis in roller 
        roller_diameter            = 40,  #diameter of the rollers
        roller_friction_edge       = 1,   #create edge to reduce friction between roller and bracket (0 = no, 1 = yes)        
        roller_gap                 = 1,   #gap between roller and bracket, 1mm should be enough
        roller_belt_edge_width     = 1,   #width of edges on the roller to keep belt in place
        roller_belt_edge_height    = 2,   #height of edges on the roller to keep belt in place
        tensioner_bolt_size        = 4    #bolt size (DIN) for tensioner 
        )

    # Create case as a Case object to get access to its parts.
belt = Belt(cq.Workplane("XY"), measures)
    
show_object(belt.belt_bracket_motor,   name = "belt_bracket_motor",   options = show_options)
show_object(belt.belt_bracket_roller,  name = "belt_bracket_roller",  options = show_options)
show_object(belt.motor_roller,  name = "motor_roller",  options = show_options)
show_object(belt.other_roller,  name = "other_roller",  options = show_options)
show_object(belt.axis_connector_left,  name = "axis_connector_left",  options = show_options)
show_object(belt.axis_connector_right,  name = "axis_connector_right",  options = show_options)
