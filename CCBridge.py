#!/usr/bin/python

#/usr/bin/env python
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

"""
todo:
-install https://github.com/justinsb/python-novatools.git for first generation server support
-add 'cdn enabled' to cloud files table       <----DONE
-add disk size, and used space to server list   alerts.ohthree.com  (get allocated from "root_gb": 160,  in reports.ohthree.com)
-add flavor/ram/os/vcpu to server list   reports.ohthree.com
-add support for cloud backup (show activity)
-add support for cloud monitoring
-add exception (AuthenticationError) to authenticate
-When using tool on RACKER network, verify host names match --name using pyrax and "vm-data/hostname" from ohthree.
  This will be a good mechanism to find flag potentials errors.  I have found cases where names differ.  I believe
  the pyrax-found name is correct and the "vm-data/hostname" found name is possibly incorrect.  VM-data is found using
  ohthree API and pulled from xenstore database.  This database entry could be incorrect but still investigating.
-add 'total cloud files space consumed'    <---DONE
-if no servers, print "no servers" instead of blank table
- show the X-Storage-URL...see below
$ curl -D - -H"X-Auth-User: USERNAME" -H"X-Auth-Key: USERAUTHKEY" https://auth.api.rackspacecloud.com/v1.0HTTP/1.1 204 No Content
Server: nginx/0.8.55
vary: Accept, Accept-Encoding, X-Auth-Token, X-Auth-Key, X-Storage-User, X-Storage-Pass, X-Auth-User
X-Storage-Url: https://storage101.dfw1.clouddrive.com/v1/MossoCloudFS_cefef46-827c-8fi3-921e-8a5dafeec42b
"""

 
from time import sleep
import curses
from curses import wrapper
import sys
import os
import curses.wrapper  #this will help reset terminal by catching exceptions and preventing effed up shells
import pyrax
import requests
from urlparse import urlparse
from urlparse import urlunparse
import json
from types import *          #<-----good for 'assert type(x) is IntType|StringType, 'message here if exception %r' % x'
from dateutil import parser     #<----dependency for time_converter()
from operator import itemgetter
from math import log   #<----dependency for byte_converter()
import cgitb   #<---this provides detailed tracebacks on error
import pdb   #<---python debugger - insert pdb.set_trace()

#enable detailed tracebacks
cgitb.enable(format='text')

###########################
#SET UP GLOBAL VARIABLES
MENU = "menu"
COMMAND = "command"
EXITMENU = "exitmenu"
CREDS_FILE = os.path.expanduser("~/.rackspace_cloud_credentials")
LOG_FILE = "/var/log/CCBridge.log"
data = []     #<---- this is a list of dictionaries.  Used with format_as_table()
titles = []   #<---this is a list that contains the title_row ..[('x', 'y'), ('z', 'w')].  Used with format_as_table()
unit_list = zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 2, 2, 2])     #<-- used in bytes conversion in byte_converter()
RACKER = False
SPACER = "\n\n"   #<---this will provide a blank two-line seperator for formatting purposes

#set identity class
pyrax.set_setting('identity_type', 'rackspace')
#I can set the region here#
#pyrax.set_setting("region", "LON")


#Determine if user is a racker, or more specifically, if currently operating on the Rackspace internal network.  Necessary if
# using the OhThree() class to scrape server info.
status_code = ''
try:
  status_code = urlopen("https://alerts.ohthree.com").code
except:
  RACKER = False
if status_code == 200:
  RACKER = True


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

#Before doing anything, curses must be initialized. This is done by calling the initscr() function,
#which will determine the terminal type, send any required setup codes to the terminal, 
#and create various internal data structures. If successful, initscr() returns a window object
# representing the entire screen
screen = curses.initscr()

#turn off automatic echoing of keys to the screen, 
#in order to be able to read keys and only display them under certain circumstances.
curses.noecho()

#react to keys instantly, without requiring the Enter key to be pressed
curses.cbreak()

# Lets you use colors when highlighting selected menu option
curses.start_color()

#Terminals usually return special keys, such as the cursor keys or navigation keys such as 
#Page Up and Home, as a multibyte escape sequence. While you could write your application to 
#expect such sequences and process them accordingly, curses can do it for you, returning a 
#special value such as curses.KEY_LEFT.   Could also use screen.keypad(True)
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
     { 'title': "Show Credentials", 'type': COMMAND },
   ]
   },
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
   { 'title': "List DNS Records", 'type': COMMAND },
]
}

#END CREATE MENU ^
############################
#CLASSES

