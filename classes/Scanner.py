from lxml import etree

from classes.GUI import *
from classes.Grid import *
from classes.Logger import *

from config import *

from threading import Thread # Needed for Messenger
from time import sleep
from sys import exit
import datetime

class Scanner:
   
   # Incapsulated objects
   GUI       = None
   logger    = None
   service   = None
   config    = None
   msnThread = None
   
   # Stats for overall scanning
   scanStartDatetime  = None
   scanFinishDatetime = None
   boxesN             = 0
   requestsTotal      = 0
   costTotal          = 0
   
   # Current box scan
   currentBox         = None

   # Vars
   bounds    = None    #bounds in latitude and longtitude [x, y, x2, y2]
   
   
   # ---------------------------------------------------------------------------
   
   
   def __init__(self):
      
      # Load configuration file
      self.config=config

      # Make Messenger
      msn = Messenger('', self.config['GUI_PORT'])
      msn.setHandler(self.incoming_msg_handler)
      self.msnThread = Thread(target=msn.start_server)
      self.msnThread.start()
      
      # GUI
      self.GUI    = GUI(msn)
      
      # Bounds
      self.set_bounds(self.config['SCANNING_AREA'])
      print("Scanning area set to: ", self.bounds)
      
      self.logger = Logger('.'+self.config['LOG_PATH'],
                           self.config['LOG_SCAN_FILENAME'],
                           self.config['LOG_STATS_FILENAME'],
                           self.config['LOG_RESULT_FILENAME'],
                           self)

   # Set outer bounds for the scanning
   def set_bounds(self, bounds):
      # Sort the bounds so that the left couple
      # is always on top and left of the right couple
      lat1=bounds[0]
      lng1=bounds[1]
      lat2=bounds[2]
      lng2=bounds[3]
      
      if (lat1<lat2) or (lng1>lng2): #swap couples
         bounds=(lat2, lng2, lat1, lng1)
         
      self.bounds=bounds
      self.GUI.center_map(bounds[0], bounds[1], bounds[2], bounds[3])

   def set_for_each_box(self, func):
      self.for_each_box=func
      
   def set_response_handler(self, func):
      self.response_handler=func
      

   # ---------------------------------------------------------------------------


   # Handling incoming messages from GUI
   def incoming_msg_handler(self, msg):
      if (msg == "PAUSE"):
         print("Client asks to pause application")
      elif (msg == "CLOSE"):
         print("Client asks to close application")
        
               
   # ---------------------------------------------------------------------------
   

   # Start scanning
   def start_scanning(self):
      self.scanStartDatetime=datetime.datetime.now()
      logger=self.logger

      # Make a grid of scannable boxes
      grid=Grid(self.bounds, self) 
      self.GUI.add_grid(grid)
      self.boxesN=len(grid.boxes)
      print("Number of boxes to scan: ", self.boxesN)

      # Scan each box
      toScan=list(grid.boxes)
      consequentReqRetries=0
      while(toScan):
         box=toScan[0]
         self.currentBox=box
         sleep(self.config['scheduler']['NEXT_SEARCH_WAIT'])
         self.GUI.remove_box(box)
         self.GUI.add_box(box, 'green')

         markers = self.service.search(box, logger) # HERE WE SEARCH BOX
         max_results = self.config['service']['response']['MAX_RESULTS']
         if max_results!='INF' and len(markers) >= max_results:
            print("response has max results")

         self.requestsTotal +=1
         self.costTotal += self.config['service']['request']['COST_PER_REQUEST']
         logger.update_stats()

         max_cost_day = self.config['service']['request']['MAX_COST_DAY']
         if max_cost_day!='INF' and self.costTotal > max_cost_day:
            print("max cost per day reached")

         # Add marker on map
         for marker in markers:
            if (len(marker)>=2):
               self.GUI.add_marker(marker[0], marker[1])

         # Remove finished box
         toScan.pop(0)
         consequentReqRetries=0
         
      # Finish
      self.scanFinishDatetime=datetime.datetime.now()
      logger.update_stats()
      print("Scanning finished.")
      print("Press CTRL+C to stop application.")


   def stop_scanning(self):
      pass


   # ----------------- Setters ---------------------

   # Sets the service to be used for scanning
   def set_service(self, service):
      self.service = service
      
      # Override config with service values
      rules = service.service
      if (rules):
         for subject in rules:
            for key in rules[subject]:


               print(subject, key)
               
               # KEY required
               if subject=='authentication' and key=='REQUIRED':
                  if rules['authentication']['REQUIRED']==True and\
                        (not service.key or len(service.key)<1):
                     print("The service requires a key, but none was provided.")
                     print("Press CTRL+Z to exit.")
                     exit()
               
               # Box limits
               elif subject=='box' and (key=='MAX_X_DISTANCE' or key=='MAX_Y_DISTANCE'):
                  if self.config['box']['X_DISTANCE'] > rules['box']['MAX_X_DISTANCE']:
                     self.config['box']['X_DISTANCE'] = rules['box']['MAX_X_DISTANCE']
                  if self.config['box']['Y_DISTANCE'] > rules['box']['MAX_Y_DISTANCE']:
                     self.config['box']['Y_DISTANCE'] = rules['box']['MAX_Y_DISTANCE']
               
               # Min sleep between requests
               elif subject=='request' and key=='MIN_REQUEST_INTERVAL':
                  if self.config['scheduler']['NEXT_SEARCH_WAIT'] < rules['request']['MIN_REQUEST_INTERVAL']:
                     self.config['scheduler']['NEXT_SEARCH_WAIT'] = rules['request']['MIN_REQUEST_INTERVAL']
               
               # Just copy rest of options
               else:
                  self.config['service'][subject][key] = rules[subject][key]

