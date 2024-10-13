import xbmc # type: ignore
import xbmcgui # type: ignore
import xbmcaddon # type: ignore
import re
import os
import json

# Log statement to verify script execution and capture import errors
try:
    xbmc.log('skipintro: default.py script loaded', xbmc.LOGDEBUG)
except Exception as e:
    xbmc.log('skipintro: Error during script loading: {}'.format(e), xbmc.LOGERROR)

addon = xbmcaddon.Addon()

class SkipIntroPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.intro_bookmark = None
        self.bookmarks_checked = False
        self.default_skip_checked = False

        # Read settings from Kodi configuration with error handling
        try:
            self.default_delay = int(addon.getSetting('default_delay'))
        except ValueError:
            self.default_delay = 60  # Default value if setting is not properly set
            xbmc.log('skipintro: Error reading default_delay setting. Using default value: 60', xbmc.LOGWARNING)

        try:
            self.skip_duration = int(addon.getSetting('skip_duration'))
        except ValueError:
            self.skip_duration = 30  # Default value if setting is not properly set
            xbmc.log('skipintro: Error reading skip_duration setting. Using default value: 30', xbmc.LOGWARNING)

        xbmc.log('skipintro: Initialized with default_delay: {}, skip_duration: {}'.format(self.default_delay, self.skip_duration), xbmc.LOGDEBUG)

    def testRpc(self):
        xbmc.log('skipintro: Starting testRpc function', xbmc.LOGDEBUG)
        try:
            # Get the JSON-RPC service
            jsonrpc = xbmc.executeJSONRPC
            xbmc.log('skipintro: JSON-RPC service obtained', xbmc.LOGDEBUG)

            # Get the currently playing item
            result = jsonrpc('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}')
            xbmc.log(f'skipintro: GetActivePlayers result: {result}', xbmc.LOGDEBUG)
            players = json.loads(result)['result']
            if not players:
                xbmc.log('skipintro: No active players found', xbmc.LOGDEBUG)
                return

            player_id = players[0]['playerid']
            xbmc.log(f'skipintro: player_id: {player_id}', xbmc.LOGDEBUG)

            item_info = json.loads(jsonrpc(json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetItem",
                "params": {"playerid": player_id, "properties": ["file"]},
                "id": 1
            })))
            xbmc.log(f'skipintro: item_info: {item_info}', xbmc.LOGDEBUG)
            filename = item_info['result']['item']['file']
            xbmc.log(f'skipintro: filename: {filename}', xbmc.LOGDEBUG)

            # Get chapter information
            chapter_info = json.loads(jsonrpc(json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetChapters",
                "params": {"playerid": player_id, "properties": ["name", "title", "time"]},
                "id": 1
            })))
            xbmc.log(f'skipintro: chapter_info: {chapter_info}', xbmc.LOGDEBUG)

            # Print chapter names
            if 'result' in chapter_info and 'chapters' in chapter_info['result']:
                for chapter in chapter_info['result']['chapters']:
                    name = chapter.get('name') or chapter.get('title') or "Unnamed Chapter"
                    time = chapter['time'] / 1000  # Convert milliseconds to seconds
                    xbmc.log(f'skipintro: Chapter: Name: {name}, Time: {time}', xbmc.LOGDEBUG)
            else:
                xbmc.log("skipintro: No chapters found for this video.", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f'skipintro: Error in testRpc: {str(e)}', xbmc.LOGERROR)
            
    def onAVStarted(self):
        xbmc.log('skipintro: AV started', xbmc.LOGDEBUG)
        if not self.bookmarks_checked:
            self.check_for_intro_chapter()
        
        xbmc.log('skipintro: testing rpc', xbmc.LOGDEBUG)
        self.testRpc()

    # ... [rest of the class remains unchanged]

if __name__ == '__main__':
    xbmc.log('skipintro: Starting SkipIntroPlayer', xbmc.LOGDEBUG)
    player = SkipIntroPlayer()
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        if xbmc.Player().isPlaying() and not player.bookmarks_checked:
            player.check_for_intro_chapter()
        monitor.waitForAbort(5)