class URLBuilder( object ):
  """
  #print bldr will just return the url provided.
  bldr = URLBuilder('https://mycloud.rackspace.com/my/path/to/server/instance')

  #Call bldr and specify components to BUILD a URL -- 'print myurl' returns https://kidrack.com/new/path/
  myurl = URLBuilder(scheme='https', netloc='kidrack.com', path='/new/path/')
  print myurl
  """
  def __init__( self, base ):
    self.parts = list( urlparse(base) )
  def __call__( self, scheme=None, netloc=None, path=None):
    if scheme is not None: self.parts[0] = scheme
    if netloc is not None: self.parts[1]= netloc
    if path is not None: self.parts[2]= path
    return urlunparse( self.parts )

class OhThree():
  """This class will be used to interact with the https://alerts.ohthree.com API.  Also, we will
  use to scrape https://reports.ohthree.com for instance information not available in alerts.ohthree.com
  """
  def __init__(self, target, type=None, path=None, url='alerts.ohthree.com'):
    """Initialize where type is an available api endpoint.
    type = [vminfo|hosts|glanceprocess|network_diagnostic|tcpdump]
    target = ['server-instance-UUID'|'host-server-display-name']
    We will need instance_uuid which is the uuid in attribute 'name-label ( RW): instance-04be189d-d7aa-4b93-8cf3-244de776f03c'. 
    We will require a 'host_name' attribute as well.  The host_name is the core host name which consists of last 
    three octets of host IP and host server core ID (ex: 23-210-195-453130).  We will need instance uuid OR the host_name.
    """
    #self.host_name = host_name
    if type is None:
      type = 'vminfo'
    if path is None:
      path = 'api'
    self.type = type
    self.target = target
    self.path = path
    self.url = url
  
  def getResponse(self):
    """Return the json response of the URL of the target instance."""
    mypath = [self.path, self.type, self.target]
    joined_path = '/'.join(mypath)
    initialize_url = URLBuilder('')
    vm_url = initialize_url(scheme='https', netloc=self.url, path=joined_path)
    response = my_Requests(vm_url)
    return response

  def getType(self):
    """Return type - default value is 'vminfo'.  This could also be 'hosts',
    'glanceprocess', 'network_diagnostic', 'tcpdump' if set explicitly"""
    return self.type
    
  def getInstance_UUID(self):
    """Return instance/server UUID used to query ohthree api"""
    return self.target
    
  def getPath(self):
    """Return the path portion of the url.  This will be always be 'api', which
    is the default value."""
    return self.path
  
  def getPowerState(self):
    """Return the current power state of server"""
    r = self.getResponse()
    my_power_state = r.json()['vm_info']['power_state']
    return my_power_state
  
  def getVDIList(self):
    """Return dictionaries containing VDI chain details."""
    r = self.getResponse()
    my_vdi_list = r.json()['vm_info']['vdi_list']
    return my_vdi_list

  def getDiskSize(self):
    r = self.getResponse()
    pass

  def getPhysicalUtilization(self):
    r = self.getResponse()
    pass
  
  #def getVirtualSize(self):
  #  vm_virt_size = byte_converter(int(response.json()['vm_info']['vdi_list'][0]['virtual_size']))
  #  return vm_virt_size
  #
  #def getPhysicalSize(self):
  #  vm_phy_size = byte_converter(int(response.json()['vm_info']['vdi_list'][0]['phy_utilization']))
  #  return vm_phy_size
  
  def getDomId(self):
    r = self.getResponse()
    my_dom_id = r.json()['vm_info']['dom_id']
    return my_dom_id
  
  def getCell(self):
    r = self.getResponse()
    my_cell = r.json()['cell']
    return my_cell
  
  def getServerName(self):
    r = self.getResponse()
    my_server_name = r.json()['vm_info']['xenstore_data']['vm-data/hostname']
    return my_server_name
  
  def getNameLabel(self):
    r = self.getResponse()
    my_name_label = r.json()['vm_info']['name_label']
    return my_name_label
  
  def getStorageRepository(self):
    r = self.getResponse()
    my_storage_repository = r.json()['vm_info']['sr_uuid']
    return my_storage_repository
  
  def getNetworkingDict(self):
    """Returns dictionary of network data about instance."""
    r = self.getResponse()
    dict = r.json()['vm_info']['xenstore_data']
    return dict

  def getNetworkingDictKeys(self):
    """Returns dictionary of network data about instance."""
    r = self.getResponse()
    my_networking_dict = r.json()['vm_info']['xenstore_data']
    keys = my_networking_dict.keys()
    return keys

  def getNetworkData(self, iptype):
    """Return dictionary of private or public network data - based on 'iptype' passed.
    'iptype' input parameter will be either 'public' or 'private'
    """
    r = self.getResponse()
    my_network_keys = self.getNetworkingDictKeys()
    my_ips = []
    my_networks = []
    
    for line in my_network_keys:
      if re.search('{0}'.format('networking'), line): 
        my_networks.append(line)
    for ntwrk in my_networks:
      x = str(r.json()['vm_info']['xenstore_data'][ntwrk])
      my_ips.append(x)
    for item in my_ips:
      y = json.loads(item)
      mykeys = y.keys()
      if y['label'] == 'private':
        private_network = {}
        for key in mykeys:
          private_network.update({key:y[key]})
    for item in my_ips:
      y = json.loads(item)
      mykeys = y.keys()
      if y['label'] == 'public':
        public_network = {}
        for key in mykeys:
          public_network.update({key:y[key]})
    #Return dictionary of public network data
    if iptype == 'public':
      filtered_public_network = {key:public_network[key] for key in public_network if key!='ip6s' and key!='gateway_v6'}
      return filtered_public_network
    #Return dictionary of private network data
    if iptype == 'private':
      filtered_private_network = {key:private_network[key] for key in private_network if key!='ip6s' and key!='gateway_v6'}
      return filtered_private_network
  
    ##---..---use these templates for ip isolation
    #broadcast_public_ip = filtered_public_network['broadcast']
    #self.broadcast_public_ip = broadcast_public_ip
    #print self.broadcast_public_ip
    #
    #mac_public_ip = filtered_public_network['mac']
    #dns_servers_public = filtered_public_network['dns']
    #label_public = filtered_public_network['label']
    #broadcast_private_ip = filtered_private_network['broadcast']
    #mac_private_ip = filtered_private_network['mac']
    #dns_servers_private = filtered_private_network['dns']
    #label_private = filtered_private_network['label']
    
    header = ['LABEL', 'SERVER IP', 'GATEWAY', 'NETMASK', 'STATUS' ] #<---status is enabled/disabled. label is public/private
    keys = ['label', 'ip', 'gateway', 'netmask', 'status' ]
    sort_by_key = 'label'
    sort_order_reverse = True
    data = []
    ip_control_pub = 0
    for i in filtered_public_network['ips']:
      ip_control_pub += 1
      enabled = i['enabled']
      if enabled:
        status = 'Enabled'
      else:
        status = 'Disabled'
      label = label_public
      ip = i['ip']
      gateway = i['gateway']
      netmask = i['netmask']
      data.append({'label':label_public, 'ip':ip, 'gateway':gateway, 'netmask':netmask, 'status':status})
    ip_control_priv = 0
    for i in filtered_private_network['ips']:
      ip_control_priv += 1
      enabled = i['enabled']
      if enabled:
        enabled = 'Enabled'
      else:
        enabled = 'Disabled'
      label = label_private
      ip = i['ip']
      gateway = i['gateway']
      netmask = i['netmask']
      data.append({'label':label_private, 'ip':ip, 'gateway':gateway, 'netmask':netmask, 'status':status})


