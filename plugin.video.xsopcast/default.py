#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import sys, os, os.path, subprocess
import urllib, urllib2, socket, re
import time
from datetime import datetime, timedelta

import tarfile
import thread
import sqlite3
#from resources.lib.key import key
#import key
from urllib2 import urlopen
from urlparse import urlparse
from posixpath import basename, dirname
try:
    try:
        raise
        import xml.etree.cElementTree as ElementTree
    except:
        from xml.etree import ElementTree
except:
    try:
        from xml.etree.ElementTree import Element
        from xml.etree.ElementTree import SubElement
        from elementtree import ElementTree
    except:
        dlg = xbmcgui.Dialog()
        dlg.ok('ElementTree missing', 'Please install the elementree addon.',
                'http://tinyurl.com/xmbc-elementtree')
        sys.exit(0)

## this function takes the url and output the basename
def parse_url(url):
    parse_object = urlparse(url)
    try:
        return basename(parse_object[2])
    except:
        return 'chlist.xml'

settings = xbmcaddon.Addon(id='plugin.video.xsopcast')

#get current working directory which contains the script
ADDON_PATH= settings.getAddonInfo('path')
## check which platform we are on
OS = os.environ.get("OS","xbox")
#we can use the following code to detect whether the platform is 32 or 64 bit,
#but since sopcast provides only 32 bit binary, it's not much use here
#
#import struct
#if struct.calcsize('l') == 4:
#    vars()["spsc_"+OS] = "http://xbox-remote.googlecode.com/files/sp-sc-32"
#else:
#    vars()["spsc_"+OS] = "http://xbox-remote.googlecode.com/files/sp-sc-64
## the url for sp-sc binary (to be downloaded)
#vars()["spsc_"+OS] = "http://xbox-remote.googlecode.com/files/sp-sc"
vars()["spsc_"+OS] = "http://download.easetuner.com/download/sp-auth.tgz"
#Specific package for the raspberry pi
raspberrypi_tgz = "http://x-sopcast-with-rpi-support-xbmc.googlecode.com/svn/trunk/sopcast-raspberry.tar.gz"
# absolute path for the sopcast pid file
SOPCAST_PID = os.path.join(ADDON_PATH, 'sopcast.pid')
# url for channel list from offical sopcast website
CHAN_LIST_MAIN = settings.getSetting('chan_list_main')
if CHAN_LIST_MAIN=="Local":
   CHAN_LIST_1 = os.path.join(ADDON_PATH,"channel_guide.xml")
   CHAN_LIST_2 = "http://www.sopcast.com/chlist.xml"
   CHAN_LIST_3 = settings.getSetting('chan_list_url')
elif CHAN_LIST_MAIN=="Sopcast":
   CHAN_LIST_1 = "http://www.sopcast.com/chlist.xml"
   CHAN_LIST_2 = os.path.join(ADDON_PATH,"channel_guide.xml")
   CHAN_LIST_3 = settings.getSetting('chan_list_url')
elif CHAN_LIST_MAIN=="Remote":
   CHAN_LIST_1 = settings.getSetting('chan_list_url')
   CHAN_LIST_2 = os.path.join(ADDON_PATH,"channel_guide.xml")
   CHAN_LIST_3 = "http://www.sopcast.com/chlist.xml"

# periodicaly fetch the channel list
#CHAN_LIST_AUTO = settings.getSetting('chan_list_auto')
# define the channel list expire time (seconds). the defualt setting is 1 day, i.e. channel list older than 1 day will be
def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                    splitparams={}   
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
    return param

params=get_params()
mode=0
try:
    mode1=int(params["mode"])
except:
    mode1=0
if mode1>99:
    if mode1==300: mode=0
    else: mode=mode1/100
    CHAN_LIST_URL = CHAN_LIST_3
    CHAN_LIST = os.path.join(ADDON_PATH,parse_url(CHAN_LIST_3))
elif mode1>9:
    if mode1==30: mode=0
    else: mode=mode1/10
    CHAN_LIST_URL = CHAN_LIST_2
    CHAN_LIST = os.path.join(ADDON_PATH,parse_url(CHAN_LIST_2))
else:
    mode=mode1
    CHAN_LIST_URL = CHAN_LIST_1
    CHAN_LIST = os.path.join(ADDON_PATH,parse_url(CHAN_LIST_1))

if CHAN_LIST_URL == "http://www.sopcast.com/chlist.xml": CHAN_LIST_EXPIRE =  int(settings.getSetting('chan_list_expire'))*60*60
elif CHAN_LIST_URL == os.path.join(ADDON_PATH,"channel_guide.xml"): CHAN_LIST_EXPIRE = 0
else: CHAN_LIST_EXPIRE =  int(settings.getSetting('chan_list_expire_remote'))*60*60

#xbmcgui.Dialog().ok(CHAN_LIST_URL, CHAN_LIST, CHAN_LIST_URL)
#if CHAN_LIST_AUTO == "true" or not os.path.isfile(os.path.join(ADDON_PATH,settings.getSetting('chan_list'))):
#    CHAN_LIST = os.path.join(ADDON_PATH,parse_url(CHAN_LIST_URL))
#else:
#    CHAN_LIST = os.path.join(ADDON_PATH,settings.getSetting('chan_list'))
SHOW_ID = settings.getSetting('show_id')
SHOW_KBPS = settings.getSetting('show_kbps')
SHOW_STREAM_TYPE = settings.getSetting('show_stream_type')
# the name of binary for sopcast backend
SPSC_BINARY = "sp-sc-auth"
# the absolute path of the sopcast log file 
SPSC_LOG = os.path.join(ADDON_PATH,"sopcast.log")
# the absolute path of the sopcast binary
SPSC = os.path.join(ADDON_PATH,"sp-auth",SPSC_BINARY)
# the port sp-sc used to connect to other peers on the internet (to get stream)
LOCAL_PORT = settings.getSetting('local_port')
# the port on local pc you will be able to view the stream (encoded in vc-1) http://localhost:9001/
VIDEO_PORT = settings.getSetting('video_port')
#buffer size for python sub process
BUFER_SIZE = int(settings.getSetting('buffer_size'))
LOG_SOPCAST = settings.getSetting('log_sopcast')
# define local IP instead of localhost
if(settings.getSetting('auto_ip')):
    LOCAL_IP=xbmc.getIPAddress()
#    LOCAL_IP=socket.gethostbyname(socket.gethostname())
else: LOCAL_IP=settings.getSetting('localhost')
# path where the schedule xml files will be downloaded
SCH_FOLDER_PATH = os.path.join(ADDON_PATH, 'schedule')
PLAYING_GRAB = settings.getSetting('sch_grab_while_play')
#PLAYING_TITLE = settings.getSetting('renew_title_while_play')
SCH_OVER_EXPIRED = settings.getSetting('sch_over_expired')
SCH_NEW_EXPIRED = settings.getSetting('sch_expired')
SCH_GRAB_BEFORE_LIST = settings.getSetting('sch_grab_before_list')
SCH_SCROLLBAR_FOCUS = settings.getSetting('sch_scrollbar_focus')
NOTIFY_OFFLINE = settings.getSetting('notify_offline')
NOTIFY_EVENTS = settings.getSetting('notify_events')
NOTIFY_GRABBING = settings.getSetting('notify_grabbing')

#number of schedule events to add to channel name
SCHEDULE_EVENTS = int(settings.getSetting('sch_events'))
# timezone difference in hours
TIMEZONE_DELTA = int(settings.getSetting('sch_timezone_delta'))
# automaticaly calculate timezone difference
TIMEZONE_AUTO = settings.getSetting('sch_timezone_auto')
# language used  display the group info. sopcast list has two language set of description, one is english(en) and the other is cn(chinese). By default we will set it to english.
LANGUAGE = settings.getSetting('language')
## the supported platform we are running
PLATFORM = "Linux"


EPGPATH = os.path.join(ADDON_PATH,'epg.sql')

conn = sqlite3.connect(EPGPATH)
db_connection=conn.cursor()
db_connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='epg';")
et=db_connection.fetchone()
if not et or et[0] == 0: db_connection.execute('''create table epg (id int PRIMARY KEY, event_id int, channel_id int, channel text, event_time_local text, event_time_gmt text, title text, subtitle text, description text, thumbnail text)''')






## error code to handle exception
my_error = 0

ACTION_MOVE_LEFT      = 1
ACTION_MOVE_RIGHT     = 2
ACTION_MOVE_UP        = 3
ACTION_MOVE_DOWN      = 4
ACTION_PAGE_UP        = 5
ACTION_PAGE_DOWN      = 6
ACTION_SELECT_ITEM    = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR     = 9
ACTION_PREVIOUS_MENU  = 10
ACTION_SHOW_INFO      = 11
ACTION_PAUSE          = 12
ACTION_STOP           = 13
ACTION_NEXT_ITEM      = 14
ACTION_PREV_ITEM      = 15
ACTION_SHOW_GUI       = 18
ACTION_PLAYER_PLAY           = 79
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_CONTEXT_MENU   = 117
ACTION_NAV_BACK       = 92
ACTION_BUILT_IN_FUNCTION  = 122

ACTION_STEP_FORWARD = 20 # seek +1% in the movie. Can b used in videoFullScreen.xml window id=2005
ACTION_STEP_BACK = 21 # seek -1% in the movie. Can b used in videoFullScreen.xml window id=2005

ACTION_DELETE_ITEM = 80 # delete current selected item. Can be used in myfiles.xml window id=3 and in myvideoTitle.xml window id=25
ACTION_COPY_ITEM = 81 # copy current selected item. Can be used in myfiles.xml window id=3
ACTION_MOVE_ITEM = 82 # move current selected item. Can be used in myfiles.xml window id=3
ACTION_RENAME_ITEM = 87 # rename item
ACTION_BIG_STEP_FORWARD = 22 # seek +10% in the movie. Can b used in videoFullScreen.xml window id=2005
ACTION_BIG_STEP_BACK = 23 # seek -10% in the movie. Can b used in videoFullScreen.xml window id=2005

WINDOW_FULLSCREEN_VIDEO      =     12005
# set python default (string) encoding 
reload(sys)
sys.setdefaultencoding('utf-8')
                    #dialog = xbmcgui.Dialog()
                    #dialog.ok(SPSC_BINARY, f, str(pid))

xbmc_language = xbmc.getLanguage().split("(")[0].split(" ")[0]
if xbmc_language == "Chinese":
    LANGUAGE = "cn"


## downloader with a progress bar
def Downloader(url,dest,description,heading):
    dp = xbmcgui.DialogProgress()
    dp.create(heading,description,url)
    dp.update(0)
    urllib.urlretrieve(url,dest,lambda nb, bs, fs, url=url: _pbhook(nb,bs,fs,dp))
## helper function to Downloader()
def _pbhook(numblocks, blocksize, filesize,dp=None):
    try:
        percent = int((int(numblocks)*int(blocksize)*100)/int(filesize))
        dp.update(percent)
    except:
        percent = 100
        dp.update(percent)
    if dp.iscanceled(): 
#        raise KeyboardInterrupt
        dp.close()


# if the underlining PLATFORM is not supported then we will display some error messages to the user
if OS != PLATFORM:
    dialog = xbmcgui.Dialog()
    ok = dialog.ok(settings.getLocalizedString(30000), settings.getLocalizedString(30001), settings.getLocalizedString(30002)+PLATFORM+settings.getLocalizedString(30003))
elif OS == PLATFORM and os.uname()[4] != "armv6l":
    # get system default env PATH
    pathdirs = os.environ['PATH'].split(os.pathsep)
    # looking for (the first match) sp-sc-auth binary in the system default path
    for dir in pathdirs:
        if os.path.isdir(dir):
            if os.path.isfile(os.path.join(dir,SPSC_BINARY)):
                SPSC = os.path.join(dir,SPSC_BINARY)
                break
# if we cannot find the sp-sc binary we will download it from internet
    if not os.path.isfile(SPSC):
        SPSC_KIT = os.path.join(ADDON_PATH,parse_url(vars()["spsc_"+OS]))
        Downloader(vars()["spsc_"+OS],SPSC_KIT,settings.getLocalizedString(30004),settings.getLocalizedString(30005))
        if tarfile.is_tarfile(SPSC_KIT):
            tar = tarfile.open(SPSC_KIT)
            tar.extractall(ADDON_PATH)
            tar.close()
        os.remove(SPSC_KIT)
        try: os.chmod(SPSC,0755)
        except: pass
# check the length the binary, if its equals than zero then we download it from internet
    elif str(os.stat(SPSC)[6]).split('L')[0] == "0":
        SPSC_KIT = os.path.join(ADDON_PATH,parse_url(vars()["spsc_"+OS]))
        Downloader(vars()["spsc_"+OS],SPSC_KIT,settings.getLocalizedString(30004),settings.getLocalizedString(30005))
        if tarfile.is_tarfile(SPSC_KIT):
            tar = tarfile.open(SPSC_KIT)
            tar.extractall(ADDON_PATH)
            tar.close()
        os.remove(SPSC_KIT)
        try: os.chmod(SPSC,0755)        # set the correct permission each time as we want to absolutely sure it's executable
        except: pass
    # abosulte path for channel list (obtained from url)
