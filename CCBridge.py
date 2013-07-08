#!/usr/bin/env python
#!/usr/bin/python
# -*- coding: utf-8 -*-
#Copyright 2013 Aaron Smith

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

 
from time import sleep
import curses
import os
import curses.wrapper  #this will help reset terminal by catching exceptions and preventing effed up shells
import pyrax
import json
from operator import itemgetter
from math import log

###########################
#SET UP GLOBAL VARIABLES
MENU = "menu"
COMMAND = "command"
EXITMENU = "exitmenu"
CREDS_FILE = os.path.expanduser("~/.rackspace_cloud_credentials")
LOG_FILE = "/var/log/CCBridge.log"
data = []     #<---- this is a list of dictionaries
titles = []   #<---this is a list that contains the title_row ..[('x', 'y'), ('z', 'w')]
unit_list = zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 2, 2, 2])     #<-- used in bytes conversion in byte_converter()

#END GLOBAL VARIABLE SET UP ^
############################
#SET UP LOGGING    <---need root privileges to create log file

#create log file if it does not exist
# if not os.path.exists("/var/log/CCBridge.log"):
#   file = open(LOG_FILE, 'w')
#   file.write('')
#   file.close()
# else:
#   pass

#END LOGGING SET UP ^
#####################
#INITIALIZE CURSES

#initializes a new window for capturing key presses
screen = curses.initscr()

# Disables automatic echoing of key presses (prevents program from input each key twice)
curses.noecho()

# Disables line buffering (runs each key as it is pressed rather than waiting for the return key to pressed)
curses.cbreak()

# Lets you use colors when highlighting selected menu option
curses.start_color()

# Capture input from keypad
screen.keypad(1)
 
# Change this to use different colors when highlighting
curses.init_pair(1,curses.COLOR_BLACK, curses.COLOR_WHITE) # Sets up color pair #1, it does black text with white background
h = curses.color_pair(1) #h is the coloring for a highlighted menu option
n = curses.A_NORMAL #n is the coloring for a non highlighted menu option

#END CURSES SETUP ^
#######################
#CREATE THE MENUS

menu_data = {
 'title': "Rackspace Cloud Bridge", 'type': MENU, 'subtitle': "Pick your poison...",
 'options':[
   { 'title': "Authenticate", 'type': MENU, 'subtitle': "Please Select an Action...",
   'options': [
     { 'title': "Authenticate using local credentials file", 'type': COMMAND },
     { 'title': "Enter credentials manually", 'type': COMMAND },
   ]
   },
   { 'title': "Show Credentials", 'type': COMMAND },
   { 'title': "List Servers", 'type': COMMAND },
   { 'title': "List Flavors", 'type': COMMAND },
   { 'title': "List Images", 'type': MENU, 'subtitle': "Please Select an Action...",
   'options':[
     { 'title': "List My Images", 'type': COMMAND },
     { 'title': "List Base Images", 'type': COMMAND },
    ]
    },
   { 'title': "List Load Balancers", 'type': COMMAND },
   { 'title': "List Databases", 'type': COMMAND },
   { 'title': "List Cloud Files", 'type': COMMAND },
]
}
 