#END CLASSES ^^
############################
# START FUNCTIONS SECTION

def my_Requests(url):
  """Used to grab the url and parse/format relevant information.  Used by OhThree() """
  # url below example: https://alerts.ohthree.com/api/vminfo/04be189d-d7aa-4b93-8cf3-244de776f03c
  response = requests.get(url=url, verify=False)
  assert response.status_code == 200, 'Attempted to access %r but received return code %r' % (url, response.status_code)
  return response

def terminal_size():
  """Get the terminal row and column length for building fit-to-screen content"""
  rows, cols = os.popen('stty size', 'r').read().split()
  return {'rows':rows, 'columns':cols}

def byte_converter(num):
  """Use this to convert bytes to human readable sizes"""
  assert type(int(num)) is IntType, 'Data supplied to byte_converter(num) is not an integer --> num = %r' % num
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

def time_converter(cloud_time):
  """This will accept the creation time of cloud products and convert to a
  more user-friendly format.  Sample return is 'Fri May  3 14:33:24 2013'
  """
  dt = parser.parse(cloud_time)
  #return dt.ctime()
  return "%d/%d/%d" % (dt.month, dt.day, dt.year)
  
def requests(url):
  """This function may not be needed!  At very least it should be renamed to no conflict with the real
  'requests' module
  """
  response = requests.get(url=url, verify=False)
  assert response.status_code == 200, 'Attempted to access %r but received return code %r' % (url, response.status_code)
  # url below example: https://alerts.ohthree.com/api/vminfo/04be189d-d7aa-4b93-8cf3-244de776f03c
  url = 'https://alerts.ohthree.com/api/vminfo/' + instance_uuid
  headers_ohthree = {'Content-Type': 'application/json'}
  filters = [dict(name='name', op='like', val='%y%')]
  params = dict(q=json.dumps(dict(filters=filters)))  #<---The query parameter q must be a JSON string.
  #response = requests.get(url, params=params, headers=headers_ohthree)
  #print response.text
  #response.json()['vm_info']['power_state']
  vm_virt_size = response.json()['vm_info']['vdi_list'][0]['virtual_size']
  vm_phy_size = response.json()['vm_info']['vdi_list'][0]['phy_utilization']
  print response.json()

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

def myTitle(title):
  """This is the header/title.  Pass a string as title.  This title occupies full terminal width"""
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
  print SPACER
  print ""