else:
    # if the folder sopcast-raspberry doesn't exist it will download the sopcast engine. If it already exist, it will set all files and folders inside ~/sopcast-raspberry as executable.
    SPSC_KIT = os.path.join(ADDON_PATH,"spc-raspberry")
    if not os.path.exists(os.path.join(ADDON_PATH,"sopcast-raspberry")):
    	Downloader(raspberrypi_tgz,SPSC_KIT,settings.getLocalizedString(30004),settings.getLocalizedString(30005))
   	if tarfile.is_tarfile(SPSC_KIT):
    		tar = tarfile.open(SPSC_KIT)
    		tar.extractall(ADDON_PATH)
    		tar.close()
   	os.remove(SPSC_KIT)
    else:
    	def get_filepaths(directory):
		file_paths = []
		for root, directories, files in os.walk(directory):
			for filename in files:
				filepath = os.path.join(root, filename)
				file_paths.append(filepath) 
		return file_paths
	full_file_paths = get_filepaths(os.path.join(ADDON_PATH,"sopcast-raspberry"))
	print full_file_paths
	for file_or_folder in full_file_paths:
		os.system('chmod +x ' + file_or_folder)
    
def GET_PID():
    sop_pid=0
    if os.path.isfile(SOPCAST_PID):
        sop_pid = open(SOPCAST_PID, 'r').read()
    return sop_pid

## this function will try to seach for running sopcast, if there the pid file is not empty it will kill all the running sopcast instance
def KILL_SOP(OS):
    if os.path.isfile(SOPCAST_PID):
        sop_pid = open(SOPCAST_PID, 'r').read()
    if OS == PLATFORM:
        try:
            if len(sop_pid) > 0 and int(sop_pid) > 0:
                os.kill(int(sop_pid), 9)
                #if os.uname()[4] == "armv6l":
                	#try: os.system("killall -9 qemu-i386")
                	#except: pass
                return True
        except:
            return False


# need to fix the invalid url case
def FETCH_CHANNEL():
    if not os.path.isfile(CHAN_LIST):
        Downloader(CHAN_LIST_URL,CHAN_LIST,settings.getLocalizedString(30006),settings.getLocalizedString(30007))
# if the channel list contains no data we will down it from internet
    elif str(os.stat(CHAN_LIST)[6]).split('L')[0] == "0":
        Downloader(CHAN_LIST_URL,CHAN_LIST,settings.getLocalizedString(30006),settings.getLocalizedString(30007))
    else:
        now_time = time.mktime(datetime.now().timetuple())
        time_created = os.stat(CHAN_LIST)[8]  # get local play list modified date
        ## if the channel list is too old (channel_expire variable in user xml configuration file) then it will be downloaded from internet
        if CHAN_LIST_EXPIRE>0 and time.mktime(datetime.now().timetuple()) - os.stat(CHAN_LIST)[8] > CHAN_LIST_EXPIRE:
            Downloader(CHAN_LIST_URL,CHAN_LIST,settings.getLocalizedString(30006),settings.getLocalizedString(30007))

    try:
        groups = ElementTree.parse(CHAN_LIST).findall('.//group')
        unname_group_index = 1
        for group in groups:
            if group.attrib[LANGUAGE] == "":
                group.attrib[LANGUAGE] = settings.getLocalizedString(30008)+str(unname_group_index)
                unname_group_index = unname_group_index + 1
                if re.sub('c','e',LANGUAGE) == LANGUAGE:
                    OTHER_LANG = re.sub('e','c',LANGUAGE)
                else:
                    OTHER_LANG = re.sub('c','e',LANGUAGE)
                if LANGUAGE == "cn":
                    try:
                        if len(group.attrib[OTHER_LANG]) > 0:
                            group.attrib[LANGUAGE] = group.attrib[OTHER_LANG]
                            unname_group_index = unname_group_index - 1
                    except:
                        pass
            if (group.find('.//channel')==None): continue
            group_name=group.attrib[LANGUAGE]
            if mode1>99:
                addDir(group_name,'',100)
            elif mode1>9:
                addDir(group_name,'',10)
            else:
                addDir(group_name,'',1)
        if mode1<10:
            if CHAN_LIST == CHAN_LIST_URL:
                addDir("+ Sopcast server list" , "" , 30 )
                if(settings.getSetting('chan_list_remote')=="true"): addDir("+ Remote list" , "" , 300 )
            elif CHAN_LIST_URL=="http://www.sopcast.com/chlist.xml":
                addDir("+ Local list" , "" , 30 )
                if(settings.getSetting('chan_list_remote')=="true"): addDir("+ Remote list" , "" , 300 )
            else:
                addDir("+ Local list" , "" , 30 )
                addDir("+ Sopcast server list" , "" , 300 )
            addLink("Enter channel ID" , "" , 2 , "DefaultVideo.png" , "")

    except:
######## if we cannot parse the channel list, we will inform the end user
        dialog = xbmcgui.Dialog()
#        dialog.ok(CHAN_LIST_URL, CHAN_LIST, CHAN_LIST_URL)
        dialog.ok(settings.getLocalizedString(30000), settings.getLocalizedString(30009), settings.getLocalizedString(30010))
        f = open(CHAN_LIST,'w')
        f.write('')
        f.close()
        global my_error
        my_error = 1



### this function is to remove empty lines in the string
def remove_line(contents):
    new_contents = []
    # Get rid of empty lines
    for line in contents:
        # Strip whitespace, should leave nothing if empty line was just "\n"
        if not line.strip():
            continue
        # We got something, save it
        else:
            new_contents.append(line)
    return "".join(new_contents)
def remove(value, deletechars):
    for c in deletechars:
        value = value.replace(c,'')
    return value;


### parsing channel info for each group from the channel list
def INDEX(name):
            group = ElementTree.parse(CHAN_LIST).find(".//group/.[@"+LANGUAGE+"='"+name+"']")
            hasEPG=False
#    unname_group_index = 1
#    for group in groups:
#        if group.attrib[LANGUAGE] == "":
#            group.attrib[LANGUAGE] = settings.getLocalizedString(30008)+str(unname_group_index)
#            unname_group_index = unname_group_index + 1
#            if LANGUAGE == "cn":
#                try:
#                    if len(group.attrib['en']) > 0:
#                        group.attrib[LANGUAGE] = group.attrib['en']
#                        unname_group_index = unname_group_index - 1
#                except:
#                    pass
#        if name == group.attrib[LANGUAGE]:
        # order elements by name
            container = group.findall('.//channel')
            if (settings.getSetting('chan_list_order')=="true"):
                data = []
                for elem in container:
                    key = elem.findtext("name")
                    data.append((key, elem))
                data.sort()
                container[:] = [item[-1] for item in data]
            for channel in container:
                chan_id = channel.attrib['id']
                chan_name_info = channel.findtext('./name').strip()
                chan_name = channel.find('./name').attrib['en']
                if chan_name==None or chan_name=="":chan_name=chan_name_info
                chan_url = channel.findtext('./sop_address/item')
                chan_users = channel.findtext('.//user_count')
                chan_kbps = channel.findtext('.//kbps')
                chan_status = channel.findtext('.//status', default="2")
                chan_stream_type = channel.findtext('.//stream_type')
                sch_domain = channel.findtext('./schedule/sch_domain', default="")
                file_name = channel.findtext('./schedule/file_name', default="")
                sch_channel_id = channel.findtext('./schedule/sch_channel_id', default="")
                sch_list_expire = channel.findtext('./schedule/sch_list_expire', default="5")
                sch_timezone = channel.findtext('./schedule/sch_timezone', default="Europe/Bucharest")
                chan_thumb = channel.findtext('.//thumbnail', default="")
                if chan_thumb==None or chan_thumb=="": chan_thumb=channel.findtext('./description/thumbnail', default="")
                thumb_path=""
                if chan_thumb and chan_thumb != "":
                  try:
                    fileName, fileExtension = os.path.splitext(chan_thumb)
                    thumb_path=os.path.join(ADDON_PATH,"logos",file_name+fileExtension)
               
  #              xbmcgui.Dialog().ok(fileName,fileExtension,thumb_path,"")
                    if not os.path.isfile(thumb_path):
                        Downloader(chan_thumb,thumb_path,file_name+fileExtension,settings.getLocalizedString(30063))
                  except:pass
                sched={'title':'','full':''}
                if SHOW_KBPS=="true" and chan_kbps.strip() != "" and int(chan_kbps)>0: chan_name = "["+chan_kbps+"kbps] "+chan_name
                if SHOW_STREAM_TYPE=="true" and chan_stream_type.strip() != "":
                    if chan_stream_type == "mpeg-ts" or chan_stream_type == "mpeg-ps": chan_stream_type = "h264"
                    chan_name = "["+chan_stream_type+"] "+chan_name
                if SHOW_ID=="true": chan_name = chan_id+" "+chan_name
                if sch_channel_id !="":
                    sched = schedule(sch_domain , file_name , sch_channel_id , sch_list_expire , sch_timezone , False) 
                    chan_name=chan_name+sched['title']
                elif chan_name_info and chan_name_info != "" and chan_name_info.strip(" \n\r") != channel.find('./name').attrib['en'].strip(" \n\r"):
                    chan_name = chan_name+" ("+chan_name_info+")"

                chan_url = remove_line(chan_url)
                if chan_status=="2":
                    if mode1>99:
                        addLink(chan_name , chan_url , 200 , thumb_path , sched['full'])
                    elif mode1>9:
                        addLink(chan_name , chan_url , 20 , thumb_path , sched['full'])
                    else:
                        addLink(chan_name , chan_url , 2 , thumb_path , sched['full'])

            db_connection.close()
            if settings.getSetting('force_big_list')=="true" and CHAN_LIST != "http://www.sopcast.com/chlist.xml": xbmc.executebuiltin("Container.SetViewMode(51)")
 
def grab_schedule(sch_list_expire , channel_id , channel , silent):
    domain = ['port.hu','port.ro','port.cz','port.hu','kamo.hr','port.sk','port.rs'][ int(channel_id) / 10000 ]
    url="http://"+domain+"/pls/w/tv.channel?i_xday=13&i_ch="+channel_id;
    rtmp_gui_flag=False
    rtmp_gui=""
    #rtmp_gui = xbmcaddon.Addon(id=settings.getSetting('sch_rtmp_db')).getAddonInfo('path')
    if settings.getSetting('sch_rtmp_update')=="true":
        try:
       #     settings_rtmp = os.path.join(xbmc.translatePath("special://userdata"), 'autoexec.py')
            rtmp_gui = os.path.join(xbmc.translatePath("special://home"), "addons", settings.getSetting('sch_rtmp_db'), "resources", "SuperTV")
            conn_rtmp = sqlite3.connect(rtmp_gui)
            db_connection_rtmp=conn_rtmp.cursor()
            rtmp_gui_flag=True
        except:
            rtmp_gui_flag=False
            xbmcgui.Dialog().ok(settings.getLocalizedString(30069),settings.getLocalizedString(30070),settings.getSetting('sch_rtmp_db'),"")

    if domain=="port.ro":
        timezone="Europe/Bucharest"
        timezone_delta=-2
        month_name_to_no={"Ianuarie" : "01","Februarie" : "02","Martie" : "03","Aprilie" : "04","Mai" : "05","Iunie" : "06","Iulie" : "07","August" : "08","Septembrie" : "09","Octombrie" : "10","Noiembrie" : "11","Decembrie" : "12"}
    elif domain=="port.hu":
        timezone="Europe/Budapest"
        timezone_delta=-1
        month_name_to_no={"Január" : "01","Február" : "02","Március" : "03","Április" : "04","Május" : "05","Június" : "06","Július" : "07","Augusztus" : "08","Szeptember" : "09","Október" : "10","November" : "11","December" : "12"}
    elif domain=="port.sk":
        timezone="Europe/Bratislava"
        timezone_delta=-1
        month_name_to_no={"Január" : "01","Február" : "02","Marec" : "03","Apríl" : "04","Viac" : "05","Jún" : "06","Júl" : "07","August" : "08","Septembra" : "09","Október" : "10","November" : "11","December" : "12"}
    elif domain=="port.cz":
        timezone="Europe/Prague"
        timezone_delta=-1
        month_name_to_no={"Leden" : "01","Únor" : "02","Březen" : "03","Duben" : "04","Více" : "05","Červen" : "06","Červenec" : "07","Srpen" : "08","Září" : "09","Říjen" : "10","Listopad" : "11","Prosinec" : "12"}
    elif domain=="kamo.hr":
        timezone="Europe/Zagreb"
        timezone_delta=-1
        month_name_to_no={"Siječanj" : "01","Veljača" : "02","Ožujak" : "03","Travanj" : "04","Više" : "05","Lipanj" : "06","Srpanj" : "07","Kolovoz" : "08","Rujan" : "09","Listopad" : "10","Studeni" : "11","Prosinac" : "12"}