# This function displays the appropriate menu and returns the option selected
def runmenu(menu, parent):
 
  # work out what text to display as the last menu option
  if parent is None:
    lastoption = "Exit"
  else:
    lastoption = "Return to %s menu" % parent['title']
 
  optioncount = len(menu['options']) # how many options in this menu
 
  pos=0 #pos is the zero-based index of the hightlighted menu option. Every time runmenu is called, position returns to 0, when runmenu ends the position is returned and tells the program what opt$
  oldpos=None # used to prevent the screen being redrawn every time
  x = None #control for while loop, let's you scroll through options until return key is pressed then returns pos to program
 
  # Loop until return key is pressed
  while x !=ord('\n'):
    if pos != oldpos:
      oldpos = pos
      screen.border(0)
      screen.addstr(2,2, menu['title'], curses.A_STANDOUT) # Title for this menu
      screen.addstr(4,2, menu['subtitle'], curses.A_BOLD) #Subtitle for this menu
 
      # Display all the menu items, showing the 'pos' item highlighted
      for index in range(optioncount):
        textstyle = n
        if pos==index:
          textstyle = h
        screen.addstr(5+index,4, "%d - %s" % (index+1, menu['options'][index]['title']), textstyle)
      # Now display Exit/Return at bottom of menu
      textstyle = n
      if pos==optioncount:
        textstyle = h
      screen.addstr(5+optioncount,4, "%d - %s" % (optioncount+1, lastoption), textstyle)
      screen.refresh()
      # finished updating screen
 
    x = screen.getch() # Gets user input
 
    # What is user input?
    if x >= ord('1') and x <= ord(str(optioncount+1)):
      pos = x - ord('0') - 1 # convert keypress back to a number, then subtract 1 to get index
    elif x == 258: # down arrow
      if pos < optioncount:
        pos += 1
      else: pos = 0
    elif x == 259: # up arrow
      if pos > 0:
        pos += -1
      else: pos = optioncount
 
  # return index of the selected item
  return pos

# This function calls showmenu and then acts on the selected item
def processmenu(menu, parent=None):
  optioncount = len(menu['options'])
  exitmenu = False
  while not exitmenu: #Loop until the user exits the menu
    getin = runmenu(menu, parent)
    if getin == optioncount:
        exitmenu = True
    elif menu['options'][getin]['type'] == COMMAND:
      curses.def_prog_mode()    # save curent curses environment
      os.system('reset')
      if menu['options'][getin]['title'] == 'Authenticate using local credentials file':
		getcreds()
#      os.system(menu['options'][getin]['command']) # run the command - bash
      if menu['options'][getin]['title'] == 'Enter credentials manually':
        input_user_creds()
      if menu['options'][getin]['title'] == 'List Servers':
      	serverlist()
      if menu['options'][getin]['title'] == 'List My Images':
        getimagelist()
      if menu['options'][getin]['title'] == 'List Base Images':
        getimagelist(base=True)
      if menu['options'][getin]['title'] == 'Show Credentials':
        show_credentials()
      if menu['options'][getin]['title'] == 'List Load Balancers':
        getLBlist()
      if menu['options'][getin]['title'] == 'List Flavors':
        flavorlist()
      if menu['options'][getin]['title'] == 'List Cloud Files':
        getCNlist()
      curses.reset_prog_mode()   # reset to 'current' curses environment
      curses.curs_set(1)         # reset doesn't do this right
      curses.curs_set(0)
    elif menu['options'][getin]['type'] == MENU:
          screen.clear() #clears previous screen on key press and updates display based on pos
          processmenu(menu['options'][getin], menu) # display the submenu
          screen.clear() #clears previous screen on key press and updates display based on pos
    elif menu['options'][getin]['type'] == EXITMENU:
          exitmenu = True

#END MENU SET UP  ^
############################
#FUNCTIONS

def terminal_size():
  """Get the terminal row and column length for building fit-to-screen content"""
  rows, cols = os.popen('stty size', 'r').read().split()
  return {'rows':rows, 'columns':cols}

def byte_converter(num):
  """Use this to convert bytes to human readable sizes"""
  if num > 1:
    exponent = min(int(log(num, 1024)), len(unit_list) - 1)
    quotient = float(num) / 1024**exponent
    unit, num_decimals = unit_list[exponent]
    format_string = '{:.%sf} {}' % (num_decimals)
    return format_string.format(quotient, unit)
  if num == 0:
    return '0 bytes'
  if num == 1:
    return '1 byte'

def myTitle(title):
  """Authenticate and get credentials and services"""
  term = terminal_size()
  col = term['columns']
  row = term['rows']
  upper_title_line = '=' * int(col)
  lower_title_line = upper_title_line
  x = int(col) - len(title)
  x2 = x / 2
  y = '-' * x2
  print upper_title_line 
  print y + title + y
  print lower_title_line
  print ""
  print ""
  print ""

def clear_screen():
  print ""
  print ""
  try:
    raw_input("Press Enter to continue...")
    screen.clear()
  except (KeyboardInterrupt,EOFError), e:
    screen.clear() #clears previous screen on key press and updates display based on pos
  except:
    screen.clear() #clears previous screen on key press and updates display based on pos
    