def my_half_Title(title):
  """This is the header/title.  Pass a string as title.  This title occupies half the terminal windows width"""
  term = terminal_size()
  col = term['columns']
  row = term['rows']
  pcol = (int(col) / 2)
  prox = (int(row) / 2)
  upper_title_line = '=' * int(pcol)
  lower_title_line = upper_title_line
  x = int(pcol) - len(title)
  x2 = x / 2
  y = '-' * x2
  print upper_title_line 
  print y + title + y
  print lower_title_line
  print ""

def clear_screen():
  """This function is used to pause and allow the user to view the table output.  You can hit 'enter' or keyboard your way out of the table
  view gracefully
  """
  print SPACER
  try:
    input("Press Enter to continue...")
    screen.clear()
  except (KeyboardInterrupt,EOFError), e:
    screen.clear() #clears previous screen on key press and updates display based on pos
  except:
    screen.clear() #clears previous screen on key press and updates display based on pos

#def get_API_key():
#  my_api_key = pyrax.identity.api_key
#  print "API key: %s" % my_api_key

def token():
  """Call this function to print string containing current auth token"""
  token = pyrax.identity.token
  print "Todays Token: %s" % token


def expires():
  """Call this function to print string containing the current auth token expiration time"""
  expires = pyrax.identity.expires
  print "Token Expires: %s" % expires
  
def authenticated_user():
  """Call this funtion to print string containing the current authed username"""
  clouduser = pyrax.identity.username
  print "Authenticated user: %s" % clouduser

def default_region():
  """Call this function to print string containing the current default region for authed user"""
  dregion = pyrax.identity.user['default_region']
  print "Default region: %s" % dregion

def name():
  """Call this function to print string containing the current authed username.  This is almost a duplicate of authenticated_user()
  so it may be able to be deprecated"""
  customer_username = pyrax.identity.username
  print "Username: %s" % customer_username

def tenant_ID():
  """Return customer DDI number, also referred to as tenant_id"""
  ddi = pyrax.identity.tenant_id
  return ddi
  
def print_cust_ddi():
  """When formatting screen with credential details, use this to return nice string containing DDI"""
  print "DDI: %s" % tenant_ID()
  
def getcreds():
  """Call this function to authenticate.  It will set credentials using local credentials file (~/.rackspace_cloud_credentials)"""
  try:
    #set crentials
    pyrax.set_credential_file(CREDS_FILE, authenticate=True)
  except Exception, e:
    print SPACER
    print e
    print SPACER
    clear_screen()
  else:
    auth_successful = pyrax.identity.authenticated
    print ""
    print ""
    print "Authentication successful: %s" % auth_successful
    name()
    #get_API_key()
    token()
    expires()
    default_region()
    print_cust_ddi()
    clear_screen()

def services():
  """Call this function to print service catalogue, as json data, for authed user"""
  services = json.dumps(pyrax.identity.services, sort_keys=True, indent=2, separators=(',', ': '))
  print services
  clear_screen()

def input_user_creds():
  """Call this function when you need to manually enter credentials.  It will prompt for user input and
  authenticate using provided credentials.  It will print the authentication information for provided user/creds"""
  print SPACER
  username = raw_input("Enter customer username: ")
  apikey = raw_input("Enter customer API key: ")
  pyrax.set_credentials(username, apikey)
  auth_successful = pyrax.identity.authenticated
  print SPACER
  print "Authentication successful: %s" % auth_successful
  name()
  print_cust_ddi()
  token()
  expires()
  default_region()
  clear_screen()

def auth_check():
  """Call this function to return True/False regarding status of current auth.  Am I authenticated as a user or not"""
  authed = pyrax.identity.authenticated
  if authed:
    return True
  else:
    return False

def not_authed():
  """If not authenticated print string message telling user to authenticate."""
  print SPACER
  print "Not Authenticated!\n  Please authenticate using option #1 (use local credentials file) or use option #2 (enter credentials manually)"
  clear_screen()

def show_credentials():
  """Print the current authenticated credentials"""
  #authed = pyrax.identity.authenticated
  try:
    if auth_check():
      print ""
      print ""
      name()
      print_cust_ddi()
      #get_API_key()
      token()
      expires()
      default_region()
      clear_screen()
  except:
    not_authed()
    #clear_screen()

def flavorlist():
  """Print all available flavors with details"""
  print SPACER
  #Draw title bar with included string
  myTitle('MY FLAVOR LIST')
  
  #Create connection to the cloud and create object containing list of flavors
  cs = pyrax.cloudservers
  flvrs = cs.flavors.list()
  my_flvrs = [flvr for flvr in flvrs]
  
  #Create list named 'data' to be used for table input
  data = []
  
  #Set up table variables and print table
  header = ['Flavor Name', 'ID', 'RAM', 'Disk', 'VCPUs', 'Swap' ]
  keys = ['name', 'id', 'ram', 'disk', 'vcpus', 'swap' ]
  sort_by_key = 'id'
  sort_order_reverse = False
  for flv in my_flvrs:
    data.append({'name':flv.name, 'id':flv.id, 'ram':flv.ram, 'disk':flv.disk, 'vcpus':flv.vcpus, 'swap':flv.swap})
  try:
    print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
    clear_screen()
  except Exception, e:
    print SPACER
    #print the exception to screen and allow graceful return to program
    print e
    print SPACER
    clear_screen()
  #print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
  #clear_screen()

