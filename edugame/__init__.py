"""EduGame Kit: make one game zip that works in Kolibri, Moodle, RACHEL, Sugarizer and Kiwix.

The kit is the save helper (runtime/edugame.js), which every game loads, and the
build tool (``edugame``, in cli.py), which turns a game folder into the files
each platform needs. Standard library only.
"""
__version__ = "0.1.0"

#: The version of the edugame.json format this kit reads.
FORMAT = 1
