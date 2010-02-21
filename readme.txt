ARCTool v0.2b 1/4/10
By tpw_rules

ARCTool is a Python script that can extract the multitude of different formats found in .arc game files. It has support for Yaz0, U8, and RARC, which are all that I have found.
The inspiration for this tool came about when I wrote a RARC extractor and realized that all the files I wanted to extract were U8, but they still had the arc extension.
I have tested it on Mac OS X 10.5.8 with Python 2.5 and 2.6. It should work on other platforms (Windows and Linux) provided Python is properly installed.
I have confirmed Yaz0 and U8 support to be 100% working.
If you have any trouble with it, message me on IRC (nick is tpw_rules) or leave a note on the talk page.

Usage: python ARCTool.py [-q] [-o <output>] <inputfile> [inputfile2] ... [inputfileN]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -o FILE/DIR, --output=FILE/DIR
                        write output to FILE/DIR. If you are extracting
                        multiple archives, all of them will be put in this
                        dir.
  -q, --quiet           don't print anything (except errors)

Requirements:
Python 2.5 or higher (not Python 3.x however). Get Python for your OS at http://python.org/download/

THANKS TO

#python on freenode for helping me with some stupid mistakes.
#wiidev for, again, helping me with stupid mistakes (and not so stupid ones).
YAGCD and the WiiBrew wiki for documentation and example code on the various formats.
Magicus for parse-u8.c which I used for testing.
Everybody else I forgot.