def serverlist():
  """Use to create a table containing list of servers by region.  This list will contain server details formatted
  nicely"""
  print SPACER
  #Draw title bar with included string
  myTitle('CLOUD SERVERS')

  #Create connection to cloud servers and get list of servers.  Also set up
  # various variables for server iteration.  Seperate lists by region.
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

  #Create list named 'data' to be used for table input
  data = []
  
  #Iterate servers by region and append to server details to 'data'.
  status = ''
  try:
    if len(my_dfw_servers) != 0:
      for pos, svr in enumerate(my_dfw_servers):
        region = 'DFW'
        public_ip = []
        private_ip = []
        try:
          for i in range(len(svr.addresses['public'])):
            if svr.addresses['public'][i]['version'] == 4:
              public_ip.append(svr.addresses['public'][i]['addr'])
              public_ip = ",".join(public_ip)
          for i in range(len(svr.addresses['private'])):
            if svr.addresses['private'][i]['version'] == 4:
              private_ip.append(svr.addresses['private'][i]['addr'])
              private_ip = ",".join(private_ip)
        except:
          pass
        data.append({'pos': pos + 1, 'name':svr.name, 'public_ip':public_ip, 'private_ip':private_ip, 'UUID':svr.id, 'region':region, 'status':svr.status, 'progress':svr.progress, 'created':time_converter(svr.created)})
  except:
    pass

  try:
    if len(my_ord_servers) != 0:
      for pos, svr in enumerate(my_ord_servers):
        region = 'ORD'
        public_ip = []
        private_ip = []
        try:
          for i in range(len(svr.addresses['public'])):
            if svr.addresses['public'][i]['version'] == 4:
              public_ip.append(svr.addresses['public'][i]['addr'])
              public_ip = ",".join(public_ip)
          for i in range(len(svr.addresses['private'])):
            if svr.addresses['private'][i]['version'] == 4:
              private_ip.append(svr.addresses['private'][i]['addr'])
              private_ip = ",".join(private_ip)
        except:
          pass
        data.append({'pos': pos + 1, 'name':svr.name, 'public_ip':public_ip, 'private_ip':private_ip, 'UUID':svr.id, 'region':region, 'status':svr.status, 'progress':svr.progress, 'created':time_converter(svr.created)})
  except:
    pass
  
  #Set up table variables and print table
  header = ['Server Name', 'Region', 'Instance UUID', '  Public IP  ', '  Private IP  ', 'Status', 'Progress', 'Created Date' ]
  keys = ['name', 'region', 'UUID', 'public_ip', 'private_ip', 'status', 'progress', 'created' ]
  sort_by_key = 'region'
  sort_order_reverse = False
  try:
    print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
    clear_screen()
  except Exception, e:
    print SPACER
    #print the exception to screen and allow graceful return to program
    print e
    print SPACER
    clear_screen()
  #print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
  #clear_screen()

