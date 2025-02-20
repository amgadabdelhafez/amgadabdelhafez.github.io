import xbmc # type: ignore
import xbmcgui # type: ignore
import xbmcaddon # type: ignore
import re
import os
import time
import json
from typing import List, Dict, Optional

addon = xbmcaddon.Addon()

class SkipIntroDialog(xbmcgui.WindowDialog):
    def __init__(self):
        super(SkipIntroDialog, self).__init__()
        # Get screen dimensions
        self.screen_width = self.getWidth()
        self.screen_height = self.getHeight()
        
        # Calculate button dimensions and position
        button_width = int(self.screen_width * 0.2)  # 20% of screen width
        button_height = int(self.screen_height * 0.1)  # 10% of screen height
        button_x = self.screen_width - button_width - 50  # 50 pixels from right edge
        button_y = self.screen_height - button_height - 100  # 100 pixels from bottom edge (moved up)
        
        # Add a background for the button
        self.background = xbmcgui.ControlImage(button_x - 10, button_y - 10, 
                                               button_width + 20, button_height + 20, 
                                               filename='', colorDiffuse='0xAA000000')
        self.addControl(self.background)
        
        # Add the skip intro button
        self.skip_button = xbmcgui.ControlButton(button_x, button_y, button_width, button_height, 
                                                 "Skip Intro", 
                                                 focusTexture='', noFocusTexture='', 
                                                 alignment=2 | 4, font='font14', 
                                                 textColor='0xFFFFFFFF')
        self.addControl(self.skip_button)
        self.setFocus(self.skip_button)
        
        self.button_pressed = False

    def onAction(self, action):
        if action.getId() in [xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU]:
            self.close()
        elif action.getId() in [xbmcgui.ACTION_SELECT_ITEM, xbmcgui.ACTION_MOUSE_LEFT_CLICK]:
            self.button_pressed = True
            self.close()

    def onControl(self, control):
        if control == self.skip_button:
            self.button_pressed = True
            self.close()

class SkipIntroPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.intro_bookmark: Optional[float] = None
        self.chapters: Optional[List[Dict[str, float]]] = None
        self.current_chapter: int = 0
        self.skip_dialog: Optional[SkipIntroDialog] = None
        self.dialog_start_time: float = 0
        self.has_skipped: bool = False
        self.using_default_skip: bool = False
        self.max_dialog_duration: float = 60.0  # Maximum duration for skip intro dialog in seconds

        self.default_delay = self._get_setting_int('default_delay', 60)
        self.skip_duration = self._get_setting_int('skip_duration', 30)
        self.skip_to_chapter = self._get_setting_int('skip_to_chapter', 2)
        self.seconds_before_skip = self._get_setting_int('seconds_before_skip', 5)
        self.chapter_diff_threshold = self._get_setting_int('chapter_diff_threshold', 15)
        self.dialog_display_duration = self._get_setting_int('dialog_display_duration', 5)
        self.skip_by_default = addon.getSettingBool('skip_by_default')
        self.use_default_skip_fallback = addon.getSettingBool('use_default_skip_fallback')

        xbmc.log(f'skipintro: Initialized with default_delay: {self.default_delay}, skip_duration: {self.skip_duration}, '
                 f'skip_by_default: {self.skip_by_default}, use_default_skip_fallback: {self.use_default_skip_fallback}, '
                 f'skip_to_chapter: {self.skip_to_chapter}, seconds_before_skip: {self.seconds_before_skip}, '
                 f'chapter_diff_threshold: {self.chapter_diff_threshold}, dialog_display_duration: {self.dialog_display_duration}', 
                 xbmc.LOGDEBUG)

    def _get_setting_int(self, setting: str, default: int) -> int:
        try:
            return int(addon.getSetting(setting))
        except ValueError:
            xbmc.log(f'skipintro: Error reading {setting} setting. Using default value: {default}', xbmc.LOGWARNING)
            return default

    def onAVStarted(self):
        xbmc.log('skipintro: AV started', xbmc.LOGDEBUG)
        self.chapters = self.getChapters()
        self.has_skipped = False
        self.current_chapter = 0
        self.using_default_skip = False
        if self.chapters:
            xbmc.log(f'skipintro: Found {len(self.chapters)} chapters', xbmc.LOGDEBUG)
            self.intro_bookmark = self.find_intro_chapter(self.chapters)
        elif self.use_default_skip_fallback:
            xbmc.log('skipintro: No chapters found. Using default skip as fallback.', xbmc.LOGINFO)
            self.using_default_skip = True
            self.intro_bookmark = self.default_delay

    def getChapters(self) -> Optional[List[Dict[str, float]]]:
        chapter_count = int(xbmc.getInfoLabel('Player.ChapterCount'))
        xbmc.log(f'skipintro: Total chapters found: {chapter_count}', xbmc.LOGDEBUG)

        if chapter_count == 0:
            xbmc.log('skipintro: No chapters found in the video.', xbmc.LOGINFO)
            return None

        raw_chapters = xbmc.getInfoLabel('Player.Chapters')
        xbmc.log(f'skipintro: Raw Chapters found: {raw_chapters}', xbmc.LOGDEBUG)

        if not raw_chapters:
            xbmc.log('skipintro: Raw chapters string is empty.', xbmc.LOGINFO)
            return None

        try:
            chapter_times = [float(time) for time in raw_chapters.split(',') if time.strip()]
        except ValueError as e:
            xbmc.log(f'skipintro: Error parsing chapter times: {str(e)}', xbmc.LOGERROR)
            return None

        if not chapter_times:
            xbmc.log('skipintro: No valid chapter times found.', xbmc.LOGINFO)
            return None

        start_times = chapter_times[::2] + [chapter_times[-1]]
        
        chapters = [{'name': f"Chapter {i + 1}", 'start': start_time} for i, start_time in enumerate(start_times)]

        for chapter in chapters:
            xbmc.log(f'skipintro: {chapter["name"]} - Start: {chapter["start"]:.2f}', xbmc.LOGDEBUG)

        return chapters

    def find_intro_chapter(self, chapters: List[Dict[str, float]]) -> Optional[float]:
        if len(chapters) >= 3 and self.skip_to_chapter == 2:
            ch2_start = chapters[1]['start']
            ch3_start = chapters[2]['start']
            total_duration = self.getTotalTime()
            
            ch2_time = (ch2_start / 100) * total_duration
            ch3_time = (ch3_start / 100) * total_duration
            
            time_diff = ch3_time - ch2_time
            
            if time_diff < self.chapter_diff_threshold:
                xbmc.log(f'skipintro: Difference between Ch2 and Ch3 is less than {self.chapter_diff_threshold} seconds. Skipping to Ch3.', xbmc.LOGINFO)
                return ch3_start  # Return the exact start time of chapter 3
            else:
                xbmc.log('skipintro: Using default Ch2 for skipping.', xbmc.LOGINFO)
                return ch2_start
        elif len(chapters) >= self.skip_to_chapter:
            chapter_start = chapters[self.skip_to_chapter - 1]['start']
            xbmc.log(f'skipintro: Chapter {self.skip_to_chapter} starts at {chapter_start:.2f}%', xbmc.LOGINFO)
            return chapter_start
        else:
            xbmc.log('skipintro: Not enough chapters found. Cannot skip intro.', xbmc.LOGINFO)
            return None

    def check_chapter_and_prompt(self):
        if self.has_skipped:
            return

        total_duration = self.getTotalTime()
        current_time = self.getTime()

        if total_duration <= 0:
            xbmc.log('skipintro: Total duration is zero or negative. Skipping percentage calculation.', xbmc.LOGWARNING)
            return

        try:
            current_percentage = (current_time / total_duration) * 100
        except ZeroDivisionError:
            xbmc.log('skipintro: Error calculating current percentage. Total duration is zero.', xbmc.LOGERROR)
            return

        if self.intro_bookmark is not None and (self.intro_bookmark > 5):
            xbmc.log('skipintro: Skip point is after 5% of video duration. Skipping disabled.', xbmc.LOGINFO)
            return

        if self.using_default_skip:
            if current_time >= self.default_delay - self.seconds_before_skip:
                if self.skip_by_default:
                    self.skip_to_intro_end()
                elif not self.skip_dialog:
                    self.show_skip_dialog()
        elif self.chapters:
            previous_chapter = self.current_chapter
            for i, chapter in enumerate(self.chapters):
                if current_percentage >= chapter['start']:
                    self.current_chapter = i + 1

            if self.current_chapter != previous_chapter:
                xbmc.log(f'skipintro: Current chapter: {self.current_chapter}', xbmc.LOGDEBUG)

            # Show dialog at the start of chapter 2
            if self.current_chapter == 2 and not self.skip_dialog:
                self.show_skip_dialog()
            
            # Remove dialog at the start of chapter 3, but ensure it's shown for at least dialog_display_duration
            elif self.current_chapter == 3:
                if self.skip_dialog:
                    current_time = time.time()
                    if current_time - self.dialog_start_time >= self.dialog_display_duration:
                        self.remove_skip_dialog()
                else:
                    self.remove_skip_dialog()

    def show_skip_dialog(self):
        xbmc.log('skipintro: Showing skip intro dialog', xbmc.LOGDEBUG)
        self.skip_dialog = SkipIntroDialog()
        self.skip_dialog.show()
        self.dialog_start_time = time.time()

    def remove_skip_dialog(self):
        if self.skip_dialog:
            self.skip_dialog.close()
            self.skip_dialog = None
            xbmc.log('skipintro: Removed skip intro dialog', xbmc.LOGDEBUG)

    def skip_to_intro_end(self):
        if self.intro_bookmark is not None and not self.has_skipped:
            if self.using_default_skip:
                skip_to = self.intro_bookmark + self.skip_duration
            else:
                skip_to = (self.intro_bookmark / 100) * self.getTotalTime()
            xbmc.log(f'skipintro: Skipping intro to {skip_to:.2f} seconds', xbmc.LOGINFO)
            self.seekTime(skip_to)
            self.remove_skip_dialog()
            self.has_skipped = True
        else:
            xbmc.log('skipintro: No intro bookmark set to skip or already skipped', xbmc.LOGWARNING)

if __name__ == '__main__':
    xbmc.log('skipintro: Starting SkipIntroPlayer', xbmc.LOGDEBUG)
    skip_intro_player = SkipIntroPlayer()
    monitor = xbmc.Monitor()

    try:
        while not monitor.abortRequested():
            if skip_intro_player.isPlaying():
                skip_intro_player.check_chapter_and_prompt()
                
                if skip_intro_player.skip_dialog:
                    current_time = time.time()
                    if current_time - skip_intro_player.dialog_start_time > skip_intro_player.max_dialog_duration:
                        skip_intro_player.remove_skip_dialog()
                    elif skip_intro_player.skip_dialog.button_pressed:
                        skip_intro_player.skip_to_intro_end()
            
            xbmc.sleep(1000)  # Check every 1 second for less CPU usage
    except Exception as e:
        xbmc.log(f'skipintro: Unexpected error: {str(e)}', xbmc.LOGERROR)

    xbmc.log('skipintro: SkipIntroPlayer stopped', xbmc.LOGDEBUG)
