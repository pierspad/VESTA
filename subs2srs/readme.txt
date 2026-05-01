subs2srs Release Notes
--------------------------------------------------------------------------------

What is subs2srs?
-----------------
subs2srs allows you to create import files for Anki or other Spaced Repetition
Systems (SRS) based on your favorite foreign language movies and TV shows to aid
in the language learning process.


How to Install and Launch (Windows Users):
------------------------------------------
1) Make sure that you have .Net Framework Version 3.5 installed (you probably
   already do). If not, you can get it through Windows update or via the following
   link: http://www.microsoft.com/download/en/details.aspx?id=21

2) Unzip subs2srs.

3) In the unzipped directory, simply double-click subs2srs.exe to launch subs2srs.


How to Install and Launch (Linux Users):
----------------------------------------
1) Install Wine 1.3 with the following command:
   sudo apt-get install wine1.3

2) Install .Net 3.5 with the following command:
   bash winetricks dotnet35

3) Unzip subs2srs.

4) In the unzipped directory, either double-click on subs2srs.exe or
   type "wine subs2srs.exe".


Offical Project Home:
---------------------
http://sourceforge.net/projects/subs2srs/
(if you didn't download subs2srs here, BEWARE!)


Feedback Thread:
----------------
Post comments/suggestions/bugs/questions here:
http://forum.koohii.com/viewtopic.php?id=2643&p=1


Contact:
--------
Christopher Brochtrup
cb4960@gmail.com


Acknowledgements:
-----------------
ffmpeg           - Video/audio/snapshot processing
Subtitle Creator - Original vobsub code
TagLib#          - MP3 tagging library
mp3gain          - Used to normalize MP3 files

--------------------------------------------------------------------------------

Version History:
----------------
[Version 27.0 (02-15-2013)]
- ADDED: Subs Re-Timer tool.

[Version 26.5 (11-22-2012)]
- ADDED: Support for larger Blu-ray vobsubs.

[Version 26.4 (11-10-2012)]
- ADDED: Anki 2 deck templates.
- ADDED: Anki 2 import instructions to the help file.

[Version 26.3 (09-16-2012)]
- CHANGE: Upgraded ffmpeg to zeranoe git-8bdba0b (120914) build and changed
          code to add support for the new CLI.

[Version 26.2 (09-15-2012)]
- FIXED: .trs parser ignored the last line of dialog.
- FIXED: .srt parser ignored the last line of dialog unless file ended with
         2 newlines.

[Version 26.1 (09-01-2012)]
- FIXED: Context lines consisted of only lines that were not pruned.

[Version 26.0 (06-02-2012)]
- ADDED: Option to normalize audio clips.

[Version 25.0 (03-31-2012)]
- ADDED: Subtitle pairing algorithm now considers both start and end times.
- ADDED: 'Remove lines with no obvious counterpart' option.
- ADDED: 'Remove styled lines (only affect .ass subtitles)' option.
- ADDED: Added the Preference dialog
- ADDED: Added option to independently shift subtitle timings.
- ADDED: Added logging.
- ADDED: Minor interface tweaks (help section colors, label renaming, tooltips,
         Snapshot Preview dialog closes when clicked, etc.)
- FIXED: Issue where vobsubs timings shifted after regenerating preview.
- FIXED: Subtitle stream not loading correctly from .s2s file.
- CHANGE: Dropped linux support and removed mono-specific code.
- CHANGE: Renamed settings.txt to preferences.txt.
- CHANGE: Removed following preferences:
          main_window_width_mono, main_window_height_mono,
          default_preview_east_asain_font, audio_player, audio_player_args,
          fix_mismatched_lines, ffmpeg_version
- CHANGE: Cleaned up the subtitle pairing code.
- CHANGE: Added comments for most methods.

[Version 24.0 (10-15-2011)]
- ADDED: More detail to the progress dialog when audio or video is being
         processed. Replaces the need for the ffmpeg DOS window to appear.
- ADDED: Number of minutes processing took to complete to the popup that
         appears when processing is finished.
- ADDED: Colored text to better show which fields are required and which
         are optional.
- CHANGE: Upgraded ffmpeg to zeranoe git-f884ef0 0.8.5 111013 build and changed
          code to add support for the new CLI.
- CHANGE: Moved the subtitle encoding option from the advanced subtitle dialog to
          the main interface. Either the encoding option or the vobsub stream
          option will appear depending on subtitle type.
- CHANGE: Replaced force_legacy_ffmpeg with ffmpeg_version.
- CHANGE: Removed Pre-Time Shift (too complicated).
- CHANGE: Post-Time Shift is now called Shift Timings.
- CHANGE: The Advanced Subtitle Options... button is now a link.
- CHANGE: In the documentation, replaced Windows XP screenshots with prettier
          Windows 7 screenshots.

[Version 23.3 (07-10-2011)]
- FIXED: Extension was missing from the video clips field on the .tsv file.

[Version 23.2 (05-14-2011)]
- FIXED: Added GUID to temp file names to allow multiple instances of subs2srs
         to run simultaneously.

[Version 23.1 (03-20-2011)]
- FIXED: Removed Advanced Video Clip Options dialog. Both h.264 and .mp4 screw
         up the timing of cut video files (though reducing the keyframe interval
         helps, .mp4 files still don't cut on time). These formats are now only
         used for iPod support.

[Version 23.0 (03-12-2011)]
- ADDED: Advanced Video Clip Options dialog.

[Version 22.0 (03-04-2011)]
- ADDED: Transcriber (.trs) support
- ADDED: audio support for non-mp3 formats
- ADDED: option to choose Subs1 and Subs2 encoding

[Version 21.2 (01-17-2011)]
- CHANGE: Max leading/trailing context options changed from 2 to 9
- CHANGE: upgraded Anki templates to v1.2
- CHANGE: upgraded ffmpeg to version 26397

[Version 21.1 (11-12-2010)]
- ADDED: support for new 0.6.1 ffmpeg
- ADDED: force_legacy_ffmpeg to settings.txt to support pre-0.6.1 ffmpeg
- ADDED: audio_player and audio_player_args to settings.txt
- CHANGE: upgraded ffmpeg to version 25726 (0.6.1 branch)

[Version 21.0 (09-04-2010)]
- ADDED: preview should now work on mono platforms (at least on linux)
- ADDED: default_preview_east_asain_font to settings.txt
- CHANGE: nudged some of the widgets a few pixels here and there
- FIXED: garbled vobsubs on mono platforms

[Version 20.5 (08-27-2010)]
- ADDED: ${cr} and ${lf} tokens to settings.txt
- CHANGE: removed the ${newline} token from settings.txt
- FIXED: newlines in the id3 lyrics tag (was [LF], now [CR][LF])

[Version 20.4 (08-22-2010)]
- ADDED: audio_id3_lyrics to settings.txt

[Version 20.3 (07-26-2010)]
- FIXED: "Win32Exception: The system cannot find the drive specified" exception

[Version 20.2 (07-24-2010)]
- FIXED: extract audio from media dialog creating empty files
- FIXED: couldn't use certain tags in the extract audio from media settings

[Version 20.1 (07-23-2010)]
- ADDED: main_window_[width|height] to settings.txt
- ADDED: default_file_browser_start_dir to settings.txt
- ADDED: srs_subs[12]_format to settings.txt
- ADDED: srs_vobsub_filename_[prefix|suffix] to settings.txt
- ADDED: srs_filename_format to settings.txt
- ADDED: srs_delimiter to settings.txt
- ADDED: added ${tab} tag to settings.txt
- ADDED: "none" may now be specified for strings in settings.txt
- ADDED: tag and sequence marker will not be added to import file when blank
- ADDED: the last dir used is passed across the dialogs
- CHANGE: in dueling subtitles dialog, moved nameing section to the bottom
- FIXED: "check actors" feature didn't work in certain cases
- FIXED: all of the trailing snapshots were the same
- FIXED: typo in the default srs_sequence_marker_format setting

[Version 20.0 (07-19-2010)]
- ADDED: settings.txt file to control various settings and output formats
- ADDED: ability to add lyrics to audio in the extract audio from media dialog
- ADDED: snapshot and video clip dimensions chooser dialog
- ADDED: setting to reencode bad audio files before splitting them
- CHANGE: batch processing now done with wildcards not seperate directories
- CHANGE: many filename formats changed. some other defaults (bitrates) changed.
- CHANGE: fix mismatched lines was moved to settings.txt
- CHANGE: top, left, and right crop were removed
- CHANGE: video_preview.txt replaced with 2 settings in settings.txt

[Version 19.3 (06-18-2010)]
- ADDED: better support for 5.1 audio
- CHANGE: upgraded ffmpeg to version 23642

[Version 19.2 (06-05-2010)]
- ADDED: in audio extract tool, span
- ADDED: in audio extract tool, stream
- ADDED: audio extract tool fields are now populated automatically
- CHANGE: in prune, increase max limits
- CHANGE: span start time now defaults to 0:01:30

[Version 19.1 (05-29-2010)]
- ADDED: command line arg to specify a .s2s file to use on startup
- ADDED: hidden video preview option
- FIXED: open and new menu options will now close the preview dialog
- FIXED: parsing of ffmpeg output to determine video dimension

[Version 19.0 (05-04-2010)]
- ADDED: in preview, distinction between active and inactive lines
- ADDED: in preview, all episodes can now be previewed, not just the first
- ADDED: in preview, find box
- ADDED: in preview, ability to edit the subs1 and subs2 text
- ADDED: in preview, statistics box
- ADDED: in preview, snapshot preview checkbox
- ADDED: in preview, go! button
- ADDED: lyric (.lrc) support
- CHANGE: .srt parser now removes the italic, bold, and underline style tags
- FIXED: remove comment line from the Anki import file
- FIXED: .ass/.ssa parser now replaces "\N" style newlines with a space
- FIXED: tab orders

[Version 18.3 (02-06-2010)]
- CHANGE: due to unresolved issues, removed preview button for linux/mac users
- CHANGE: upgraded ffmpeg to version 21566
- FIXED: the "check actors" feature gave a null pointer exception

[Version 18.2 (02-05-2010)]
- FIXED: .ass/.ssa parser is more robost and no longer assumes format and order
- FIXED: removed .ass style line breaks from the quick reference file
- FIXED: color dialog color incorrect on subtitle style dialog

[Version 18.1 (01-31-2010)]
- ADDED: quick reference .txt file option on dueling subtitles dialog
- FIXED: font textbox not being updated on the subtitle style dialog

[Version 18.0 (01-30-2010)]
- ADDED: dueling subtitles feature
- CHANGE: force output file to utf-8 instead of using default
- FIXED: remove any lines where end time is less than or equal to start time

[Version 17.0 (01-03-2010)]
- ADDED: preview feature (text, snapshot, and audio)
- ADDED: option to select which audio stream to use from the video file
- ADDED: option to exclude lines longer than X milliseconds
- ADDED: context formatting (include/exclude audio, snapshot, video)
- ADDED: remove newline character ("\N") and embedded styling from .ass source
- ADDED: comment to beginning of .tsv file describing the import format
- CHANGE: vobsub stream is now selected via drop down on the main interface
- CHANGE: changed "First Enumeration" to "First Episode"

[Version 16.0 (10-10-2009)]
- ADDED: linux/mac support via mono
- ADDED: id3 lyrics tag now includes the corresponding line of dialog
- CHANGE: using ffmpeg instead of mp3splt to split audio (for linux/mac support)
- CHANGE: using TagLib# instead of mp3splt to apply id3 tags to the audio

[Version 15.0 (10-03-2009)]
- ADDED: "Fix mismatched lines" option
- ADDED: snapshot crop
- ADDED: video crop
- ADDED: pre-Time Shift option
- ADDED: option to exclude lines not meeting a minimum number of milliseconds
- ADDED: allow user to reduce size of interface (scroll bars will be used)
- CHANGE: Time Shift is now called Post-Time Shift

[Version 14.0 (09-02-2009)]
- ADDED: sequence marker

[Version 13.0 (08-29-2009)]
- ADDED: context options
- ADDED: interface tweaks (more spinners and dropdowns)

[Version 12.1 (05-30-2009)]
- FIXED: vobsubs could not be used for both Subs1 and Subs2

[Version 12.0 (05-24-2009)]
- ADDED: removed dependence on Avisynth (now using ffmpeg)
- ADDED: frame rate field removed
- ADDED: interfaced tweaks

[Version 11.2.1 (05-03-2009)]
- FIXED: user could enter invalid input into grayed-out fields

[Version 11.1 (05-03-2009)]
- ADDED: validate frame rate auto-detect

[Version 11.0 (05-03-2009)]
- ADDED: video clip generation
- ADDED: option to enter audio clip bitrate
- ADDED: updated documention which step-by-step guide
- ADDED: auto-detection of framerate
- ADDED: more visual form validation
- ADDED: interface tweaks

[Version 10.3 (03-20-2009)]
- FIXED: compensate for mp3splt adding .mp3 extention

[Version 10.2 (03-18-2009)]
- FIXED: snapshot of every frame when subtitle exists on first frame (again)

[Version 10.1 (03-15-2009)]
- ADDED: now works with mp3splt 2.2.3
- ADDED: "extract audio from video" tool now used mp3splt to cut mp3 files
- ADDED: ID3v2 tags to all mp3 files

[Version 10.0 (03-14-2009)]
- FIXED: vobsub processing didn't obey the time span
- ADDED: optimizations to automatic audio extraction

[Version 9.0 (03-06-2009)]
- ADDED: optimizations to snapshot processing
- ADDED: ignore "hidden" files

[Version 8.0 (03-01-2009)]
- ADDED: option to only process lines in the specified time span

[Version 7.1 (02-28-2009)]
- FIXED: snapshot of every frame when subtitle exists on first frame

[Version 7.0 (02-15-2009)]
- ADDED: vobsub (.idx/.sub) support
- ADDED: the "extract audio from video" tool

[Version 6.0 (02-08-2009)]
- ADDED: option to automatically extract audio track from video

[Version 5.0 (02-06-2009)]
- ADDED: option to select which actors/characters to process when using
         .ass/.ssa files
- ADDED: option to form words or phrases to include/exclude from processing
- ADDED: option to shift timings
- ADDED: option to only process lines that contain at least one kanji

[Version 4.1 (02-03-2009)]
- ADDED: forced Avisynth to use the provided framerate
- ADDED: additional validation code

[Version 4.0 (02-03-2009)]
- FIXED: globalization issue with frame rate
- ADDED: multiline dialog support for .srt parser
- ADDED: option to pad timings
- ADDED: folder browser remembers last folder

[Version 3.0 (02-01-2009)]
- ADDED: option to remove duplicate lines

[Version 2.0 (01-31-2009)]
- ADDED: easier to use interface

[Version 1.0 (12-15-2008)]
- initial version