def getimagelist(base=False):
  """Interact with images using this function.  Passing base=True will print base images from Rackspace.
  Leaving base=false will return your saved images and NOT base images from Rackspace.
  """
  print SPACER
  #Draw title bar with included string
  myTitle('MY IMAGES')
  
  #Create connection to cloud servers
  try:
    cs = pyrax.cloudservers
  except:
    print "Unable to connect to pyrax.cloudservers"
    clear_screen()
  
  #Create base image list
  all_base_images = cs.images.list()
  base_images = [img for img in all_base_images if not hasattr(img, "server")]
  
  #Initialize variables containing image lists for each region
  dfw_images = []
  ord_images = []
  lon_images = []
  
  #Create connection to cloud servers with region set to DFW and create an object to hold list of images
  try:
    svrs_dfw = pyrax.connect_to_cloudservers(region="DFW")
    dfw_images = svrs_dfw.images.list()
  except:
    #print "Unable to connect to cloudservers DFW"
    pass
  
  #Create connection to cloud servers with region set to ORD and create an object to hold list of images
  try:
    svrs_ord = pyrax.connect_to_cloudservers(region="ORD")
    ord_images = svrs_ord.images.list()
  except:
    pass
  
  #Create connection to cloud servers with region set to LON and create an object to hold list of images
  try:
    svrs_lon = pyrax.connect_to_cloudservers(region="LON")
    lon_images = svrs_ord.images.list()
  except:
    pass
  
  #Gather all images together into one object named 'all_images'
  all_imgs = dfw_images + ord_images + lon_images
  
  #Create iterable list object of all images with the attribute 'server', which means it is
  # a saved image and not a base image from Rackspace
  images = [img for img in all_imgs if hasattr(img, "server")]
  sort_by_key = ''
  
  #If no saved images then do not print table.  Print message instead
  if not images:
    print SPACER
    print "You have no images!"
    clear_screen()
    
  #Create iterable list of saved images (not base) in DFW and ORD, respectively
  my_dfw_images = [img for img in dfw_images if hasattr(img, "server")]
  my_ord_images = [img for img in ord_images if hasattr(img, "server")]
  my_lon_images = [img for img in lon_images if hasattr(img, "server")]
  
  #create list named data (or delete contents if exists).  This list used as input for format_as_table()
  data = []
  
  #If base=True then set up table to print base Rackspace images
  if base:
    #Create table variables
    header = ['Image Name', 'Image ID']
    keys = ['name', 'ID']
    #sor_by_key = 'name'
    sort_order_reverse = False
    for img in base_images:
      data.append({'name':img.name, 'ID':img.id})
    try:
      print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
      clear_screen()
    except Exception, e:
      print SPACER
      #print the exception to screen and allow graceful return to program
      print e
      print SPACER
      clear_screen()
  else:
    #If base=False (default) then set up table to print saved iamges
    header = ['Image Name', 'Region', 'Image ID', 'Min RAM', 'Min Disk', 'Status', 'Progress' ]
    keys = ['name', 'region', 'ID', 'minram', 'mindisk', 'status', 'progress' ]
    #sort_by_key = 'region'
    sort_order_reverse = False
    for pos,img in enumerate(my_dfw_images):
      region = 'DFW'
      data.append({'pos':pos + 1, 'name':img.name, 'region':region, 'ID':img.id, 'minram':img.minRam, 'mindisk':img.minDisk, 'status':img.status, 'progress':img.progress})
    for pos, img in enumerate(my_ord_images):
      region = 'ORD'
      data.append({'pos':pos + 1, 'name':img.name, 'region':region, 'ID':img.id, 'minram':img.minRam, 'mindisk':img.minDisk, 'status':img.status, 'progress':img.progress})
    for pos, img in enumerate(my_lon_images):
      region = 'LON'
      data.append({'pos':pos + 1, 'name':img.name, 'region':region, 'ID':img.id, 'minram':img.minRam, 'mindisk':img.minDisk, 'status':img.status, 'progress':img.progress})
    try:
      print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
      clear_screen()
    except Exception, e:
      print SPACER
      #print the exception to screen and allow graceful return to program
      print e
      print SPACER
      clear_screen()

def getLBlist():
  """Report information about cloud load balancers"""
  print SPACER
  #Print title bar with lincluded string
  myTitle('MY LOAD BALANCERS')
  
  #Create connection to cloud load balancers
  try:
    lb = pyrax.cloud_loadbalancers
  except:
    print "Unable to connect to cloud load balancers!"
    clear_screen()
  
  #Capture all load balancers in an object
  all_lbs = lb.list()
  
  #Create iterable object 'lbs' containing list of load balancers
  lbs = [loadb for loadb in all_lbs]
  
  #create list named data (or delete contents if exists).  This list used as input for format_as_table()
  data = []
  
  #for every load balancer add dict of details to data list
  for pos, lb in enumerate(lbs):
    public_ip = lb.virtual_ips[0].address
    data.append({'pos': pos + 1, 'name':lb.name, 'public_ip':public_ip, 'protocol':lb.protocol, 'port':lb.port, 'status':lb.status})
  
  #Set up table varaibles and print table
  header = [ 'Load Balancer Name', '  IP Address  ', 'Protocol', 'Port', 'Status' ]
  keys = [ 'name', 'public_ip', 'protocol', 'port', 'status' ]
  sort_by_key = 'status'
  sort_order_reverse = False
  #If no load balancers exist don't print table, else print table with data
  if not lbs:
    print SPACER
    print "You have no load balancers!"
    print SPACER
    clear_screen()
  else:
    try:
      print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
      clear_screen()
    except Exception, e:
      print SPACER
      #print the exception to screen and allow graceful return to program
      print e
      print SPACER
      clear_screen()

def getDBlist():
  """Provide information about cloud databases"""
  print SPACER
  print "This function is not support at this time"
  print SPACER
  clear_screen()