def get_API_key():
  my_api_key = pyrax.identity.api_key
  print "API key: %s" % my_api_key

#print token
def token():
  token = pyrax.identity.token
  print "Todays Token: %s" % token

#print expiration date
def expires():
  expires = pyrax.identity.expires
  print "Token Expires: %s" % expires
  
# get authenticated user
def authenticated_user():
  clouduser = pyrax.identity.username
  print "Authenticated user: %s" % clouduser

def default_region():
  dregion = pyrax.identity.user['default_region']
  print "Default region: %s" % dregion

def name():
  customer_username = pyrax.identity.username
  print "Username: %s" % customer_username

def cust_ddi():
  tennant_ddi = pyrax.identity.tenant_id
  print "DDI: %s" % tennant_ddi

def getcreds():
  try:
    pyrax.set_credential_file(CREDS_FILE)
  except Exception, e:
    print ""
    print ""
    print e
    print ""
    print ""
    clear_screen()
  else:
    auth_successful = pyrax.identity.authenticated
    print ""
    print ""
    print "Authentication successful: %s" % auth_successful
    name()
    get_API_key()
    token()
    expires()
    default_region()
    cust_ddi()
    clear_screen()

def services():
  services = json.dumps(pyrax.identity.services, sort_keys=True, indent=2, separators=(',', ': '))
  print services
  clear_screen()

def input_user_creds():
  print ""
  print ""
  username = raw_input("Enter customer username: ")
  apikey = raw_input("Enter customer API key: ")
  pyrax.set_credentials(username, apikey)
  auth_successful = pyrax.identity.authenticated
  print ""
  print ""
  print "Authentication successful: %s" % auth_successful
  name()
  cust_ddi()
  token()
  expires()
  default_region()
  clear_screen()

def auth_check():
  authed = pyrax.identity.authenticated
  if authed:
    return True
  else:
    return False

def not_authed():
  print ""
  print ""
  print "Not Authenticated!"
  clear_screen()

def show_credentials():
#  authed = pyrax.identity.authenticated
  if auth_check():
    print ""
    print ""
    name()
    cust_ddi()
    get_API_key()
    token()
    expires()
    default_region()
    clear_screen()
  else:
    not_authed()
    clear_screen()

def format_as_table(data, keys, header=None, sort_by_key=None, sort_order_reverse=False):
    """Takes a list of dictionaries, formats the data, and returns
    the formatted data as a text table.

    Required Parameters:
        data - Data to process (list of dictionaries). (Type: List)
        keys - List of keys in the dictionary. (Type: List)

    Optional Parameters:
        header - The table header. (Type: List)
        sort_by_key - The key to sort by. (Type: String)
        sort_order_reverse - Default sort order is ascending, if
            True sort order will change to descending. (Type: Boolean)
    """
    # Sort the data if a sort key is specified (default sort order
    # is ascending)
    if sort_by_key:
        data = sorted(data,
                      key=itemgetter(sort_by_key),
                      reverse=sort_order_reverse)

    # If header is not empty, add header to data
    if header:
        # Get the length of each header and create a divider based
        # on that length
        header_divider = []
        for name in header:
            header_divider.append('-' * len(name))

        # Create a list of dictionary from the keys and the header and
        # insert it at the beginning of the list. Do the same for the
        # divider and insert below the header.
        header_divider = dict(zip(keys, header_divider))
        data.insert(0, header_divider)
        header = dict(zip(keys, header))
        data.insert(0, header)

    column_widths = []
    for key in keys:
        column_widths.append(max(len(str(column[key])) for column in data))

    # Create a tuple pair of key and the associated column width for it
    key_width_pair = zip(keys, column_widths)

    format = ('%-*s ' * len(keys)).strip() + '\n'
    formatted_data = ''
    for element in data:
        data_to_format = []
        # Create a tuple that will be used for the formatting in
        # width, value format
        for pair in key_width_pair:
            data_to_format.append(pair[1])
            data_to_format.append(element[pair[0]])
        formatted_data += format % tuple(data_to_format)
    return formatted_data

