#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Topmenu and the submenus are based of the example found at this location http://blog.skeltonnetworks.com/2010/03/python-curses-custom-menu/
# The rest of the work was done by Matthew Bennett and he requests you keep these two mentions when you reuse the code :-)
# Basic code refactoring by Andrew Scheller
 
from time import sleep
import curses
import os
import curses.wrapper  #this will help reset terminal by catching exceptions and preventing effed up shells
import pyrax
import json
from operator import itemgetter

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

MENU = "menu"
COMMAND = "command"
EXITMENU = "exitmenu"
CREDS_FILE = os.path.expanduser("~/.rackspace_cloud_credentials")
data = []     #<---- this is a list of dictionaries
titles = []   #<---this is a list that contains the title_row ..[('x', 'y'), ('z', 'w')]
# set pyrax creds without creds file
#pyrax.set_credentials('USERNAME', 'API_KEY')

menu_data = {
 'title': "Rackspace Cloud Bridge", 'type': MENU, 'subtitle': "Pick your poison...",
 'options':[
   { 'title': "Authenticate", 'type': MENU, 'subtitle': "Please Select an action...",
   'options': [
     { 'title': "Authenticate using local credentials file", 'type': COMMAND },
     { 'title': "Enter credentials manually", 'type': COMMAND },
   ]
   },
   { 'title': "Show Credentials", 'type': COMMAND },
   { 'title': "List Servers", 'type': COMMAND },
   { 'title': "List Images", 'type': COMMAND },
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


#Authenticate and get credentials and services
def servers_title():
    print "============================================"
    print "----------------SERVER LIST----------------"
    print "============================================"
    print ""
    print ""
    print ""

def lb_title():
    print "============================================"
    print "---------------Load Balancers---------------"
    print "============================================"
    print ""

def clear_screen():
  print ""
  print ""
  raw_input("Press Enter to continue...")
  screen.clear() #clears previous screen on key press and updates display based on pos

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
  pyrax.set_credential_file(CREDS_FILE)
  auth_successful = pyrax.identity.authenticated
  print ""
  print ""
  print "Authentication successful: %s" % auth_successful
  name()
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
  try:
    authed = pyrax.identity.authenticated
    if authed:
      return True
  except Exception:
    not_authed()

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

def serverlist():
  print ""
  print ""
  servers_title()
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
  header = ['Server Name', 'Region', 'Server UUID']
  keys = ['name', 'region', 'UUID']
  sort_by_key = 'region'
  sort_order_reverse = False
  #region = []
  data = []
  for pos, svr in enumerate(my_dfw_servers):
    region = 'DFW'
    data.append({'pos': pos + 1, 'name':svr.name, 'UUID':svr.id, 'region':region})
  for pos, svr in enumerate(my_ord_servers):
    region = 'ORD'
    data.append({'pos': pos + 1, 'name': svr.name, 'UUID':svr.id, 'region':region})
  print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
  clear_screen()

def getimagelist():
  print ""
  print ""
  ## Print list of available images with imageID
  cs = pyrax.cloudservers
  all_imgs = cs.images.list()
  images = [img for img in all_imgs if hasattr(img, "server")]
  if not images:
    print ""
    print ""
    print "You have no images!"
    clear_screen()
  img_dict = {}
  for pos, img in enumerate(images):
    print "%s: %s" % (pos + 1, img.name)
    img_dict[str(pos)] = img
    clear_screen()

def getLBlist():
  auth_check()
  print ""
  print ""
  lb = pyrax.cloud_loadbalancers
  all_lbs = lb.list()
  lbs = [loadb for loadb in all_lbs]
  if not lbs:
    print ""
    print ""
    print "You have no load balancers!"
    clear_screen()
  else:
    print ""
    print ""
    lb_title()
#     print "Name: %s" % lbs.name
#     print "ID: %s" % lbs.id
#     print "Status: %s" % lbs.status
#     print "Nodes: %s" % lbs.nodes
#     print "Virtual IPs: %s" % lbs.virtual_ips
#     print "Algorithm: %s" % lbs.algorithm
#     print "Protocol: %s" % lbs.protocol
#     clear_screen()
    my_lbs = [load_b for load_b in lbs]
    for pos, my_lb in enumerate(my_lbs):
      print "%s: %s" % (pos +1, my_lb.name)
    clear_screen()

def getDBlist():
  auth_check()
    
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
      if menu['options'][getin]['title'] == 'List Images':
        getimagelist()
      if menu['options'][getin]['title'] == 'Show Credentials':
        show_credentials()
      if menu['options'][getin]['title'] == 'List Load Balancers':
        getLBlist()
      curses.reset_prog_mode()   # reset to 'current' curses environment
      curses.curs_set(1)         # reset doesn't do this right
      curses.curs_set(0)
    elif menu['options'][getin]['type'] == MENU:
          screen.clear() #clears previous screen on key press and updates display based on pos
          processmenu(menu['options'][getin], menu) # display the submenu
          screen.clear() #clears previous screen on key press and updates display based on pos
    elif menu['options'][getin]['type'] == EXITMENU:
          exitmenu = True

# Main program
processmenu(menu_data)
curses.endwin() #VITAL! This closes out the menu system and returns you to the bash prompt.
os.system('clear')