def getDNSlist():
  """Report all DNS records/domains registered with cloud account"""
  print SPACER
  #Draw title line with string included
  myTitle('CLOUD DNS')
  
  #Create connection to cloud DNS and list as object
  try:
    dns = pyrax.cloud_dns
    dns_domains = dns.list()
  except Exception, e:
    print SPACER
    print "Unable to create connection to cloud_dns"
    print SPACER
    print e
    clear_screen()

  #Gather a list of domain names and id numbers into a list of dictionaries
  dns_domain_names_id = []
  for i in dns.list():
    dns_domain_names_id.append({i.id:str(i.name)})

  #Using the list dns_domains, gather list if domain ID numbers for later use
  dns_idnumbers = []
  for i in dns_domains:
    dns_idnumbers.append(i)

  #Create list named name_email and append dictionaries comprised of domain name, administrator email address, and the domain ID
  name_email = []
  for i in dns_domains:
    name_email.append({'name':i.name, 'email':i.emailAddress, 'id':str(i.id)})

  #Create a list named dns_data and append dictionaries containing all DNS data to be parsed
  dns_data = []
  for i in dns_idnumbers:
    dns_data.append(dns.list_records(i))

  #create list named data (or delete contents if exists).  This list used as input for format_as_table()
  data = []
  
  #-->For every root domain name in the list dns_data...
  for x in range(len(dns_data)):
    #-->For every DNS record within each root domain...
    for y in range(len(dns_data[x])):
      #Save root domain name as domainName
      domainName = name_email[x]['name']
      #Save administrator email as domainEmail
      domainEmail = name_email[x]['email']
      #this variable 'pad' is used to pad data with spacces for formatting
      pad = '  '
      
      #If the dns record is the first in the list - or record 0- then use actual domain name in table column
      if y == 0:
        #Append information to the list 'data' to be used in format_as_table()
        data.append({'domain':(domainName + pad), 'dns_record':(dns_data[x][y].name + pad), 'target':(dns_data[x][y].data + pad), 'record_type':dns_data[x][y].type, 'created':time_converter((dns_data[x][y].created) + pad), 'ttl':dns_data[x][y].ttl })
      #Now every other DNS record within this root domain will have just 2 dashes in the domain name table column
      else:
        #set domain name table column to 2 dashes
        domainName = '   --  '
        #Append information to the list 'data' to be used in format_as_table()
        data.append({'domain':(domainName + pad), 'dns_record':(dns_data[x][y].name + pad), 'target':(dns_data[x][y].data + pad), 'record_type':dns_data[x][y].type, 'created':time_converter((dns_data[x][y].created) + pad), 'ttl':dns_data[x][y].ttl })
  
  #Set up table varaibles and print table
  header = [ 'Domain Name', 'DNS Record', '  Target  ', 'Record Type', '   Created   ', 'TTL' ]
  keys = [ 'domain', 'dns_record', 'target', 'record_type', 'created', 'ttl' ]
  sort_by_key = ''
  sort_order_reverse = False
  try:
    print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
    #call clear_screen() to reset the terminal
    clear_screen()
  except Exception, e:
    print SPACER
    #print the exception to screen and allow graceful return to program
    print e
    print SPACER
    clear_screen()