def flavorlist():
  print ""
  print ""
  myTitle('MY FLAVOR LIST')
  cs = pyrax.cloudservers
  flvrs = cs.flavors.list()
  my_flvrs = [flvr for flvr in flvrs]
  header = ['Flavor Name', 'ID', 'RAM', 'Disk', 'VCPUs', 'Swap' ]
  keys = ['name', 'id', 'ram', 'disk', 'vcpus', 'swap' ]
  sort_by_key = 'id'
  sort_order_reverse = False
  data = []
  for flv in my_flvrs:
    data.append({'name':flv.name, 'id':flv.id, 'ram':flv.ram, 'disk':flv.disk, 'vcpus':flv.vcpus, 'swap':flv.swap})
  print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
  clear_screen()

def serverlist():
  print ""
  print ""
  myTitle('CLOUD SERVERS')
  cs = pyrax.cloudservers  #use cs.servers.list()
  svrs = cs.servers.list()
  my_servers = [svr for svr in svrs]
  svrs_dfw = pyrax.connect_to_cloudservers(region="DFW")
  svrs_ord = pyrax.connect_to_cloudservers(region="ORD")
  dfw_servers = svrs_dfw.servers.list()
  my_dfw_servers = [svr for svr in dfw_servers]
  ord_servers = svrs_ord.servers.list()
  my_ord_servers = [svr for svr in ord_servers]
  all_servers = dfw_servers + ord_servers
  header = ['Server Name', 'Region', 'Server UUID', '  Public IP  ', '  Private IP  ', 'Status' ]
  keys = ['name', 'region', 'UUID', 'public_ip', 'private_ip', 'status' ]
  sort_by_key = 'region'
  sort_order_reverse = False
  #region = []
  data = []
  #public_ip = ''
  #private_ip = ''
  status = ''
  for pos, svr in enumerate(my_dfw_servers):
    region = 'DFW'
    public_ip = []
    private_ip = []
    for i in range(len(svr.addresses['public'])):
      if svr.addresses['public'][i]['version'] == 4:
        public_ip.append(svr.addresses['public'][i]['addr'])
        public_ip = ",".join(public_ip)
    for i in range(len(svr.addresses['private'])):
      if svr.addresses['private'][i]['version'] == 4:
        private_ip.append(svr.addresses['private'][i]['addr'])
        private_ip = ",".join(private_ip)
    #public_ip = svr.addresses['public'][0]['addr']
    #private_ip = svr.addresses['private'][0]['addr']
    data.append({'pos': pos + 1, 'name':svr.name, 'public_ip':public_ip, 'private_ip':private_ip, 'UUID':svr.id, 'region':region, 'status':svr.status})
  for pos, svr in enumerate(my_ord_servers):
    region = 'ORD'
    public_ip = []
    private_ip = []
    for i in range(len(svr.addresses['public'])):
      if svr.addresses['public'][i]['version'] == 4:
        public_ip.append(svr.addresses['public'][i]['addr'])
        public_ip = ",".join(public_ip)
    for i in range(len(svr.addresses['private'])):
      if svr.addresses['private'][i]['version'] == 4:
        private_ip.append(svr.addresses['private'][i]['addr'])
        private_ip = ",".join(private_ip)
    data.append({'pos': pos + 1, 'name':svr.name, 'public_ip':public_ip, 'private_ip':private_ip, 'UUID':svr.id, 'region':region, 'status':svr.status})
  print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
  clear_screen()

def getimagelist(base=False):
  print ""
  print ""
  myTitle('MY IMAGES')
  ## Print list of available images with imageID
  cs = pyrax.cloudservers
  all_base_images = cs.images.list()
  base_images = [img for img in all_base_images if not hasattr(img, "server")]
  svrs_dfw = pyrax.connect_to_cloudservers(region="DFW")
  svrs_ord = pyrax.connect_to_cloudservers(region="ORD")
  dfw_images = svrs_dfw.images.list()
  ord_images = svrs_ord.images.list()
  all_imgs = dfw_images + ord_images
  images = [img for img in all_imgs if hasattr(img, "server")]
  sort_by_key = ''
  if not images:
    print ""
    print ""
    print "You have no images!"
    clear_screen()
  my_dfw_images = [img for img in dfw_images if hasattr(img, "server")]
  my_ord_images = [img for img in ord_images if hasattr(img, "server")]
  if base:
    data = []
    header = ['Image Name', 'Image ID']
    keys = ['name', 'ID']
