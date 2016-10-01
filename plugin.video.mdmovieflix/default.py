import sys,urllib,re,xbmcplugin,xbmcgui,xbmc,xbmcaddon,xbmcvfs,os,shutil
from addon.common.addon import Addon
import requests


#MovieFlix Add-on Created By Mucky Duck (7/2016)


User_Agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36'
addon_id = 'plugin.video.mdmovieflix'
selfAddon = xbmcaddon.Addon(id=addon_id)
addon_name = selfAddon.getAddonInfo('name')
addon = Addon(addon_id, sys.argv)
art = xbmc.translatePath(os.path.join('special://home/addons/' + addon_id + '/resources/art/'))
icon = xbmc.translatePath(os.path.join('special://home/addons/' + addon_id, 'icon.png'))
fanart = xbmc.translatePath(os.path.join('special://home/addons/' + addon_id , 'fanart.jpg'))
show_tv = selfAddon.getSetting('enable_shows')
show_mov = selfAddon.getSetting('enable_movies')
baseurl = 'http://movieflix.to'
baseurl1 = baseurl + '/movies'
baseurl2 = baseurl + '/shows'
s = requests.session()




def CAT():
        if show_tv == 'true':
                addDir('[B][I][COLOR firebrick]TV SHOWS[/COLOR][/I][/B]',baseurl2,1,art+'icon.png',fanart,'')
        if show_mov == 'true':
                addDir('[B][I][COLOR firebrick]MOVIES[/COLOR][/I][/B]',baseurl1,1,art+'icon.png',fanart,'')




def MENU(url):
        #if url == baseurl2:
                #addDir('[B][I][COLOR firebrick]New Episodes[/COLOR][/I][/B]',baseurl+'/latest/episodes',5,art+'icon.png',fanart,'')
        headers = {'Accept':'application/json', 'User-Agent':User_Agent}
        r = s.get(url, headers=headers).json()
        json_data = r['filters']
        for links in json_data[:5]:
                name = links['title']
                url2 = links['url']
                url2 = url2 + '&p=1'
                addDir('[B][I][COLOR firebrick]%s[/COLOR][/I][/B]' %name,url2,2,art+'icon.png',fanart,'')
        addDir('[B][I][COLOR firebrick]Genre[/COLOR][/I][/B]',url,6,art+'icon.png',fanart,'')
        addDir('[B][I][COLOR firebrick]Search[/COLOR][/I][/B]','url',7,art+'icon.png',fanart,'')




def INDEX(url):
        headers = {'Accept':'application/json', 'User-Agent':User_Agent}
        r = s.get(url, headers=headers).json()
        json_data = r['items']
        for links in json_data:
                type = links['type']
                name = links['title']
                name = addon.unescape(name)
                name = name.encode('ascii', 'ignore').decode('ascii')
                year = links['year']
                url2 = links['url']
                if baseurl not in url2:
                        url2 = baseurl + url2
                poster = 'http:' + links['images']['poster']
                thumb = poster.replace('353x208','172x255')
                fanart = poster.replace('353x208/posters','previews')
                info = links['description']
                info = addon.unescape(info)
                info = info.encode('ascii', 'ignore').decode('ascii')
                if type == 'movie':
                        addDir('[B][I][COLOR white]%s[/COLOR] [COLOR firebrick](%s)[/COLOR][/I][/B]' %(name,year),url2,100,thumb,fanart,info)
                elif type == 'tvshow':
                        addDir('[B][I][COLOR white]%s[/COLOR][/I][/B]' %name,url2,3,thumb,fanart,info)
        try:
                np = re.split(r"&p=", str(url), re.I)
                pn = int(np[1]) + 1
                url = np[0] + '&p=' + str(pn)
                addDir('[B][I][COLOR firebrick]Go To Next Page>>>[/COLOR][/I][/B]',url,2,art+'next.png',fanart,'')
        except: pass
        if type == 'movie':
                setView('movies', 'movie-view')
        elif type == 'tvshow':
                setView('tvshows', 'show-view')