# verify port.rs month names
    elif domain=="port.rs":
        timezone="Europe/Belgrade"
        timezone_delta=-1
        month_name_to_no={"Januar" : "01","Februar" : "02","Mart" : "03","April" : "04","мај" : "05","Jun" : "06","Jul" : "07","Avgust" : "08","Septembar" : "09","Octobar" : "10","Novembar" : "11","Detembar" : "12"}
    else :
        timezone="Europe/Bucharest"
        timezone_delta=-2
        month_name_to_no={"Ianuarie" : "01","Februarie" : "02","Martie" : "03","Aprilie" : "04","Mai" : "05","Iunie" : "06","Iulie" : "07","August" : "08","Septembrie" : "09","Octombrie" : "10","Noiembrie" : "11","Decembrie" : "12"}
    

    if silent:
        if NOTIFY_GRABBING == "true": xbmc.executebuiltin("Notification(%s,%s,%i)" % (settings.getLocalizedString(30030), channel+".xml", 3))
        req = urllib2.Request(url)
        f = urllib2.urlopen(req)
        link = f.read()
        f.close()

    else:
        temp = os.path.join(ADDON_PATH,"temp.htm")
        Downloader(url,temp,channel+".xml",settings.getLocalizedString(30030))
        f = open(temp)
        link = f.read()
        f.close()
        os.remove(temp)
    g_r=re.compile(r'class="begin_time">(?P<time>.*?)</p>').search(link)
    if g_r:
        now_time=g_r.group('time')
    else:
        now_time=""
    now_duplicate=0
    xml_day = ["","","","","","","","","","","","",""]
    event_id=1
    column=0

    match_days=re.compile('<p class="date_box" style="margin-bottom:0px">\n                        <span>\n(?P<date>.*?)\n   </span><br/>(?P<content>.*?)<td style="vertical-align:top;text-align:center">',re.DOTALL).findall(link)
    if match_days:
#    nowDateTime = time.mktime(datetime.now(LocalTimezone).timetuple())
      if rtmp_gui_flag: db_connection_rtmp.execute("DELETE FROM epg WHERE chan = ?",(channel_id,))
      db_connection.execute("DELETE FROM epg WHERE channel_id = ?",(channel_id,))
      for date,content in match_days:
 #       xbmcgui.Dialog().ok("open1",date,"","")


        date_obj = re.match( '.*? \((.*) (.*)\)', date)
        event_day=date_obj.group(1).zfill(2)
        event_month=month_name_to_no[date_obj.group(2)]
        if time.strftime("%m")=="12" and event_month=="01":event_year=str(int(time.strftime("%Y"))+1)
        elif time.strftime("%m")=="01" and event_month=="12":event_year=str(int(time.strftime("%Y"))-1)
        else :event_year=time.strftime("%Y")

        match_events=re.compile('btxt\" style=\"width:40px;margin:0px;padding:0px\">(?P<event_time>.*?)<.*?btxt\">(?P<event_title>.*?)</(?P<event_details>.*?)</td></tr><tr style=',re.DOTALL).findall(content)
        if match_events:
          for event_time , event_title , event_details in match_events:

            try:mtxt=re.compile(r'<span class="mtxt"> (?P<mtxt>.*?)</span>').search(event_details).group('mtxt')
            except: mtxt=""
            try:ltxt=re.compile(r'<span class="ltxt"> (?P<ltxt>.*?) </span>').search(event_details).group('ltxt')
            except: ltxt=""
            try:desc_text=re.compile(r'<p class="desc_text">(?P<desc_text>.*?)</p>').search(event_details).group('desc_text')
            except: desc_text=""
            try:event_thumbnail=re.compile(r'<img class="object_picture" src="(?P<thumb>.*?)"').search(event_details).group('thumb')
            except: event_thumbnail=""

            subtitle=mtxt.replace("&", "") + ltxt.replace("&", "")
            if now_time==event_time:
                if now_duplicate==1: continue
                now_duplicate=1
            if event_time=="":
                if now_duplicate==1: continue
                elif now_time != "":
                    now_duplicate=1
                    event_time=now_time
                else: #error
                    if NOTIFY_GRABBING == "true":
                        xbmc.executebuiltin("Notification(%s,%s,%i)" % (settings.getLocalizedString(30045), channel+".xml", 3))
                    xml = '<?xml version="1.0" encoding="windows-1250"?>\n'
                    xml += '<content timezone="'+timezone+'" list_expire="'+sch_list_expire+'" date_created="'+time.strftime("%d-%m-%y %H:%M")+'">\n'
                    xml += '<timezone>'+timezone+'</timezone>\n'
                    xml += '<list_expire>1</list_expire>\n'
                    xml += '<date_created>'+time.strftime("%d-%m-%y %H:%M")+'</date_created>\n\n'
                    xml += '</content>'
                    xml_file = open(os.path.join(SCH_FOLDER_PATH,channel+".xml"),'w')
                    xml_file.write(xml)
                    xml_file.close()
                    db_connection.close()
                    return False
            event_hour=event_time.split(":")[0].zfill(2)
            event_minutes=event_time.split(":")[1]
            event_timestamp_remote = time.mktime(time.strptime(event_day+"-"+event_month+"-"+event_year+" "+event_hour+":"+event_minutes, "%d-%m-%Y %H:%M"))
            if int(event_hour)<4 : event_timestamp_remote += 60*60*24
            event_time_local = time.strftime("%d-%m-%y %H:%M", time.localtime(event_timestamp_remote))
            event_time_local_ = time.strftime("%Y-%m-%d %H:%M", time.localtime(event_timestamp_remote))

            if TIMEZONE_AUTO == "true":
                d = datetime(int(event_year), 4, 1)   # ends last Sunday in October
                dston = d - timedelta(days=d.weekday() + 1)
                d = datetime(int(event_year), 11, 1)
                dstoff = d - timedelta(days=d.weekday() + 1)
                event_date = datetime(int(event_year),int(event_month),int(event_day),int(event_hour),int(event_minutes))
                if dston <=  event_date < dstoff: event_timestamp_gmt = event_timestamp_remote+(timezone_delta-1)*60*60
                else: event_timestamp_gmt = event_timestamp_remote+timezone_delta*60*60
            else: event_timestamp_gmt = event_timestamp_remote+TIMEZONE_DELTA*60*60
            event_time_gmt = time.strftime("%d-%m-%y %H:%M", time.localtime(event_timestamp_gmt))
            event_time_gmt_ = time.strftime("%Y-%m-%d %H:%M", time.localtime(event_timestamp_gmt))
            event_timestamp_start = event_timestamp_gmt - (datetime.utcnow()-datetime.now()).total_seconds()
            event_timestamp_end = event_timestamp_start #need work here
                
#            db_connection.execute("INSERT INTO epg VALUES (?,?,?,?,?,?,?,?);", (channel_id, channel, event_time_local_, event_time_gmt_, event_title.replace("&", ""), subtitle.replace(")(", " - "), desc_text.replace("&", ""), ""))
            sql="INSERT INTO epg VALUES (NULL,"+str(event_id)+","+channel_id+",'"+channel+"','"+event_time_local_+"','"+event_time_gmt_+"','"+unicode(event_title.replace("'", ""), 'windows-1250')+"','"+unicode(subtitle.replace("'", ""), 'windows-1250')+"','"+unicode(desc_text.replace("'", ""), 'windows-1250')+"', '"+event_thumbnail+"');"
#            xbmc.executebuiltin("Notification(%s,%s,%i)" % (sql, sql, 50000))
#            xbmcgui.Dialog().ok(sql,sql,event_title.replace("&'", ""),subtitle.replace(")('", " - "))
            db_connection.execute(sql)
            if rtmp_gui_flag:
                sql="INSERT INTO epg VALUES ('"+unicode(event_title.replace("'", ""), 'windows-1250')+"', "+str(event_timestamp_start)+", "+str(event_timestamp_end)+", '"+unicode(subtitle.replace("'", ""), 'windows-1250')+' '+unicode(desc_text.replace("'", ""), 'windows-1250')+"', '"+event_thumbnail+"', '"+channel_id+"', 'PortHUEPG');"
                db_connection_rtmp.execute(sql)

            xml_day[column] += '<event id="'+str(event_id)+'">'
#            xml_day[column] += '\n\t<time>'+event_time+'</time>'
#            xml_day[column] += '\n\t<day></day>'
            xml_day[column] += '\n\t<fulltime>'+event_time_local+'</fulltime>'
            xml_day[column] += '\n\t<gmttime>'+event_time_gmt+'</gmttime>'
            xml_day[column] += '\n\t<title>'+event_title.replace("&", "") + '</title>'
            xml_day[column] += '\n\t<subtitle>' + subtitle.replace(")(", " - ") + '</subtitle>'
            xml_day[column] += '\n\t<cast>' + desc_text.replace("&", "") + '</cast>'
            xml_day[column] += '\n</event>\n'
            event_id +=1
        
        if column < 12: column += 1
        else: column = 0
        
      if rtmp_gui_flag:
        conn_rtmp.commit()
        db_connection_rtmp.close()
      conn.commit()
      xml = '<?xml version="1.0" encoding="windows-1250"?>\n'
      xml += '<content timezone="'+timezone+'" list_expire="'+sch_list_expire+'" date_created="'+time.strftime("%d-%m-%y %H:%M")+'">\n'
      xml += '<timezone>'+timezone+'</timezone>\n'
      xml += '<list_expire>'+sch_list_expire+'</list_expire>\n'
      xml += '<date_created>'+time.strftime("%d-%m-%y %H:%M")+'</date_created>\n\n'
      xml += xml_day[0] + xml_day[1] + xml_day[2] + xml_day[3] + xml_day[4] + xml_day[5] + xml_day[6] + xml_day[7] + xml_day[8] + xml_day[9] + xml_day[10] + xml_day[11] + xml_day[12]
      xml += '</content>'
      xml_file = open(os.path.join(SCH_FOLDER_PATH,channel+".xml"),'w')
      xml_file.write(xml)
      xml_file.close()
    else:
            if NOTIFY_GRABBING == "true": xbmc.executebuiltin("Notification(%s,%s,%i)" % (settings.getLocalizedString(30045), channel+".xml", 3))
            xml = '<?xml version="1.0" encoding="windows-1250"?>\n'
            xml += '<content timezone="'+timezone+'" list_expire="'+sch_list_expire+'" date_created="'+time.strftime("%d-%m-%y %H:%M")+'">\n'
            xml += '<timezone>'+timezone+'</timezone>\n'
            xml += '<list_expire>1</list_expire>\n'
            xml += '<date_created>'+time.strftime("%d-%m-%y %H:%M")+'</date_created>\n\n'
            xml += '</content>'
            xml_file = open(os.path.join(SCH_FOLDER_PATH,channel+".xml"),'w')
            xml_file.write(xml)
            xml_file.close()
            return False

    return True
now_event_title=""
now_event_subtitle=""
now_event_cast=""

def schedule( sch_domain , file_name , sch_channel_id , sch_list_expire , sch_timezone , silent):
#we need to verify if the local list is old

    sched= {'grabbed':False , 'title':'' , 'full':'' , 'error':'','event_id':[],'event_title':[],'event_subtitle':[],'event_cast':[],'event_time':[]}
    db_connection.execute("SELECT event_id, event_time_local, event_time_gmt, title, subtitle, description from epg WHERE channel_id="+sch_channel_id+" ORDER BY event_time_gmt")
#    db_connection.execute("SELECT * from epg WHERE channel_id="+sch_channel_id+" and Datetime(event_time_gmt)>Datetime('"+datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")+"') ORDER BY event_time_gmt LIMIT 1")
 #   return sched
    events=db_connection.fetchall()
#    xbmcgui.Dialog().ok(str(1), sch_list_expire, str(events[0][5]), "")
    if len(events)<1 and (SCH_GRAB_BEFORE_LIST=="true" or silent==True): # if the schedule list does not exist we will grab it from internet
        grab_schedule(sch_list_expire , sch_channel_id , file_name , silent)
        sched['grabbed']=True
        db_connection.execute("SELECT event_id, event_time_local, event_time_gmt, title, subtitle, description from epg WHERE channel_id="+sch_channel_id+" ORDER BY event_time_gmt")
        events=db_connection.fetchall()

    # if the schedule list contains no data we will grab it from internet
    elif len(events)<1 and (SCH_GRAB_BEFORE_LIST=="false" and silent==False): 
#        xbmcgui.Dialog().ok(str(1), sch_list_expire, str(events[0][5]), "")
        return sched
#    now_time = time.mktime(datetime.now().timetuple())
#    now_time = time.mktime(datetime.utcnow().timetuple())

    next_event_count=1
    try:

 #       list_date_delta = time.mktime(datetime.utcnow().timetuple()) - time.mktime(time.strptime(events[0][5], "%Y-%m-%d %H:%M"))

        try:formated_date=datetime.strptime(events[0][2], "%Y-%m-%d %H:%M")
        except:formated_date = datetime.fromtimestamp(time.mktime(time.strptime(events[0][2], "%Y-%m-%d %H:%M")))
# check if file version is old
        if ((datetime.utcnow() - formated_date).total_seconds() >= int(sch_list_expire)*60*60*24):
#        if time.mktime(datetime.utcnow().timetuple()) - time.mktime(time.strptime(events[0][2], "%Y-%m-%d %H:%M")) >= int(sch_list_expire)*60*60*24:
 #           xbmcgui.Dialog().ok(str(1), sch_list_expire, events[0][5], "")
            grab_schedule(sch_list_expire , sch_channel_id , file_name , silent)
            sched['grabbed']=True
            db_connection.execute("SELECT event_id, event_time_local, event_time_gmt, title, subtitle, description from epg WHERE channel_id="+sch_channel_id+" ORDER BY event_time_gmt")
            events=db_connection.fetchall()