#    sor_by_key = 'name'
    sort_order_reverse = False
    for img in base_images:
      data.append({'name':img.name, 'ID':img.id})
    print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
    clear_screen()
  else:
    data = []
    header = ['Image Name', 'Region', 'Image ID', 'Min RAM', 'Min Disk', 'Status', 'Progress' ]
    keys = ['name', 'region', 'ID', 'minram', 'mindisk', 'status', 'progress' ]
 #   sort_by_key = 'region'
    sort_order_reverse = False
    for pos,img in enumerate(my_dfw_images):
      region = 'DFW'
      data.append({'pos':pos + 1, 'name':img.name, 'region':region, 'ID':img.id, 'minram':img.minRam, 'mindisk':img.minDisk, 'status':img.status, 'progress':img.progress})
    for pos, img in enumerate(my_ord_images):
      region = 'ORD'
      data.append({'pos':pos + 1, 'name':img.name, 'region':region, 'ID':img.id, 'minram':img.minRam, 'mindisk':img.minDisk, 'status':img.status, 'progress':img.progress})
    print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
    clear_screen()

def getLBlist():
  lb = pyrax.cloud_loadbalancers
  all_lbs = lb.list()
  lbs = [loadb for loadb in all_lbs]
  header = [ 'Load Balancer Name', '  IP Address  ', 'Protocol', 'Port', 'Status' ]
  keys = [ 'name', 'public_ip', 'protocol', 'port', 'status' ]
  sort_by_key = 'status'
  sort_order_reverse = False
  data = []
  for pos, lb in enumerate(lbs):
    public_ip = lb.virtual_ips[0].address
    data.append({'pos': pos + 1, 'name':lb.name, 'public_ip':public_ip, 'protocol':lb.protocol, 'port':lb.port, 'status':lb.status})
  if not lbs:
    print ""
    print ""
    print "You have no load balancers!"
    clear_screen()
  else:
    print ""
    print ""
    myTitle('LOAD BALANCERS')
    print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
    clear_screen()

def getDBlist():
  auth_check()

def getCNlist():
  print ""
  print ""
  myTitle('CLOUD FILES')
  cfiles = pyrax.cloudfiles  #use cs.servers.list()
  #connect to cloud files by region
  cf_ord = pyrax.connect_to_cloudfiles(region='ORD')
  cf_dfw = pyrax.connect_to_cloudfiles(region='DFW')
  dfw_containers = cf_dfw.list_containers_info()
  ord_containers = cf_ord.list_containers_info()
  all_containers = dfw_containers + ord_containers
  header = ['Container Name', 'Total Objects', 'Region', 'Size' ]
  keys = ['name', 'total_objects', 'region', 'size' ]
  sort_by_key = 'total_objects'
  sort_order_reverse = True
  #region = []
  data = []
  for cn in dfw_containers:
    region = 'DFW'
    num = int(cn['bytes'])
    size = byte_converter(num)
    count = cn['count']
    name = cn['name']
    data.append({'name':name, 'total_objects':count, 'region':region, 'size':size})
  for cn in ord_containers:
    region = 'ORD'
    num = int(cn['bytes'])
    size = byte_converter(num)
    count = cn['count']
    name = cn['name']
    data.append({'name':name, 'total_objects':count, 'region':region, 'size':size})
  print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
  clear_screen()
    
#END FUNCTIONS ^
##################
# MAIN PROGRAM

try:
  processmenu(menu_data)
except KeyboardInterrupt, e:
  curses.endwin() #VITAL! This closes out the menu system and returns you to the bash prompt.
curses.endwin() #VITAL! This closes out the menu system and returns you to the bash prompt.
os.system('clear')