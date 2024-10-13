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

    def onAVStarted(self):
        xbmc.log('skipintro: onAVStarted method called', xbmc.LOGINFO)
        if not self.bookmarks_checked:
            self.check_for_intro_chapter()

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
            chapter_count = int(xbmc.getInfoLabel('Player.ChapterCount'))
            xbmc.log(f'skipintro: Chapter count: {chapter_count}', xbmc.LOGDEBUG)
            
            chapters = []
            for i in range(1, chapter_count + 1):
                chapter_name = xbmc.getInfoLabel(f'Player.ChapterName({i})')
                chapter_time = xbmc.getInfoLabel(f'Player.ChapterTime({i})')
                
                # Convert chapter time to seconds
                time_parts = chapter_time.split(':')
                seconds = sum(int(x) * 60 ** i for i, x in enumerate(reversed(time_parts)))
                
                xbmc.log(f'skipintro: Chapter {i}: Name: {chapter_name}, Time: {seconds}', xbmc.LOGDEBUG)
                chapters.append({'name': chapter_name, 'time': seconds})
            
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