#        xbmcgui.Dialog().ok(str((datetime.utcnow() - formated_date).seconds), str(formated_date), events[0][5], "")
        start_time=0
        event_count=0
        now_event = {'id':'0' , 'title':'Unknown event' , 'subtitle':'' , 'cast':''}

        for event_id, event_time_remote, event_time_gmt, event_title, event_subtitle, event_cast in events:

 #           xbmcgui.Dialog().ok(str(event_id),event_time_gmt,event_title,event_subtitle)
 
            if (TIMEZONE_AUTO=="false"): eventtime = time.mktime( time.strptime(event_time_remote, "%Y-%m-%d %H:%M") ) - 60*60*TIMEZONE_DELTA
            else: eventtime = time.mktime( time.strptime(event_time_gmt, "%Y-%m-%d %H:%M") ) - (datetime.utcnow()-datetime.now()).total_seconds()
    
            sched['event_id'].append(event_id)
            sched['event_title'].append(event_title)
            sched['event_subtitle'].append(event_subtitle)
            sched['event_cast'].append(event_cast)
            sched['event_time'].append(eventtime)
            event_count+=1
            nowtime = time.mktime( time.localtime())
#if now time equal with event return current event and next event
            if nowtime <= eventtime + 60: # add 60 seconds because of the p2p delay
                if next_event_count == 1:
                    sched['now_id'] = now_event['id']
                    sched['now_title'] = now_event['title']
                    sched['now_subtitle'] = now_event['subtitle']
                    sched['now_cast'] = now_event['cast']
                    sched['title'] = " - "+now_event['title']
                    if settings.getSetting('sch_show_details')=="true": sched['title'] += " "+now_event['subtitle']
                    sched['full'] = " - NOW - "+now_event['title']+" "+now_event['subtitle']+" - "+now_event['cast']+"\n"
                if settings.getSetting('sch_hour_format')=="true": formated_time=time.strftime("%H:%M", time.localtime(eventtime))
                else :
                    if settings.getSetting('sch_hour_ampm')=="true": formated_time=time.strftime("%I:%M%p", time.localtime(eventtime))
                    else: formated_time=time.strftime("%I:%M", time.localtime(eventtime))
                if next_event_count < SCHEDULE_EVENTS: 
                    sched['title'] += " - "+formated_time+" "+event_title
                    if settings.getSetting('sch_show_details')=="true": sched['title'] += " "+now_event['subtitle']
                sched['full'] += time.strftime("%A", time.localtime(eventtime))+" "+formated_time+" - "+event_title+" "+event_subtitle+" - "+event_cast+"\n"
                next_event_count += 1
            now_event['id']=event_id
            now_event['title']=event_title
            now_event['subtitle']=event_subtitle
            now_event['cast']=event_cast



    except: pass
    return sched
    
def schedule_old( sch_domain , file_name , sch_channel_id , sch_list_expire , sch_timezone , silent):
#we need to verify if the local list is old
    sched= {'grabbed':False , 'title':'' , 'full':'' , 'error':'','event_id':[],'event_title':[],'event_subtitle':[],'event_cast':[],'event_time':[]}
    result = os.path.join(ADDON_PATH,"schedule",file_name+".xml")
    if not os.path.isfile(result) and (SCH_GRAB_BEFORE_LIST=="true" or silent==True): # if the schedule list does not exist we will grab it from internet
        grab_schedule(sch_list_expire , sch_channel_id , file_name , silent)
        sched['grabbed']=True
    # if the schedule list contains no data we will grab it from internet
    elif (SCH_GRAB_BEFORE_LIST=="true" or silent==True): 
        for length in str(os.stat(result)[6]).split('L'):
            if length == "0":
                grab_schedule(sch_list_expire , sch_channel_id , file_name , silent)
                sched['grabbed']=True
    else:
        return sched
    now_time = time.mktime(datetime.now().timetuple())


    next_event_count=1
    try:
        response = ElementTree.parse(result)
        list_date_created = time.mktime(time.strptime(response.findtext('.//date_created'), "%d-%m-%y %H:%M"))
# check if file version is old
        if now_time - list_date_created >= int(sch_list_expire)*60*60*24:
            grab_schedule(sch_list_expire , sch_channel_id , file_name , silent)
            sched['grabbed']=True
            response = ElementTree.parse(result)

        events = response.findall('.//event')
        start_time=0
        event_count=0
        now_event = {'id':'0' , 'title':'Unknown event' , 'subtitle':'' , 'cast':''}
        for event in events:
            event_id=event.attrib.get('id')
            event_time_remote = event.findtext('.//fulltime',"")
            event_time_gmt = event.findtext('.//gmttime',"")
            event_title = event.findtext('.//title',"")
            event_subtitle = event.findtext('.//subtitle',"")
            event_cast = event.findtext('.//cast',"")

            if (TIMEZONE_AUTO=="false"): eventtime = time.mktime( time.strptime(event_time_remote, "%d-%m-%y %H:%M") ) - 60*60*TIMEZONE_DELTA
            else: eventtime = time.mktime( time.strptime(event_time_gmt, "%d-%m-%y %H:%M") ) - (datetime.utcnow()-datetime.now()).total_seconds()
     
            sched['event_id'].append(event_id)
            sched['event_title'].append(event_title)
            sched['event_subtitle'].append(event_subtitle)
            sched['event_cast'].append(event_cast)
            sched['event_time'].append(eventtime)
            event_count+=1
            nowtime = time.mktime( time.localtime())
#if now time equal with event return current event and next event
            if nowtime <= eventtime + 60: # add 60 seconds because of the p2p delay
                if next_event_count == 1:
                    sched['now_id'] = now_event['id']
                    sched['now_title'] = now_event['title']
                    sched['now_subtitle'] = now_event['subtitle']
                    sched['now_cast'] = now_event['cast']
                    sched['title'] = " - "+now_event['title']
                    if settings.getSetting('sch_show_details')=="true": sched['title'] += " "+now_event['subtitle']
                    sched['full'] = " - NOW - "+now_event['title']+" "+now_event['subtitle']+" - "+now_event['cast']+"\n"
                if settings.getSetting('sch_hour_format')=="true": formated_time=time.strftime("%H:%M", time.localtime(eventtime))
                else :
                    if settings.getSetting('sch_hour_ampm')=="true": formated_time=time.strftime("%I:%M%p", time.localtime(eventtime))
                    else: formated_time=time.strftime("%I:%M", time.localtime(eventtime))
                if next_event_count < SCHEDULE_EVENTS: 
                    sched['title'] += " - "+formated_time+" "+event_title
                    if settings.getSetting('sch_show_details')=="true": sched['title'] += " "+now_event['subtitle']
                sched['full'] += time.strftime("%A", time.localtime(eventtime))+" "+formated_time+" - "+event_title+" "+event_subtitle+" - "+event_cast+"\n"
                next_event_count += 1
            now_event['id']=event_id
            now_event['title']=event_title
            now_event['subtitle']=event_subtitle
            now_event['cast']=event_cast



    except:
######## if we cannot parse the schedule list, we will inform the end user
        sched['error']=" error parsing "+file_name+".xml"
# if file has errors and it is more than 1 hour old grab new file
        time_created = os.stat(result)[8]  # get local sched list modified date
        if now_time - time_created > 3600:
            grab_schedule(sch_list_expire , sch_channel_id , file_name , silent)
            sched['grabbed']=True
    return sched

    
    
# this function will sleep only if the sop is running
def sop_sleep(time , spsc_pid):
    counter=0
    increment=200
    path="/proc/%s" % str(spsc_pid)
#    xbmc.sleep(3000)
#    xbmcgui.Dialog().ok(path,str(spsc_pid),"1","")
 #   xbmcgui.Dialog().ok("","","1","")
    try:
      while counter < time and spsc_pid>0 and not xbmc.abortRequested and os.path.exists(path):
 #       xbmcgui.Dialog().ok(path,str(spsc_piid),"2","")
        counter += increment
        xbmc.sleep(increment)
    except: return True
#    ValueError as a: 
  #      xbmcgui.Dialog().ok(a,a,a,a)
        
    if counter < time: return False
    else: return True

def WATCH_SOP_THREAD(spsc_pid,listitem,sop):
    xbmc.sleep(100)
    sop_sleep(4000 , spsc_pid)
    while os.path.exists("/proc/"+str(spsc_pid)) and not xbmc.abortRequested:
# close the epg window if other window is active
        if not xbmc.getCondVisibility("Window.IsActive(12005)"):
            try:
                if xbmc.getCondVisibility("Window.IsActive(epg.xml)"):
                    xbmc.executebuiltin("Action(Select)") 
                    xbmc.executebuiltin("Action(Close)")
            except:
                pass
# check if player stoped and restart it
        if not xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying():
            
#            xbmc.sleep(1000)
            if not sop_sleep(1000 , spsc_pid): break
            if not xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying():
                url = "http://"+LOCAL_IP+":"+str(VIDEO_PORT)+"/"
                player = streamplayer(xbmc.PLAYER_CORE_AUTO , spsc_pid=spsc_pid , listitem=listitem)
                player.play(url,listitem)

            sop_sleep(2000 , spsc_pid)
#            xbmc.sleep(2000)
 #       checkwindow()
        #if xbmc.Player(xbmc.PLAYER_CORE_AUTO).getTime()>10:
        #        xbmcgui.Dialog().ok("onplaybackended",sop,"","")
        #        autostart(sop)
        sop_sleep(300 , spsc_pid)
#        xbmc.sleep(500)
    try:
#  this will close the epg window on exit
        if xbmc.getCondVisibility("Window.IsActive(epg.xml)"):
            xbmc.executebuiltin("Action(Select)") 
            xbmc.executebuiltin("Action(Close)")
    except:
        pass
        
def get_epg(file_name):
    global conn
    global db_connection
    response = ElementTree.parse(os.path.join(ADDON_PATH,"channel_guide.xml"))
    for channel in response.findall( './/channel' ):
        if file_name == channel.findtext('./schedule/file_name', default=""):
            sch_domain = channel.findtext('./schedule/sch_domain', default="")
            sch_channel_id = channel.findtext('./schedule/sch_channel_id', default="")
            sch_list_expire = channel.findtext('./schedule/sch_list_expire', default="")
            sch_timezone = channel.findtext('./schedule/sch_timezone', default="")
            if SCH_OVER_EXPIRED == "true": sch_list_expire = SCH_NEW_EXPIRED

            conn = sqlite3.connect(EPGPATH)

            db_connection=conn.cursor()
            sched = schedule(sch_domain , file_name , sch_channel_id , sch_list_expire , sch_timezone, True)
            db_connection.close()
            return sched

    return False

def GRAB_SCH_THREAD (spsc_pid,listitem,dummy):
    global conn
    global db_connection
 #   if not sop_sleep(60000 , spsc_pid): return
    from urlparse import urljoin
# refetch the channel guide and check all schedules. if old, grab a new one and wait 10s
    while os.path.exists("/proc/"+str(spsc_pid)) and not xbmc.abortRequested:
        if xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying(): # grab new schedule
 #           xbmcgui.Dialog().ok(listitem.getProperty('VideoCodec'),xbmc.Player(xbmc.PLAYER_CORE_AUTO).getVideoInfoTag().getFile(),listitem.getLabel(),xbmc.getInfoLabel('VideoPlayer.VideoCodec'))
  #          req = urllib2.Request(urljoin(settings.getSetting('chan_list_url'),"update.php")+"?VideoCodec="+xbmc.getInfoLabel('VideoPlayer.VideoCodec')+"&VideoAspect="+xbmc.getInfoLabel('VideoPlayer.VideoAspect')+"&VideoResolution="+xbmc.getInfoLabel('VideoPlayer.VideoResolution')+"&AudioCodec="+xbmc.getInfoLabel('VideoPlayer.AudioCodec')+"&AudioChannels="+xbmc.getInfoLabel('VideoPlayer.AudioChannels'))
  #          urllib2.urlopen(req)
            if not sop_sleep(10000 , spsc_pid): return

#            if LOG_SOPCAST == "true" and int(str(os.stat(os.path.join(ADDON_PATH,"sopcast.log"))[6]).split('L')[0])>100000:
#                logfile=open(SPSC_LOG,"w")
#                logfile.close
 
            response = ElementTree.parse(os.path.join(ADDON_PATH,"channel_guide.xml"))
            groups = response.findall('.//group')
            unname_group_index = 1
            sched = {'grabbed':False,'title':''}
            try:  
              for group in groups:
      #          xbmc.sleep(50)
                if group.attrib[LANGUAGE] == "":
                    group.attrib[LANGUAGE] = settings.getLocalizedString(30008)+str(unname_group_index)
                    unname_group_index = unname_group_index + 1
                    if LANGUAGE == "cn":
                        try:
                            if len(group.attrib['en']) > 0:
                                group.attrib[LANGUAGE] = group.attrib['en']
                                unname_group_index = unname_group_index - 1
                        except:
                            pass
#        if name == group.attrib[LANGUAGE]:
                for channel in group.findall('.//channel'):
#                   chan_id = channel.attrib['id']
                    chan_name = channel.findtext('./name', default="").strip()
                    chan_url = channel.findtext('./sop_address/item', default="")