def SEA(name,url,iconimage):
        headers = {'Accept':'application/json', 'User-Agent':User_Agent}
        r = s.get(url, headers=headers).json()
        json_data = r['seasons']
        items = len(json_data)
        for links in json_data:
                name = links['title']
                url = links['url']
                if baseurl not in url:
                        url = baseurl + url
                fanart = 'http:' + links['images']['preview_large']
                addDir('[B][I][COLOR firebrick]%s[/COLOR][/I][/B]' %name,url,4,iconimage,fanart,'')




def EP(name,url,iconimage):
        if iconimage == None:
                iconimage = icon
        headers = {'Accept':'application/json', 'User-Agent':User_Agent}
        r = s.get(url, headers=headers).json()
        json_data = r['episodes']
        items = len(json_data)
        for links in json_data:
                name = links['title']
                name = addon.unescape(name)
                name = name.encode('ascii', 'ignore').decode('ascii')
                ep = links['seq']
                if 'media' in links:
                        try:
                                url = links['media']['720']
                        except:
                                url = links['media']['480']
                fanart = 'http:' + links['images']['preview_large']
                info = links['description']
                info = addon.unescape(info)
                info = info.encode('ascii', 'ignore').decode('ascii')
                addDir('[B][I][COLOR firebrick]Episode%s:[/COLOR] [COLOR white]%s[/COLOR][/I][/B]' %(ep,name),url,100,iconimage,fanart,info)
        setView('tvshows', 'show-view')




def NEW_EP(url):
        headers = {'Accept':'application/json', 'User-Agent':User_Agent}
        r = s.get(url, headers=headers).json()
        json_data = r['items']
        for links in json_data:
                name = links['title']
                name = addon.unescape(name)
                name = name.encode('ascii', 'ignore').decode('ascii')
                url2 = links['url']
                if baseurl not in url2:
                        url2 = baseurl + url2
                poster = 'http:' + links['images']['poster']
                thumb = poster.replace('353x208','172x255')
                fanart = poster.replace('353x208','1280x720')
                info = links['description']
                info = addon.unescape(info)
                info = info.encode('ascii', 'ignore').decode('ascii')
                addDir('[B][I][COLOR white]%s[/COLOR][/I][/B]' %name,url2,100,thumb,fanart,info)
        try:
                np = re.split(r"&p=", str(url), re.I)
                pn = int(np[1]) + 1
                url = np[0] + '&p=' + str(pn)
                addDir('[B][I][COLOR firebrick]Go To Next Page>>>[/COLOR][/I][/B]',url,5,art+'next.png',fanart,'')
        except: pass
        setView('tvshows', 'show-view')




def SEARCH():
        keyb = xbmc.Keyboard('', 'Search')
        keyb.doModal()
        if (keyb.isConfirmed()):
                search = keyb.getText().replace(' ','%20')
                url = baseurl + '/search?q=' + search
                INDEX(url)




def GENRE(url):
        headers = {'Accept':'application/json', 'User-Agent':User_Agent}
        r = s.get(url, headers=headers).json()
        json_data = r['filters']
        for links in json_data[5:]:
                genre = links['items']
                for genres in genre:
                        name = genres['title']
                        url = genres['url']
                        url = url + '&p=1'
                        addDir('[B][I][COLOR firebrick]%s[/COLOR][/I][/B]' %name,url,2,art+'icon.png',fanart,'')




def RESOLVE(name,url,iconimage):
        if baseurl in url:
                headers = {'Accept':'application/json', 'Referer':url, 'User-Agent':User_Agent}
                link = s.get(url, headers=headers).json()
                try:
                        url = link['item']['media']['720']
                except:
                        url = link['item']['media']['480']
        else:
                url = url
        liz = xbmcgui.ListItem(name, iconImage='DefaultVideo.png', thumbnailImage=iconimage)
        liz.setInfo(type='Video', infoLabels={"Title":name,"Plot":description})
        liz.setProperty("IsPlayable","true")
        liz.setPath(url)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)




def regex_from_to(text, from_string, to_string, excluding=True):
        if excluding:
                try: r = re.search("(?i)" + from_string + "([\S\s]+?)" + to_string, text).group(1)
                except: r = ''
        else:
                try: r = re.search("(?i)(" + from_string + "[\S\s]+?" + to_string + ")", text).group(1)
                except: r = ''
        return r




def regex_get_all(text, start_with, end_with):
        r = re.findall("(?i)(" + start_with + "[\S\s]+?" + end_with + ")", text)
        return r




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