def getCNlist():
  #print space buffer at top of terminal for formatting purposes
  print SPACER
  
  #Draw title bar with string included
  myTitle('CLOUD FILES')
  
  #create a connection to cloud files for later use if necessary
  try:
    cfiles = pyrax.cloudfiles
  except:
    print "Unable to connect to pyrax.cloudfiles"
    clear_screen()
  
  #Save default region
  def_region = pyrax.default_region
  
  #Initialize container list for each region
  ord_containers = []
  dfw_containers = []
  lon_containers = []
  
  #Connect to cloud files by region and create a list of containers in each region.
  try:
    #dfw_containers = cf_dfw.list_containers_info()
    cf_dfw = pyrax.connect_to_cloudfiles(region='DFW')
    dfw_containers = cf_dfw.get_all_containers()
  except:
    pass
  try:
    #ord_containers = cf_ord.list_containers_info()
    cf_ord = pyrax.connect_to_cloudfiles(region='ORD')
    ord_containers = cf_ord.get_all_containers()
  except:
    pass
  try:
    #lon_containers = cf_lon.list_containers_info()
    cf_lon = pyrax.connect_to_cloudfiles(region='LON')
    lon_containers = cf_lon.get_all_containers()
  except:
    pass
  
  #All containers combined into one list
  all_containers = dfw_containers + ord_containers + lon_containers
  
  #Capture a running total count of all containers combined
  total_obj = 0
  
  #Initialize variable named total_bytes to capture a running total count of all bytes used in cloud files
  total_bytes = 0
  
  #Create list named data (or delete contents if exists).  This list used as input for format_as_table()
  data = []

  #Gather a list of dfw containers and append them to the list named data
  for cn in dfw_containers:
    region = 'DFW'
    #number_bytes = int(cn['bytes'])
    number_bytes = cn.total_bytes
    size = byte_converter(number_bytes)
    #count = cn['count']
    count = cn.object_count
    name = cn.name
    cdn_logs = cn.cdn_log_retention
    cdn_logs_table = '---'
    cdn = cn.cdn_enabled
    cdn_table = '---'
    uri = '---'
    if cdn:
      uri = cn.cdn_uri
      cdn_table = cdn
    data.append({'name':name,
                 'total_objects':count,
                 'region':region,
                 'size':size,
                 'cdn':cdn_table,
                 'cdn_logs':cdn_logs_table,
                 'http_uri':uri})
    
    #Increment total_obj by the number of objects in the current container
    total_obj += count
    
    #Increment total_bytes by the number of bytes in variable 'number_bytes'
    total_bytes += number_bytes
    
  #Gather a list of ord containers and append them to the list named data
  for cn in ord_containers:
    region = 'ORD'
    number_bytes = cn.total_bytes
    size = byte_converter(number_bytes)
    count = cn.object_count
    name = cn.name
    cdn_logs = cn.cdn_log_retention
    cdn_logs_table = '---'
    cdn = cn.cdn_enabled
    cdn_table = '---'
    uri = '---'
    if cdn:
      uri = cn.cdn_uri
      cdn_table = cdn
    data.append({'name':name,
                 'total_objects':count,
                 'region':region,
                 'size':size,
                 'cdn':cdn_table,
                 'cdn_logs':cdn_logs_table,
                 'http_uri':uri})
    #Increment total_obj by the number of objects in the current container
    total_obj += count
    
    #Increment total_bytes by the number of bytes in variable 'number_bytes'
    total_bytes += number_bytes

  #Gather a list of lon containers and append them to the list named data
  for cn in lon_containers:
    region = 'LON'
    number_bytes = cn.total_bytes
    size = byte_converter(number_bytes)
    count = cn.object_count
    name = cn.name
    cdn_logs = cn.cdn_log_retention
    cdn_logs_table = '---'
    cdn = cn.cdn_enabled
    cdn_table = '---'
    uri = '---'
    if cdn:
      uri = cn.cdn_uri
      cdn_table = cdn
    data.append({'name':name,
                 'total_objects':count,
                 'region':region,
                 'size':size,
                 'cdn':cdn_table,
                 'cdn_logs':cdn_logs_table,
                 'http_uri':uri})    
    #Increment total_obj by the number of objects in the current container
    total_obj += count
    
    #Increment total_bytes by the number of bytes in variable 'number_bytes'
    total_bytes += number_bytes
  
  #Set up table varaibles and print table
  header = ['Container Name', 'Total Objects', 'Region', 'Size', 'CDN Enabled', 'CDN Logs Enabled', '  HTTP CDN Base URL  ' ]
  keys = ['name', 'total_objects', 'region', 'size', 'cdn', 'cdn_logs', 'http_uri' ]
  sort_by_key = 'total_objects'
  sort_order_reverse = True
  try:
    print format_as_table(data, keys, header, sort_by_key, sort_order_reverse)
    print SPACER
    print "Total Objects = %s " % total_obj
    print "Total Space Consumed = %s" % byte_converter(total_bytes)
    print "Default Region = %s" % def_region
    print SPACER
  except Exception, e:
    print SPACER
    #print the exception to screen and allow graceful return to program
    print e
    print SPACER
    clear_screen()
  
  #Call clear_screen() to reset the terminal
  clear_screen()
    
#END FUNCTIONS ^
##################
# MAIN PROGRAM

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
      # convert keypress back to a number, then subtract 1 to get index
      pos = x - ord('0') - 1 
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
      #os.system(menu['options'][getin]['command']) # run a bash command if necessary
      if menu['options'][getin]['title'] == 'Enter credentials manually':
        input_user_creds()
      if menu['options'][getin]['title'] == 'List Servers':
        try:
          auth_check()
        except:
          not_authed()
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
      if menu['options'][getin]['title'] == 'List DNS Records':
        getDNSlist()
      if menu['options'][getin]['title'] == 'List Databases':
        getDBlist()
      # reset to 'current' curses environment
      curses.reset_prog_mode()
      # reset doesn't do this right
      curses.curs_set(1)
      curses.curs_set(0)
    elif menu['options'][getin]['type'] == MENU:
      #clears previous screen on key press and updates display based on pos
      screen.clear() 
      processmenu(menu['options'][getin], menu) # display the submenu
      #clears previous screen on key press and updates display based on pos
      screen.clear()
    elif menu['options'][getin]['type'] == EXITMENU:
      exitmenu = True

#Execute program
# This function calls showmenu and then acts on the selected item
try:
  wrapper(processmenu(menu_data))
except KeyboardInterrupt:
  curses.endwin() #VITAL! This closes out the menu system and returns you to the bash prompt.
  os.system('cls' if os.name=='nt' else 'clear')
  sys.exit()
finally:
  os.system('cls' if os.name=='nt' else 'clear')
  curses.endwin() #VITAL! This closes out the menu system and returns you to the bash prompt.
  sys.exit()
  