#                   chan_users = channel.findtext('.//user_count', default="")
                    sch_domain = channel.findtext('./schedule/sch_domain', default="")
                    file_name = channel.findtext('./schedule/file_name', default="")
                    sch_channel_id = channel.findtext('./schedule/sch_channel_id', default="")
                    sch_list_expire = channel.findtext('./schedule/sch_list_expire', default="")
                    sch_timezone = channel.findtext('./schedule/sch_timezone', default="")
#                    chan_description = channel.findtext('./description/thumbnail', default="")
#                   plot = ""

                    if SCH_OVER_EXPIRED == "true": sch_list_expire = SCH_NEW_EXPIRED
                    if(sch_domain != "" and file_name != "" and sch_domain != "" and sch_channel_id != "" and sch_list_expire != "" and sch_timezone != ""):
              #          xbmc.sleep(10)

                        conn = sqlite3.connect(EPGPATH)

                        db_connection=conn.cursor()
                        sched = schedule(sch_domain , file_name , sch_channel_id , sch_list_expire , sch_timezone, True)
  #                      xbmc.executebuiltin("Notification(%s,%s,%i)" % (sch_channel_id, file_name, 5))

                        db_connection.close()
 #                       plot = sched['full']
                    if sched['grabbed'] == True: break
                if sched['grabbed'] == True: break
# new event started we need to update the title and inform user 
            except:pass
        #        xbmc.executebuiltin("Notification(%s,%s,%i)" % (str(sch_channel_id), "90", 5))
       #     xbmc.executebuiltin("Notification(%s,%s,%i)" % ("onPlayBackStopped", "9", 5))

        if not sop_sleep(10000 , spsc_pid): return
def EVENT_SCH_THREAD (spsc_pid , file_name , chan_name):
    sched = get_epg(file_name)
    now_event = {'event_id':sched['now_id'] , 'event_title':sched['now_title'] , 'event_subtitle':sched['now_subtitle'] , 'event_cast':sched['now_cast']}
    if not sop_sleep(2000 , spsc_pid): return
    total_events=len(sched['event_title'])
    now_event_id=sched['now_id']
    now_event_id=0
    while os.path.exists("/proc/"+str(spsc_pid)) and not xbmc.abortRequested:
      nowtime = time.mktime( time.localtime())
      try:
        if xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying() and xbmc.Player(xbmc.PLAYER_CORE_AUTO).getTime()>1:
            for count in range(total_events):
                if nowtime > sched['event_time'][count]:
                    now_event['event_id']=int(sched['event_id'][count])
                    now_event['event_title']=sched['event_title'][count]
                    now_event['event_subtitle']=sched['event_subtitle'][count]
                    now_event['event_cast']=sched['event_cast'][count]
            if now_event['event_id'] != now_event_id:

                now_event_id=now_event['event_id']
                epg_window(file_name,chan_name)
                if not sop_sleep(2000 , spsc_pid): return
                                #this will close the EPG window so it will refresh with the new epg_window
               #                 xbmc.executebuiltin("Dialog.Close(3003,true)")
            #                    xbmc.executebuiltin("Dialog.Close(all,true)")
               #                 xbmc.executebuiltin("Dialog.Close(epg.xml,true)")
              #                  xbmcgui.Dialog().ok("onplaybackended",str(xbmcgui.getCurrentWindowId()),"","")

                if xbmc.getCondVisibility("Window.IsActive(epg.xml)"):
                    xbmc.executebuiltin("Action(Select)")
                    xbmc.executebuiltin("Action(Close)")
                if not sop_sleep(2000 , spsc_pid): return
                notify_subtitle = ""
                if now_event['event_subtitle'] != "": notify_subtitle += now_event['event_subtitle'] + " "
                if now_event['event_cast'] != "": notify_subtitle += now_event['event_cast'] + " "
                xbmc.executebuiltin("Notification(%s,%s,%i)" % (now_event['event_title'], notify_subtitle, 10000))
            if not sop_sleep(60000 , spsc_pid): return
      except:pass

def checkwindow():
    count=1000
    while count<12909:
        count+=1
        if count==3100:count=10000
        if count==10041:count=10100
        if count==10151:count=10500
        if count==10504:count=12000
        if count==12010:count=12900
        if xbmc.getCondVisibility("Window.IsVisible(%s)" % (str(count))):
            xbmc.executebuiltin("Notification(%s,%s,%i)" % ("Window- visible", str(count), 2))
            xbmc.sleep(1000)
        if xbmc.getCondVisibility("Window.IsActive(%s)" % (str(count))):
            xbmc.executebuiltin("Notification(%s,%s,%i)" % ("Window- active", str(count), 2))
            xbmc.sleep(1000)
    xbmc.executebuiltin("Notification(%s,%s,%i)" % ("Window- current", str(xbmcgui.getCurrentWindowId()), 2))
    xbmc.sleep(1000)

        
def WATCH_ACTIONS (spsc_pid):

 #   xbmc.executebuiltin( "ActivateWindow(busydialog)" )
 #   xbmc.sleep(5000)
    mydisplay = EPG("epg.xml",ADDON_PATH,spsc_pid=spsc_pid)
    mydisplay.doModal()
    del mydisplay

    time_c=0
    while os.path.exists("/proc/"+str(spsc_pid)) and not xbmc.abortRequested:
  #      if time_c==0: checkwindow()
        if xbmcgui.getCurrentWindowId() == WINDOW_FULLSCREEN_VIDEO and not xbmc.getCondVisibility("Window.IsVisible(12901)") :
            if time_c>10:
                
                time_c=0
                
                mydisplay = EPG("epg.xml",ADDON_PATH,spsc_pid=spsc_pid)
                mydisplay.doModal()
                del mydisplay
            else:time_c+=1

 #       elif not xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying():
 #               try:
 #                   os.kill(spsc_pid,9)
 #               except:pass
        else: time_c=0
        xbmc.sleep(500)
def updatestation():
#check if channel is in local guide
    
#    groups = []
    channel = {'name':'' , 'name_en':'' , 'name_cn':'' , 'ch_language':'' , 'ch_type':'0' , 'ch_btype':'0' ,
            'status':'2' , 'region':'' , 'region_en':'' , 'region_cn':'' , 'class':'' , 'class_en':'' , 'class_cn':'' , 'user_count':'1' ,
            'sn':'' , 'visit_count':'1' , 'start_from':'' , 'stream_type':'' , 'kbps':'' , 'qs':'90' , 'qc':'90' ,
            'sch_domain':'' , 'file_name':'' , 'sch_channel_id':'' , 'sch_list_expire':'' , 'sch_timezone':'' ,
            'description':'' , 'description_cn':'' , 'thumbnail':'' , 'sop_address':sop}
    
    tvstations = ElementTree.parse(os.path.join(ADDON_PATH,"data.xml")).findall('.//channel')
    tvstations_list = []
    for elem in tvstations:
        key = elem.findtext("name", default="")
        tvstations_list.append((key, elem))
    tvstations_list.sort()
    tvstations[:] = [item[-1] for item in tvstations_list]
    tvstations_list = ['CUSTOM CHANNEL']
    for elem in tvstations:
        tvstations_list.append(elem.findtext('./name', default="").strip()+" ["+elem.findtext('./region', default="").strip()+"]")
    sop_port = urlparse(sop).path.strip("/")

    chlist_tree = ElementTree.parse(os.path.join(ADDON_PATH,"channel_guide.xml"))
    try:
        chlist_l = chlist_tree.find(".//channel/.[@id='"+sop_port+"']")
        if chlist_l:
            channel['user_count'] = chlist_l.find('.//user_count', default="").text
            channel['sn'] = chlist_l.find('.//sn', default="").text
            channel['visi_count'] = chlist_l.find('.//visi_count', default="").text
            channel['start_from'] = chlist_l.find('.//start_from', default="").text
            channel['stream_type'] = chlist_l.find('.//stream_type', default="").text
            channel['kbps'] = chlist_l.find('.//kbps', default="").text
            channel['qs'] = chlist_l.find('.//qs', default="").text
            channel['qc'] = chlist_l.find('.//qc', default="").text
            channel['description'] = chlist_l.find('.//description', default="").text
    except: pass
    try:
        chlist_s = ElementTree.parse(os.path.join(ADDON_PATH,"chlist.xml")).find(".//channel/.[@id='"+sop_port+"']")
        if chlist_s:
            channel['ch_language'] = chlist_s.attrib['language']
            channel['ch_type'] = chlist_s.attrib['type']
            channel['ch_btype'] = chlist_s.attrib['btype']
            channel['name_en'] = chlist_s.find('.//name').attrib['en']
            channel['name_cn'] = chlist_s.find('.//name').attrib['cn']
            if (channel['region']==''):
                channel['region'] = chlist_s.findtext('.//region', default="")
                channel['region_en'] = chlist_s.find('.//region').attrib['en'].strip()
                channel['region_cn'] = chlist_s.find('.//region').attrib['cn']
            channel['user_count'] = chlist_s.findtext('.//user_count', default="")
            channel['sn'] = chlist_s.findtext('.//sn', default="")
            channel['visi_count'] = chlist_s.findtext('.//visi_count', default="")
            channel['start_from'] = chlist_s.findtext('.//start_from', default="")
            channel['stream_type'] = chlist_s.findtext('.//stream_type', default="")
            channel['kbps'] = chlist_s.findtext('.//kbps', default="")
            channel['qs'] = chlist_s.findtext('.//qs', default="")
            channel['qc'] = chlist_s.findtext('.//qc', default="")
            if (channel['description']==''): channel['description'] = chlist_s.findtext('.//description', default="")
            channel['description_cn'] = chlist_s.find('.//description').attrib['cn']