def addDir(name,url,mode,iconimage,fanart,description):
        name = name.replace('()','')
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&iconimage="+urllib.quote_plus(iconimage)+"&description="+urllib.quote_plus(description)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
        liz.setInfo(type="Video", infoLabels={"Title":name,"Plot":description})
        liz.setProperty('fanart_image', fanart)
        if mode==100:
            liz.setProperty("IsPlayable","true")
            ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
        else:
            ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok




def notification(title, message, icon):
        addon.show_small_popup( addon.get_name(), message.title(), 5000, icon)
        #notification( addon.get_name(), 'fetching trailer', addon.get_icon())
        return




def addLink(name,url,mode,iconimage,fanart,description=''):
        #u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&description="+str(description)
        #ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name, 'plot': description } )
        liz.setProperty('fanart_image', fanart)
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz,isFolder=False)
        return ok




def setView(content, viewType):
    ''' Why recode whats allready written and works well,
    Thanks go to Eldrado for it '''
    if content:
        xbmcplugin.setContent(int(sys.argv[1]), content)
    if addon.get_setting('auto-view') == 'true':

        print addon.get_setting(viewType)
        if addon.get_setting(viewType) == 'Info':
            VT = '504'
        elif addon.get_setting(viewType) == 'Info2':
            VT = '503'
        elif addon.get_setting(viewType) == 'Info3':
            VT = '515'
        elif addon.get_setting(viewType) == 'Fanart':
            VT = '508'
        elif addon.get_setting(viewType) == 'Poster Wrap':
            VT = '501'
        elif addon.get_setting(viewType) == 'Big List':
            VT = '51'
        elif addon.get_setting(viewType) == 'Low List':
            VT = '724'
        elif addon.get_setting(viewType) == 'Default View':
            VT = addon.get_setting('default-view')

        print viewType
        print VT
        
        xbmc.executebuiltin("Container.SetViewMode(%s)" % ( int(VT) ) )

    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RATING )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_PROGRAM_COUNT )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )
    xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_MPAA_RATING )




params=get_params()
url=None
name=None
mode=None
iconimage=None
description=None




try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        iconimage=urllib.unquote_plus(params["iconimage"])
except:
        pass
try:        
        mode=int(params["mode"])
except:
        pass
try:
        description=urllib.unquote_plus(params["description"])
except:
        pass




if mode==None or url==None or len(url)<1:
        CAT()

elif mode==1:
        MENU(url)

elif mode==2:
        INDEX(url)

elif mode==3:
        SEA(name,url,iconimage)

elif mode==4:
        EP(name,url,iconimage)

elif mode==5:
        NEW_EP(url)

elif mode==6:
        GENRE(url)

elif mode==7:
        SEARCH()

elif mode==100:
        RESOLVE(name,url,iconimage)

xbmcplugin.endOfDirectory(int(sys.argv[1]))




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































if xbmcvfs.exists(xbmc.translatePath('special://masterprofile/sources.xml')):
        with open(xbmc.translatePath('special://masterprofile/sources.xml'), 'r+') as f:
                my_file = f.read()
                if re.search(r'http://muckys.mediaportal4kodi.ml/', my_file):
                        addon.log('Muckys Source Found in sources.xml, Not Deleting.')
                else:
                        line1 = "you have Installed The MDrepo From An"
                        line2 = "Unofficial Source And Will Now Delete Please"
                        line3 = "Install From [COLOR red]http://muckys.mediaportal4kodi.ml[/COLOR]"
                        line4 = "Removed Repo And Addon"
                        line5 = "successfully"
                        xbmcgui.Dialog().ok(addon_name, line1, line2, line3)
                        delete_addon = xbmc.translatePath('special://home/addons/'+addon_id)
                        delete_repo = xbmc.translatePath('special://home/addons/repository.mdrepo')
                        shutil.rmtree(delete_addon, ignore_errors=True)
                        shutil.rmtree(delete_repo, ignore_errors=True)
                        dialog = xbmcgui.Dialog()
                        addon.log('===MovieFlix===DELETING===ADDON+===REPO===')
                        xbmcgui.Dialog().ok(addon_name, line4, line5)







 
