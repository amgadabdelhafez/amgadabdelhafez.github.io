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
        xbmc.log('skipintro: onAVStarted method called', xbmc.LOGINFO)
        if not self.bookmarks_checked:
            self.check_for_intro_chapter()
        
        xbmc.log('skipintro: testing rpc', xbmc.LOGDEBUG)
        self.testRpc()

    def check_for_intro_chapter(self):
        xbmc.log('skipintro: Checking for intro chapter', xbmc.LOGDEBUG)
        playing_file = self.getPlayingFile()
        if not playing_file:
            xbmc.log('skipintro: No playing file detected', xbmc.LOGERROR)
            return

        # Retrieve chapters
        chapters = self.getChapters()
        if chapters:
            xbmc.log('skipintro: Found {} chapters'.format(len(chapters)), xbmc.LOGDEBUG)
            self.intro_bookmark = self.find_intro_chapter(chapters)
            if self.intro_bookmark:
                self.prompt_skip_intro()
            else:
                self.bookmarks_checked = True
        else:
            self.check_for_default_skip()

    def getChapters(self):
        xbmc.log('skipintro: Getting chapters', xbmc.LOGDEBUG)
        try:
            jsonrpc = xbmc.executeJSONRPC
            result = jsonrpc('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}')
            players = json.loads(result)['result']
            if not players:
                xbmc.log('skipintro: No active players found', xbmc.LOGDEBUG)
                return []

            player_id = players[0]['playerid']
            chapter_info = json.loads(jsonrpc(json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetChapters",
                "params": {"playerid": player_id, "properties": ["name", "title", "time"]},
                "id": 1
            })))
            
            chapters = []
            if 'result' in chapter_info and 'chapters' in chapter_info['result']:
                for chapter in chapter_info['result']['chapters']:
                    name = chapter.get('name') or chapter.get('title') or f"Chapter {len(chapters) + 1}"
                    time = chapter['time'] / 1000  # Convert milliseconds to seconds
                    xbmc.log(f'skipintro: Chapter: Name: {name}, Time: {time}', xbmc.LOGDEBUG)
                    chapters.append({'name': name, 'time': time})
            else:
                xbmc.log("skipintro: No chapters found for this video.", xbmc.LOGDEBUG)
            
            return chapters
        except Exception as e:
            xbmc.log(f'skipintro: Error in getChapters: {str(e)}', xbmc.LOGERROR)
            return []

    def find_intro_chapter(self, chapters):
        xbmc.log('skipintro: Searching for intro chapter', xbmc.LOGDEBUG)
        for chapter in chapters:
            xbmc.log('skipintro: Checking chapter: {} at {} seconds'.format(chapter['name'], chapter['time']), xbmc.LOGDEBUG)
            if 'intro end' in chapter['name'].lower():
                xbmc.log('skipintro: Intro end chapter found at {} seconds'.format(chapter['time']), xbmc.LOGINFO)
                return chapter['time']
        xbmc.log('skipintro: No intro end chapter found', xbmc.LOGINFO)
        return None

    def check_for_default_skip(self):
        xbmc.log('skipintro: Checking for default skip', xbmc.LOGDEBUG)
        if self.default_skip_checked:
            return

        current_time = self.getTime()
        xbmc.log('skipintro: Current time: {}'.format(current_time), xbmc.LOGDEBUG)
        if current_time >= self.default_delay:
            self.intro_bookmark = current_time + self.skip_duration
            self.prompt_skip_intro()

        self.default_skip_checked = True

    def prompt_skip_intro(self):
        xbmc.log('skipintro: Prompting user to skip intro', xbmc.LOGDEBUG)
        skip_intro = xbmcgui.Dialog().yesno('Skip Intro?', 'Do you want to skip the intro?')
        if skip_intro:
            self.skip_to_intro_end()

    def skip_to_intro_end(self):
        if self.intro_bookmark:
            xbmc.log('skipintro: Skipping intro to {} seconds'.format(self.intro_bookmark), xbmc.LOGINFO)
            self.seekTime(self.intro_bookmark)
        else:
            xbmc.log('skipintro: No intro bookmark set to skip', xbmc.LOGERROR)

if __name__ == '__main__':
    xbmc.log('skipintro: Script execution started', xbmc.LOGINFO)
    player = SkipIntroPlayer()
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        if xbmc.Player().isPlaying() and not player.bookmarks_checked:
            player.check_for_intro_chapter()
        monitor.waitForAbort(5)