# xbmc.executebuiltin("Notification(%s,%s,%i)" % (channel['kbps'], chlist_s.findtext('.//kbps', default=""), 1))
    except: pass
    try:
        chlist_r = ElementTree.parse(os.path.join(ADDON_PATH,"remote_chlist.xml")).find(".//channel/.[@id='"+sop_port+"']")
        if chlist_r:
            if (channel['kbps']==''): channel['kbps'] = chlist_r.findtext('.//kbps', default="")
            if (channel['description']==''): channel['description'] = chlist_r.findtext('.//description', default="")
    except: pass
    
    sel_item = xbmcgui.Dialog().select('Select the tv station', tvstations_list)
    if (sel_item==-1): return
    if (sel_item==0):
        kb=xbmc.Keyboard(channel['name_en'],'Channel name')
        kb.doModal()
        if (kb.isConfirmed()):
            channel['name_en'] = kb.getText()
            if channel['name'] == "" or channel['name'] == None: channel['name'] = channel['name_en']
        classes = ElementTree.parse(os.path.join(ADDON_PATH,"data.xml")).findall('./classes/class')
        classes_list=[]
        for elem in classes:
            classes_list.append(elem.findtext(".//name_en", default=""))

 #       classes_list = {1:'Entertainmnet',2:'Sports',3:'General',6:'News',7:'Finance &amp; Economics',8:'Education',9:'Movies',10:'Cartoon',11:'Music',12:'Comic',13:'Documentary',14:'TV play series',99:'Others']
        sel_item = xbmcgui.Dialog().select('Select the tv class', classes_list)
        if (sel_item==-1): return
        channel['class'] = classes[sel_item].findtext(".//id", default="")
        channel['class_en'] = classes_list[sel_item]
        channel['class_cn'] = classes[sel_item].findtext(".//name_cn", default="")
        
        
      
    else:
        tvstation=tvstations[sel_item-1]
        channel['name']=tvstation.findtext('./name', default="").strip()
        channel['ch_language']=tvstation.attrib['language'].strip()
        channel['name_en']=channel['name']
        channel['region']=tvstation.findtext('./region', default="").strip()
        channel['region_en']=tvstation.find('./region').attrib['en'].strip()
        channel['region_cn']=tvstation.find('./region').attrib['cn'].strip()
        channel['class']=tvstation.findtext('./class', default="").strip()
        channel['class_en']=tvstation.find('./class').attrib['en'].strip()
        channel['class_cn']=tvstation.find('./class').attrib['cn'].strip()
        channel['sch_domain']=tvstation.findtext('./sch_domain', default="").strip()
        channel['file_name']=tvstation.findtext('./file_name', default="").strip()
        channel['sch_channel_id']=tvstation.findtext('./sch_channel_id', default="").strip()
        channel['sch_list_expire']=tvstation.findtext('./sch_list_expire', default="").strip()
        channel['sch_timezone']=tvstation.findtext('./sch_timezone', default="").strip()
        channel['description']=tvstation.findtext('./description', default="").strip()
        channel['thumbnail']=tvstation.findtext('./thumbnail', default="").strip()

   # xbmcgui.Dialog().ok(xbmc.getInfoLabel('VideoPlayer.VideoCodec'),channel['stream_type'],"","")

    if (channel['start_from'] == '' or channel['start_from'] == None): channel['start_from']=datetime.utcnow().strftime("%a %d %b %Y %H:%M:%S GMT")
    if (channel['stream_type'] == '' or channel['stream_type'] == None):
        stream_type=xbmc.getInfoLabel('VideoPlayer.VideoCodec')
        if (stream_type == 'h264'): channel['stream_type'] = 'mpeg-ts'
        elif (stream_type == 'wmva' or stream_type == 'wvc1' or stream_type == 'wmv1' or stream_type == 'wmv2' or stream_type == 'wmv3'): channel['stream_type'] = 'wmv'
  #  xbmcgui.Dialog().ok(xbmc.getInfoLabel('VideoPlayer.VideoCodec'),channel['stream_type'],"","")

 #   group_sel = xbmcgui.Dialog().select('Move to group (ESC to skip):', groups)
 #   if (group_sel == -1 and chlist_l == None): return
    if (settings.getSetting('chan_list_edit')=='true'):
        if (channel['kbps']==None or channel['kbps']==''): channel['kbps'] = xbmcgui.Dialog().numeric(0, 'Enter stream bitrate [kbps]','')
        kb=xbmc.Keyboard(channel['description'],'Description')
        kb.doModal()
        if (kb.isConfirmed()): channel['description'] = kb.getText()
    save = xbmcgui.Dialog().yesno("Confirm modifications", 'Channel name: '+channel['name'],'Description: '+str(channel['description']))
    
    if (save):
        updated=False
        if chlist_l:
          if (channel['class_en'] == chlist_l.find('.//class').attrib['en'].strip()):
            chlist_l.attrib['language']=channel['ch_language']
            chlist_l.find('.//name').text = channel['name']
            chlist_l.find('.//name').attrib['en'] = channel['name_en']
            chlist_l.find('.//name').attrib['cn'] = channel['name_cn']
            chlist_l.find('.//class').text = channel['class']
            chlist_l.find('.//class').attrib['en'] = channel['class_en']
            chlist_l.find('.//class').attrib['cn'] = channel['class_cn']
            chlist_l.find('.//region').text = channel['region']
            chlist_l.find('.//stream_type').text = channel['stream_type']
            chlist_l.find('.//region').attrib['en'] = channel['region_en']
            chlist_l.find('.//region').attrib['cn'] = channel['region_cn']
            chlist_l.find('./schedule/sch_domain').text = channel['sch_domain']
            chlist_l.find('./schedule/file_name').text = channel['file_name']
            chlist_l.find('./schedule/sch_channel_id').text = channel['sch_channel_id']
            chlist_l.find('./schedule/sch_list_expire').text = channel['sch_list_expire']
            chlist_l.find('./schedule/sch_timezone').text = channel['sch_timezone']
            chlist_l.find('.//thumbnail').text = channel['thumbnail']
            if channel['kbps'] and channel['kbps'] != "": chlist_l.find('.//kbps').text = channel['kbps']
            updated=True
          else:
            group_root = chlist_tree.find(".//group/.[@en='"+chlist_l.find('.//class').attrib['en']+"']")
            group_root.remove(chlist_l)
        if (updated == False):
            el_group = chlist_tree.find(".//group/.[@en='"+channel['class_en']+"']")
            el_channel = ElementTree.SubElement(el_group,"channel",attrib={ 'type':channel['ch_type'], 'btype':channel['ch_btype'], 'language':channel['ch_language'], 'id':sop_port})
            ElementTree.SubElement(el_channel,"name",attrib={ 'en':channel['name_en'], 'cn':channel['name_cn']}).text=channel['name']
            ElementTree.SubElement(el_channel,"status").text=channel['status']
            ElementTree.SubElement(el_channel,"region", attrib={ 'en':channel['region_en'], 'cn':channel['region_cn']}).text=channel['region']
            ElementTree.SubElement(el_channel,"class", attrib={ 'en':channel['class_en'], 'cn':channel['class_cn']}).text=channel['class']
            ElementTree.SubElement(el_channel,"user_count").text=channel['user_count']
            ElementTree.SubElement(el_channel,"sn").text=channel['sn']
            ElementTree.SubElement(el_channel,"visit_count").text=channel['visit_count']
            ElementTree.SubElement(el_channel,"start_from").text=channel['start_from']
            ElementTree.SubElement(el_channel,"stream_type").text=channel['stream_type']
            ElementTree.SubElement(el_channel,"kbps").text=channel['kbps']
            ElementTree.SubElement(el_channel,"qs").text=channel['qs']
            ElementTree.SubElement(el_channel,"qc").text=channel['qc']
            el_schedule = ElementTree.SubElement(el_channel,"schedule")
            ElementTree.SubElement(el_schedule,"sch_domain").text=channel['sch_domain']
            ElementTree.SubElement(el_schedule,"file_name").text=channel['file_name']
            ElementTree.SubElement(el_schedule,"sch_channel_id").text=channel['sch_channel_id']
            ElementTree.SubElement(el_schedule,"sch_list_expire").text=channel['sch_list_expire']
            ElementTree.SubElement(el_schedule,"sch_timezone").text=channel['sch_timezone']
            ElementTree.SubElement(el_channel,"description").text=channel['description']
            ElementTree.SubElement(el_channel,"thumbnail").text=channel['thumbnail']
            el_sop_address = ElementTree.SubElement(el_channel,"sop_address")
            ElementTree.SubElement(el_sop_address,"item").text=channel['sop_address']

        chlist_tree.write(os.path.join(ADDON_PATH,"channel_guide.xml"),encoding="utf-8")
        xbmc.executebuiltin("Notification(%s,%s,%i)" % ("Channel saved", channel['name'], 1))
def update_list():
        Downloader(CHAN_LIST_URL,CHAN_LIST,settings.getLocalizedString(30006),settings.getLocalizedString(30007))

def removestation():
    sop_port = urlparse(sop).path.strip("/")
    remove = xbmcgui.Dialog().yesno(settings.getLocalizedString(30072), settings.getLocalizedString(30073)+name,settings.getLocalizedString(30074)+sop,settings.getLocalizedString(30075)+sop_port)
    if (remove):
        chlist_tree = ElementTree.parse(os.path.join(ADDON_PATH,"channel_guide.xml"))
        chlist_l = chlist_tree.find(".//channel/.[@id='"+sop_port+"']")
        if chlist_l:
            group_root = chlist_tree.find(".//group/.[@en='"+chlist_l.find('.//class').attrib['en']+"']")
            group_root.remove(chlist_l)
            chlist_tree.write(os.path.join(ADDON_PATH,"channel_guide.xml"),encoding="utf-8")
            xbmc.executebuiltin("Notification(%s,%s,%i)" % (settings.getLocalizedString(30071), name, 1))
def getactionno(action):
 # this is to detect action no. in case you wonder what is it
        count=0
        while count<100:
            count+=1
            if (action==count):
                xbmcgui.Dialog().ok("event",str(count),"","")
            xbmc.sleep(40)
class EPG(xbmcgui.WindowXMLDialog):
    def __init__( self , *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__( self , *args, **kwargs)
        self.spsc_pid=kwargs.get('spsc_pid')
 #       self.now_event=kwargs.get('now_event')

    def onInit(self):
        pass
    def onControl(self,control):
        pass

    def onClick( self, controlId ):
		pass
	
    def onFocus( self, controlId ):
		pass
	
    def onAction(self, action):
 #       self.setFocus( self.getControl(699))
  #      getactionno(action)
  # this is to detect visible windows:
  #      count=3000
  #      while count<12999:
  #          if xbmc.getCondVisibility('Window.IsVisible(%s)' % (str(count))):
  #              xbmc.executebuiltin("Notification(%s,%s,%i)" % ("window", str(count), 1))
  #          count+=1
  #          if count==4000:count=10000
  #          if count==10151: count=10500
  #          if count==10504:count=12000
  #          if count==12010:count=12900
        try: 
            if not os.path.exists("/proc/"+str(self.spsc_pid)): self.close()
        except: pass
        if action == ACTION_STOP:
            try:
#                os.system("killall -9 "+SPSC_BINARY)
                os.kill(self.spsc_pid,9)
                spsc.kill()
                spsc.wait()
                #if os.uname()[4] == "armv6l":
                #	try: os.system("killall -9 qemu-i386")
                #	except: pass
                xbmc.sleep(100)
            except:pass
            try:
                xbmc.Player(xbmc.PLAYER_CORE_AUTO).stop()
            except:pass
            self.close()
#        elif action == ACTION_NAV_BACK and xbmc.getCondVisibility('Control.IsVisible(50)'):
#            self.getControl( 50 ).setVisible(False)
        elif action == ACTION_PREVIOUS_MENU:
            xbmc.executebuiltin("ActivateWindow(videoosd)")
            self.close()
        elif action == ACTION_PAGE_UP or action == ACTION_MOVE_ITEM or action == ACTION_COPY_ITEM or action == ACTION_RENAME_ITEM:
            self.close()
            updatestation()
        elif action == ACTION_PAGE_DOWN or action == ACTION_DELETE_ITEM:
            if (CHAN_LIST == os.path.join(ADDON_PATH,"channel_guide.xml")): removestation()
            else: update_list()
        elif action == ACTION_SHOW_GUI:
            xbmc.executebuiltin("ActivateWindow(videolibrary)")
            self.close()

        elif action == ACTION_SELECT_ITEM:
  #          if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
  #              xbmc.executebuiltin("ActivateWindow(fullscreenvideo)")
 #               xbmc.executebuiltin("Action(aspectratio)")
                self.close()

        elif action == ACTION_MOVE_LEFT or action == ACTION_MOVE_RIGHT or action == ACTION_MOVE_UP or action == ACTION_MOVE_DOWN or action ==  ACTION_PAGE_UP or action ==  ACTION_PAGE_DOWN or action == ACTION_SHOW_INFO or action == ACTION_PAUSE or action == ACTION_NEXT_ITEM or action == ACTION_PREV_ITEM or action == ACTION_FORWARD or action == ACTION_REWIND:
            pass
#        elif action == ACTION_PARENT_DIR or action ==  ACTION_BUILT_IN_FUNCTION or action == ACTION_SHOW_VIDEOMENU or action == ACTION_SHOW_PLAYLIST:
        else:
            self.close()

def autostart(name):
    path=os.path.join(xbmc.translatePath("special://userdata"), 'autoexec.py')
# first remove the file if it is 0 bytes
    try:
        if str(os.stat(path)[6]).split('L')[0] == "0": os.remove(path)
    except: pass
 #   xbmcgui.Dialog().ok(sop,name,path,"")
 #   xbmc.executebuiltin("Notification(%s,%s,%i)" % ("window", "", 1))
    try:
        flag=False
        autoexec=""
        with open(path,'r') as f:
            for line in f:
                if "import xbmc" in line: flag=True
                if "plugin.video.xsopcast" in line: pass
                else: autoexec+=line
        if flag==False and settings.getSetting('autostart')=="true": autoexec="import xbmc\n"+autoexec
        if settings.getSetting('autostart')=="true":
            if settings.getSetting('autostart_last')=="true": autoexec+="xbmc.executebuiltin(\"RunPlugin(\\\"plugin://plugin.video.xsopcast/?sop="+sop+"&name="+name+"&mode=2\\\")\")\n"
            else: autoexec+="xbmc.executebuiltin(\"RunPlugin(\\\"plugin://plugin.video.xsopcast/?sop=sop://broker.sopcast.com:3912/"+settings.getSetting('autostart_custom')+"&name="+name+"&mode=2\\\")\")\n"

        f = open(path,'w')
        f.write(autoexec)
        f.close()
    except:
        if settings.getSetting('autostart')=="true":
            autoexec="import xbmc\n"
            if settings.getSetting('autostart_last')=="true": autoexec+="xbmc.executebuiltin(\"RunPlugin(\\\"plugin://plugin.video.xsopcast/?sop="+sop+"&name="+name+"&mode=2\\\")\")\n"
            else: autoexec+="xbmc.executebuiltin(\"RunPlugin(\\\"plugin://plugin.video.xsopcast/?sop=sop://broker.sopcast.com:3912/"+settings.getSetting('autostart_custom')+"&name="+name+"&mode=2\\\")\")\n"
            f = open(path,'w')
            f.write(autoexec)
            f.close()
            
def update_kbps():
    downloadRate=0
    logfile_=open(SPSC_LOG,"r")
    logfile=logfile_.read()
    logfile_.close
    if len(logfile) < 200000: return
    downloadRates=re.compile('GLOBAL downloadRate=(.*?)	dnSum=',re.DOTALL).findall(logfile)
    downloadRate=int(round(int(max(downloadRates,key=int))/1000,-1))
    if downloadRate > 0:
        sop_port = urlparse(sop).path.strip("/")
        chlist_tree = ElementTree.parse(os.path.join(ADDON_PATH,"channel_guide.xml"))
        chlist_l = chlist_tree.find(".//channel/.[@id='"+sop_port+"']")
        chlist_l.find('.//kbps').text = str(downloadRate)
        chlist_tree.write(os.path.join(ADDON_PATH,"channel_guide.xml"),encoding="utf-8")

class streamplayer(xbmc.Player):
    def __init__( self , *args, **kwargs):
        self.spsc_pid=kwargs.get('spsc_pid')
        self.listitem=kwargs.get('listitem')
 #       self.sop=kwargs.get('sop')
 #       self.now_event=kwargs.get('now_event')
    def onPlayBackStarted(self):
# this will kill the sopcast if we changed the media
        if xbmc.Player(xbmc.PLAYER_CORE_AUTO).getPlayingFile() != "http://"+LOCAL_IP+":"+str(VIDEO_PORT)+"/":
            try: os.kill(self.spsc_pid,9)
            except: pass
            try: EPG.close()
            except:
                if xbmc.getCondVisibility("Window.IsActive(epg.xml)"):
                    xbmc.executebuiltin("Action(Select)") 
                    xbmc.executebuiltin("Action(Close)")
        else: autostart(self.listitem.getLabel())
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    def onPlayBackEnded(self):
 #       xbmcgui.Dialog().ok("onplaybackended","","","")
        url = "http://"+LOCAL_IP+":"+str(VIDEO_PORT)+"/"
        xbmc.sleep(300)
        if os.path.exists("/proc/"+str(self.spsc_pid)) and xbmc.getCondVisibility("Window.IsActive(epg.xml)") and settings.getSetting('safe_stop')=="true":
            if not xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying():
                player = streamplayer(xbmc.PLAYER_CORE_AUTO , spsc_pid=self.spsc_pid , listitem=self.listitem)
                player.play(url, self.listitem)
     
        else: 
            try: os.kill(self.spsc_pid,9)
            except: pass
            #if os.uname()[4] == "armv6l":
                	#try: os.system("killall -9 qemu-i386")
                	#except: pass
            try: EPG.close()
            except:
                if xbmc.getCondVisibility("Window.IsActive(epg.xml)"):
                    xbmc.executebuiltin("Action(Select)") 
                    xbmc.executebuiltin("Action(Close)")
    def onPlayBackStopped(self):
#        xbmc.executebuiltin("Notification(%s,%s,%i)" % ("onPlayBackStopped", "", 5))
#        xbmc.sleep(1000)
        url = "http://"+LOCAL_IP+":"+str(VIDEO_PORT)+"/"
 #       xbmc.executebuiltin( "ActivateWindow(busydialog)" )
  #      xbmcgui.Dialog().ok("onplaybackended","3","","")
        xbmc.sleep(300)
        if os.path.exists("/proc/"+str(self.spsc_pid)) and xbmc.getCondVisibility("Window.IsActive(epg.xml)") and settings.getSetting('safe_stop')=="true":
            if not xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying(): 
                player = streamplayer(xbmc.PLAYER_CORE_AUTO , spsc_pid=self.spsc_pid , listitem=self.listitem)
                player.play(url, self.listitem)
     
        else:
            try: os.kill(self.spsc_pid,9)
            except: pass
            #if os.uname()[4] == "armv6l":
            #    	try: os.system("killall -9 qemu-i386")
            #    	except: pass
            try: EPG.close()
            except:
                if xbmc.getCondVisibility("Window.IsActive(epg.xml)"):
                    xbmc.executebuiltin("Action(Select)") 
                    xbmc.executebuiltin("Action(Close)")
            if LOG_SOPCAST == "true" and settings.getSetting('update_kbps')=="true": update_kbps()

def epg_window(file_name,chan_name):
    now_event = {'event_id':0 , 'event_title':'Unknown event' , 'event_subtitle':'' , 'event_cast':'' , 'event_time':'' , 'file_name':file_name}
#    xbmcgui.Dialog().ok("jjjj","","","")
    if file_name!="":
        sched = get_epg(file_name)
#        sched = schedule( sch_domain , file_name , sch_channel_id , sch_list_expire , sch_timezone , True)
        epg_events=""
        nowtime = time.mktime( time.localtime())
        total_events=len(sched['event_title'])
        count_delay = 0
        now_event['total_events']=total_events
        now_event['event_time']=nowtime
        now_event['event_end_time']=sched['event_time'][0]
        now_event['event_sel_delay'] = sched['event_id'][0]
#        xbmcgui.Dialog().ok(sched['title'],"","","")
#
        for count in range(total_events):
            if nowtime > sched['event_time'][count]:
                textcolor="88888888"
                if total_events>count+1 and nowtime <= sched['event_time'][count+1]:
                    now_event['event_end_time']=sched['event_time'][count+1]
                    textcolor="selected"
                now_event['event_id']=int(sched['event_id'][count])
                now_event['event_title']=sched['event_title'][count]
                now_event['event_subtitle']=sched['event_subtitle'][count]
                now_event['event_cast']=sched['event_cast'][count]
                now_event['event_time']=sched['event_time'][count]
            else:
                textcolor="FFFFFFFF"
                count_delay += 1
                if count_delay < 8: now_event['event_sel_delay'] = sched['event_id'][count]
            epg_subtitle=""
            if sched['event_subtitle'][count] != "": epg_subtitle += " " + sched['event_subtitle'][count]
            if sched['event_cast'][count] != "": epg_subtitle += " " + sched['event_cast'][count]
            if epg_subtitle != "": epg_subtitle= " -" + epg_subtitle

            if settings.getSetting('sch_hour_format')=="true": formated_time=time.strftime("%A %H:%M - ", time.localtime(sched['event_time'][count]))
            elif settings.getSetting('sch_hour_ampm')=="true": formated_time=time.strftime("%A %I:%M%p - ", time.localtime(sched['event_time'][count]))
            else: formated_time=time.strftime("%A %I:%M - ", time.localtime(sched['event_time'][count]))

            epg_events+='				<control type="button" id="'+str(700+int(sched['event_id'][count]))+'">\n'
            epg_events+='					<label>' + formated_time + sched['event_title'][count] + epg_subtitle + '</label>\n'
            epg_events+='					<width>860</width>\n'
            epg_events+='					<textcolor>'+textcolor+'</textcolor>\n'
#            epg_events+='					<include>dialogButton</include>\n'
            epg_events+='				</control>\n'
            
        if settings.getSetting('sch_hour_format')=="true":
            formated_start_time=time.strftime("%H:%M --- ", time.localtime(now_event['event_time']))
            formated_end_time=time.strftime(" --- %H:%M", time.localtime(now_event['event_end_time']))
        elif settings.getSetting('sch_hour_ampm')=="true":
            formated_start_time=time.strftime("%I:%M%p --- ", time.localtime(now_event['event_time']))
            formated_end_time=time.strftime(" --- %I:%M%p", time.localtime(now_event['event_end_time']))
        else:
            formated_start_time=time.strftime("%I:%M --- ", time.localtime(now_event['event_time']))
            formated_end_time=time.strftime(" --- %I:%M", time.localtime(now_event['event_end_time']))
 
        epg='<window type="dialog">\n'
        epg+='	<defaultcontrol always="true">'+str(700+int(now_event['event_sel_delay']))+'</defaultcontrol>\n'
#        epg+='	<defaultcontrol always="true">699</defaultcontrol>\n'
        epg+='	<coordinates>\n'
        epg+='		<system>1</system>\n'
        epg+='		<posx>0</posx>\n'
        epg+='		<posy>0</posy>\n'
        epg+='	</coordinates>\n'
        epg+='	<include>dialogeffect</include>\n'

 #       epg+='	<include>dialogbusy</include>\n'
        epg+='	<controls>\n'
#busy dialog
        epg+='		<control type="group">\n'
        epg+='			<visible>!Player.Playing + !Player.Paused</visible>\n'
        epg+='			<posx>1070</posx>\n'
        epg+='			<posy>638</posy>\n'
        epg+='			<control type="image">\n'
        epg+='				<description>background image</description>\n'
        epg+='				<posx>0</posx>\n'
        epg+='				<posy>0</posy>\n'
        epg+='				<width>200</width>\n'
        epg+='				<height>72</height>\n'
        epg+='				<texture border="20">OverlayDialogBackground.png</texture>\n'
        epg+='			</control>\n'
        epg+='			<control type="image">\n'
        epg+='				<description>Busy animation</description>\n'
        epg+='				<posx>20</posx>\n'
        epg+='				<posy>20</posy>\n'
        epg+='				<width>32</width>\n'
        epg+='				<height>32</height>\n'
        epg+='				<texture>busy.png</texture>\n'
        epg+='				<aspectratio>keep</aspectratio>\n'
        epg+='				<animation effect="rotate" start="0" end="360" center="36,36" time="1200" loop="true" condition="true">conditional</animation>\n'
        epg+='			        </control>\n'
        epg+='			<control type="label">\n'
        epg+='				<description>Busy label</description>\n'
        epg+='				<posx>60</posx>\n'
        epg+='				<posy>20</posy>\n'
        epg+='				<width>120</width>\n'
        epg+='				<height>32</height>\n'
        epg+='				<align>left</align>\n'
        epg+='				<aligny>center</aligny>\n'
        epg+='				<label>$LOCALIZE[31004]</label>\n'
        epg+='				<font>font12</font>\n'
        epg+='			</control>\n'
        epg+='		</control>\n'
#main window
        epg+='		<control type="group" id="697">\n'
        epg+='			<include>VisibleFadeEffect</include>\n'
        epg+='			<posx>310</posx>\n'
        epg+='			<posy>50</posy>\n'
        epg+='			<visible>Player.ShowInfo + [Player.Playing | Player.Paused]</visible>\n'
        epg+='			<control type="image">\n'
        epg+='				<description>background image</description>\n'
        epg+='				<posx>0</posx>\n'
        epg+='				<posy>0</posy>\n'
        epg+='				<width>910</width>\n'
        epg+='				<height>500</height>\n'
        epg+='				<texture border="8">DialogBack.png</texture>\n'
        epg+='				<colordiffuse>99009900</colordiffuse>\n'
        epg+='			</control>\n'
        epg+='			<control type="image">\n				<description>Dialog Header image</description>\n				<posx>40</posx>\n				<posy>16</posy>\n				<width>830</width>\n				<height>40</height>\n				<texture>dialogheader.png</texture>\n            </control>\n'
        epg+='			<control type="label">\n'
        epg+='			<description>Channel name</description>\n'
        epg+='			<posx>40</posx>\n'
        epg+='			<posy>20</posy>\n'
        epg+='			<width>830</width>\n'
        epg+='			<height>30</height>\n'
        epg+='			<font>font13_title</font>\n'
#        epg+='			<label>'+chan_name+'</label>\n'
        epg+='			<label>' + formated_start_time + now_event['event_title'] + formated_end_time + '</label>\n'
        epg+='			<align>center</align>\n'
        epg+='			<aligny>center</aligny>\n'
        epg+='			<textcolor>selected</textcolor>\n'
        epg+='			<shadowcolor>black</shadowcolor>\n'
        epg+='			</control>\n'

        epg+='			<control type="grouplist" id="698">\n'
        epg+='				<description>Events List</description>\n'
        epg+='				<posx>20</posx>\n'
        epg+='				<posy>65</posy>\n'
        epg+='				<width>870</width>\n'
        epg+='				<height>415</height>\n'
        epg+='				<itemgap>2</itemgap>\n'
        epg+='				<pagecontrol>699</pagecontrol>\n'
        epg+='				<scrolltime tween="linear">400</scrolltime>\n'
        epg+='				<orientation>vertical</orientation>\n'
        epg+='				<usecontrolcoords>false</usecontrolcoords>\n'
        if SCH_SCROLLBAR_FOCUS == "true": epg+='				<onright>699</onright>\n'
        else: epg+='				<onright>'+str(700+int(now_event['event_id']))+'</onright>\n'
        epg+='				<onleft>'+str(700+int(now_event['event_id']))+'</onleft>\n'
        epg+=epg_events
        epg+='			</control>\n' #grouplist
        epg+='			<control type="scrollbar" id="699">\n'
        epg+='				<description>Events Scrollbar</description>\n'
        epg+='				<posx>870</posx>\n'
        epg+='				<posy>55</posy>\n'
        epg+='				<width>30</width>\n'
        epg+='				<height>435</height>\n'
        epg+='				<texturesliderbackground border="0,14,0,14">ScrollBarV.png</texturesliderbackground>\n'
        if SCH_SCROLLBAR_FOCUS == "true": epg+='				<texturesliderbar border="0,14,0,14">'+os.path.join(ADDON_PATH,'resources/skins/skin.confluence/media/ScrollBarV_bar.png')+'</texturesliderbar>\n'
        else: epg+='				<texturesliderbar border="0,14,0,14">ScrollBarV_bar_focus.png</texturesliderbar>\n'
        epg+='				<texturesliderbarfocus border="0,14,0,14">ScrollBarV_bar_focus.png</texturesliderbarfocus>\n'
        epg+='				<textureslidernib>ScrollBarNib.png</textureslidernib>\n'
        epg+='				<textureslidernibfocus>ScrollBarNib.png</textureslidernibfocus>\n'
        epg+='				<orientation>vertical</orientation>\n'
        epg+='				<onleft>'+str(700+int(now_event['event_id']))+'</onleft>\n'
        epg+='			</control>\n'
        epg+='		</control>\n' #group
        epg+='	</controls>\n'
        epg+='</window>'
        path=os.path.join(ADDON_PATH, 'resources/skins/skin.confluence/720p','epg.xml')
        f = open(path,'w')
        f.write(epg)
        f.close()
        path=os.path.join(ADDON_PATH, 'resources/skins/default/720p','epg.xml')
        f = open(path,'w')
        f.write(epg)
        f.close()

    return now_event

def STREAM(name,iconimage):
  try:
 #   iconimage="http://image.bayimg.com/aajgmaadb.jpg"
 #   xbmcgui.Dialog().ok(name,sop1,iconimage,sop)
    xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    global sop
    if sop == "":
        channel_id = xbmcgui.Dialog().numeric(0, 'Enter Channel Id')
        if int(channel_id)>0:
        #    global sop
            try:chlist_s = ElementTree.parse(os.path.join(ADDON_PATH,"chlist.xml")).find(".//channel/.[@id='"+sop_port+"']")
            except:chlist_s=None
            try:chlist_l = ElementTree.parse(os.path.join(ADDON_PATH,"channel_guide.xml")).find(".//channel/.[@id='"+sop_port+"']")
            except:chlist_l=None
            try:chlist_r = ElementTree.parse(os.path.join(ADDON_PATH,"remote_list.xml")).find(".//channel/.[@id='"+sop_port+"']")
            except:chlist_r=None
            if chlist_s: sop= chlist_s.findtext('./sop_address/item', default="")
            elif chlist_l: sop= chlist_l.findtext('./sop_address/item', default="")
            elif chlist_r: sop= chlist_r.findtext('./sop_address/item', default="")
            elif settings.getSetting('select_address') == "true":
                server_list=['sop://broker.sopcast.com:3912/','sop://211.152.36.38:3912/','sop://221.12.89.140:3912/','sop://221.12.89.140:53/']
                sel_item = xbmcgui.Dialog().select('Select the server', server_list)
                server=server_list[sel_item]
                sop=server+channel_id
            else: sop="sop://broker.sopcast.com:3912/"+channel_id
        else: return
    else:channel_id=sop.split("/")[-1]
    if settings.getSetting('sop_override') == "true": sop="sop://"+settings.getSetting('sop_address')+"/"+channel_id
#    sop=sop1
    xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    epg='<window type="dialog">\n'
    epg+='	<coordinates>\n'
    epg+='		<system>1</system>\n'
    epg+='		<posx>0</posx>\n'
    epg+='		<posy>0</posy>\n'
    epg+='	</coordinates>\n'
    epg+='	<include>dialogeffect</include>\n'
    epg+='	<controls>\n'
#---start busy dialog
    epg+='		<control type="group">\n'
    epg+='			<visible>!Player.Playing + !Player.Paused</visible>\n'
    epg+='			<posx>1070</posx>\n'
    epg+='			<posy>638</posy>\n'
    epg+='			<control type="image">\n'
    epg+='				<description>background image</description>\n'
    epg+='				<posx>0</posx>\n'
    epg+='				<posy>0</posy>\n'
    epg+='				<width>200</width>\n'
    epg+='				<height>72</height>\n'
    epg+='				<texture border="20">OverlayDialogBackground.png</texture>\n'
    epg+='			</control>\n'
    epg+='			<control type="image">\n'
    epg+='				<description>Busy animation</description>\n'
    epg+='				<posx>20</posx>\n'
    epg+='				<posy>20</posy>\n'
    epg+='				<width>32</width>\n'
    epg+='				<height>32</height>\n'
    epg+='				<texture>busy.png</texture>\n'
    epg+='				<aspectratio>keep</aspectratio>\n'
    epg+='				<animation effect="rotate" start="0" end="360" center="36,36" time="1200" loop="true" condition="true">conditional</animation>\n'
    epg+='			        </control>\n'
    epg+='			<control type="label">\n'
    epg+='				<description>Busy label</description>\n'
    epg+='				<posx>60</posx>\n'
    epg+='				<posy>20</posy>\n'
    epg+='				<width>120</width>\n'
    epg+='				<height>32</height>\n'
    epg+='				<align>left</align>\n'
    epg+='				<aligny>center</aligny>\n'
    epg+='				<label>$LOCALIZE[31004]</label>\n'
    epg+='				<font>font12</font>\n'
    epg+='			</control>\n'
    epg+='		</control>\n'
#----end busy dialog
    epg+='	</controls>\n'
    epg+='</window>'
    f = open(os.path.join(ADDON_PATH, 'resources/skins/skin.confluence/720p','epg.xml'),'w')
    f.write(epg)
    f.close()
    f = open(os.path.join(ADDON_PATH, 'resources/skins/default/720p','epg.xml'),'w')
    f.write(epg)
    f.close()
    global spsc
    if LOG_SOPCAST == "true":
    	if os.uname()[4] == "armv6l":
    		cmd = [os.path.join(ADDON_PATH,"sopcast-raspberry") +"/qemu-i386",os.path.join(ADDON_PATH,"sopcast-raspberry")+"/lib/ld-linux.so.2","--library-path",os.path.join(ADDON_PATH,"sopcast-raspberry")+"/lib",os.path.join(ADDON_PATH,"sopcast-raspberry")+"/sp-sc-auth",sop,"1234","9001"]
        else: cmd = [SPSC, sop, str(LOCAL_PORT), str(VIDEO_PORT)]#,">", SPSC_LOG,"2>&1"]
        log=file(SPSC_LOG,'w')
        spsc = subprocess.Popen(cmd, shell=False, bufsize=BUFER_SIZE,stdin=None, stdout=log, stderr=None)
        log.close()
#        spsc = subprocess.Popen(cmd, shell=False, bufsize=BUFER_SIZE, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#        log = open(SPSC_LOG,'w')
#        log.write('')
#        log.close()
#        subprocess.Popen("while read line; do echo $line >> "+SPSC_LOG+" ; done", shell=True, stdin=spsc.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
    	if os.uname()[4] == "armv6l":
    		cmd = [os.path.join(ADDON_PATH,"sopcast-raspberry") +"/qemu-i386",os.path.join(ADDON_PATH,"sopcast-raspberry")+"/lib/ld-linux.so.2","--library-path",os.path.join(ADDON_PATH,"sopcast-raspberry")+"/lib",os.path.join(ADDON_PATH,"sopcast-raspberry")+"/sp-sc-auth",sop,"1234","9001"]
        else: cmd = [SPSC, sop, str(LOCAL_PORT), str(VIDEO_PORT), "> /dev/null &"]
        spsc = subprocess.Popen(cmd, shell=False, bufsize=BUFER_SIZE,stdin=None, stdout=None, stderr=None)


     
        
#    f = open(SOPCAST_PID, 'w')
#    f.write(str(spsc.pid))
#    f.close()
    file_name=""
    channel=ElementTree.parse(os.path.join(ADDON_PATH,"channel_guide.xml")).find( ".//channel/.[@id='"+channel_id+"']" )
    if channel:
            name = channel.findtext('./name', default="").strip()
            chan_url = channel.findtext('./sop_address/item', default="")
            chan_users = channel.findtext('.//user_count', default="")
            chan_kbps = channel.findtext('.//kbps', default="")
            chan_stream_type = channel.findtext('.//stream_type', default="")
            sch_domain = channel.findtext('./schedule/sch_domain', default="")
            file_name = channel.findtext('./schedule/file_name', default="")
            sch_channel_id = channel.findtext('./schedule/sch_channel_id', default="")
            sch_list_expire = channel.findtext('./schedule/sch_list_expire', default="")
            sch_timezone = channel.findtext('./schedule/sch_timezone', default="")
            iconimage=channel.findtext('.//thumbnail', default="")
            if iconimage=="" or iconimage==None: iconimage = channel.findtext('./description/thumbnail', default="")
            if SCH_OVER_EXPIRED == "true": sch_list_expire = SCH_NEW_EXPIRED
            if SHOW_KBPS=="true" and chan_kbps.strip() != "" and int(chan_kbps)>0:
                name += " "+chan_kbps+" kbps"
            if chan_stream_type == "mpeg-ts" or chan_stream_type == "mpeg-ps": chan_stream_type = "h264"
            if SHOW_STREAM_TYPE=="true" and chan_stream_type.strip() != "":
                name += " ["+chan_stream_type+"]"


    listitem = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    listitem.setLabel(name)
    listitem.setInfo('video', {'Title': name})

    url = "http://"+LOCAL_IP+":"+str(VIDEO_PORT)+"/"
 #   xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    db_connection.close()
    xbmc.sleep(int(settings.getSetting('wait_time')))
 #   xbmcgui.Dialog().ok("onplaybackended",str(spsc.pid),"","")
    res=False
    counter=50
    while counter > 0 and os.path.exists("/proc/"+str(spsc.pid)):
 #       xbmc.executebuiltin("Notification(%s,%s,%i)" % (str(1), str(counter), 5))

        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        xbmc.sleep(400)
        counter -= 1
        if LOG_SOPCAST == "true":
            logfile=open(SPSC_LOG)
            for line in logfile:
                    if 'downloadRate' not in line: continue
                    else:
                        counter=0
                        res=True
                        break
            logfile.close
        else:
            try:
                urllib2.urlopen(url)
                counter=0
                res=sop_sleep(200 , spsc.pid)
                break
            except:pass
                
#    
#    res=sop_sleep(2500 , spsc.pid)
    if res:
        player = streamplayer(xbmc.PLAYER_CORE_AUTO , spsc_pid=spsc.pid , listitem=listitem)
        player.play(url, listitem)
# this is a new thread for watching sop process and restarting the player if it dies
 #this will cause the player not to stop if the EPG class is not active
 #       thread.start_new_thread(WATCH_SOP_THREAD, (spsc.pid,listitem,sop))

# this is a new thread for grabbing new schedules while playing
        if PLAYING_GRAB == "true": thread.start_new_thread(GRAB_SCH_THREAD, (spsc.pid,listitem,0))

# this is a new thread for watching event change during play
        if NOTIFY_EVENTS == "true" and file_name != "": thread.start_new_thread(EVENT_SCH_THREAD, (spsc.pid , file_name , name))

        mydisplay = EPG("epg.xml",ADDON_PATH,spsc_pid=spsc.pid)
        mydisplay.doModal()
        del mydisplay

        time_c=0
        while os.path.exists("/proc/"+str(spsc.pid)) and not xbmc.abortRequested:
  #      if time_c==0: checkwindow()
            if xbmcgui.getCurrentWindowId() == WINDOW_FULLSCREEN_VIDEO and not xbmc.getCondVisibility("Window.IsVisible(12901)") :
                if time_c>10:
                    time_c=0
                    mydisplay = EPG("epg.xml",ADDON_PATH,spsc_pid=spsc.pid)
                    mydisplay.doModal()
                    del mydisplay
                else:time_c+=1
            else: time_c=0
            xbmc.sleep(500)

    elif channel and not os.path.exists("/proc/"+str(spsc.pid)):
        try:
            urllib2.urlopen("http://www.google.com")
            if settings.getSetting('chan_list_remove')=="true" and CHAN_LIST==os.path.join(ADDON_PATH,"channel_guide.xml"): removestation()
            elif NOTIFY_OFFLINE == "true": xbmc.executebuiltin("Notification(%s,%s,%i)" % (settings.getLocalizedString(30085), "", 1))

        except:
            if NOTIFY_OFFLINE == "true": xbmc.executebuiltin("Notification(%s,%s,%i)" % (settings.getLocalizedString(30053), "", 1))
    elif NOTIFY_OFFLINE == "true": xbmc.executebuiltin("Notification(%s,%s,%i)" % (settings.getLocalizedString(30076), "", 1))

    try: os.kill(spsc.pid,9)
    #os.system("killall -9 "+SPSC_BINARY)
    except: pass
    #if os.uname()[4] == "armv6l":
    	#try: os.system("killall -9 qemu-i386")
    	#except: pass
    try:
        xbmc.executebuiltin("Dialog.Close(all,true)")
#        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    except: pass

  except:
    try: EPG.close()
    except: pass
    try: os.system("killall -9 "+SPSC_BINARY)
    except: pass
    try: xbmc.executebuiltin("Dialog.Close(all,true)")
    except: pass
def addLink(name,url,mode,iconimage,plot):
    ok = True
    u=sys.argv[0]+"?"+"sop="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name.decode('utf8').encode('utf8'))+"&iconimage="+urllib.quote_plus(iconimage)
    liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": plot} )
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz)
    return ok

def addDir(name,url,mode):
    u=sys.argv[0]+"?"+"mode="+str(mode)+"&name="+urllib.quote_plus(name.decode('utf8').encode('utf8'))
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png",thumbnailImage="")
    liz.setInfo( type="Video", infoLabels={ "Title": name })
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    return ok

try: sop=urllib.unquote_plus(params["sop"])
except: sop=None

try: name=urllib.unquote_plus(params["name"].decode('utf8').encode('utf8'))
except: name=None

try: iconimage=urllib.unquote_plus(params["iconimage"])
except: iconimage=None

if mode==None or name==None or len(name)<1 or mode==0:
    if OS == PLATFORM: FETCH_CHANNEL()
elif mode==1: #groups
    INDEX(name)
elif mode==2: #links
    if xbmc.Player(xbmc.PLAYER_CORE_AUTO).isPlaying("http://"+LOCAL_IP+":"+str(VIDEO_PORT)+"/"):
        os.system("killall -9 "+SPSC_BINARY)
        #KILL_SOP(OS)
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).stop()
        try: xbmc.executebuiltin("Dialog.Close(all,true)")
        except: pass
        xbmc.sleep(500)
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )

        STREAM(name,iconimage)
    else:
        os.system("killall -9 "+SPSC_BINARY)
        #KILL_SOP(OS)
        STREAM(name,iconimage)

if (OS == PLATFORM) and (my_error == 0): xbmcplugin.endOfDirectory(int(sys.argv[1]))
## if it's not linux we will simply exit
