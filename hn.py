#!/usr/bin/env python3

'''
Copyright (c) 2024 Yannis Charalambidis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import requests
from bs4 import BeautifulSoup
import curses
from enum import Enum
import os
from datetime import datetime
from pathlib import Path
import argparse

HN_URL = "https://news.ycombinator.com/"


class State(Enum):
    UNSELECTED = 1
    SITE = 2
    COMMENTS = 3


def check_time():
    """Check if the user already checked today"""

    now = datetime.now()

    file_path = Path("~/.hacker_news").expanduser()

    if not file_path.exists():
        with open(file_path, "w+") as f:
            f.write(now.strftime("%Y-%m-%d"))
        return True

    with open(file_path, "r+") as f:
        last = datetime.strptime(f.read().strip(), "%Y-%m-%d")
        if (now - last).days < 1:
            return False

        f.seek(0)
        f.write(now.strftime("%Y-%m-%d"))
        return True


def get_links():
    """Get the links from the page"""

    keys = "0123456789abcdefhilmnoprstuvwxyz"  # No g,j,k,q,

    response = requests.get(HN_URL)

    bs = BeautifulSoup(response.text, "html.parser")

    trs = bs.select_one("tr.athing").parent.select("tr")[:-1]

    # filter tr with class "spacer" or "morespace"
    trs = [tr for tr in trs if (tr.get("class") != ["spacer"]) and (
        tr.get("class") != ["morespace"])]

    data = {}

    it = iter(trs)
    key = iter(keys)

    while tr := next(it, None):
        titleline = tr.select_one("span.titleline a")
        tr2 = next(it)

        data[next(key)] = {"title": titleline.text,
                           "url": titleline["href"], "state": State.UNSELECTED, "item_path": tr2.select("a")[-1]['href']}

    return data


def menu(stdscr, data):
    """Display the menu"""

    pad = curses.newpad(len(data), 100)
    pad_pos = 0

    stdscr.refresh()

    while True:
        for i, key in enumerate(data.keys()):
            s = f" {key:2} - {data[key]['title']}"
            pad.addstr(i, 0, s, curses.color_pair(data[key]["state"].value))

        pad.refresh(pad_pos, 0, 0, 0, curses.LINES - 1,
                    curses.COLS - 1)

        c = stdscr.getch()

        # Quit
        if c == ord('q') or c == 10:  # 10 is enter
            break
        # Move up
        elif c == ord('k'):
            pad_pos = max(pad_pos - 1, 0)
        # Move down
        elif c == ord('j') or c == 32:  # 32 is space
            pad_pos += 1
            if pad_pos + curses.LINES > len(data):
                pad_pos = len(data) - curses.LINES
        # Move to top
        elif c == ord('g'):
            pad_pos = 0
        # Move to bottom
        elif c == ord('G'):
            pad_pos = len(data) - curses.LINES

        # Select item
        for key in data.keys():
            if c == ord(key):
                data[key]["state"] = {
                    State.UNSELECTED: State.SITE,
                    State.SITE: State.COMMENTS,
                    State.COMMENTS: State.UNSELECTED,
                }[data[key]["state"]]

    return data


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="Hacker News Daily", usage="%(prog)s [options]", add_help=True, prog="hn.py",
        epilog="""

Scraps the front page of Hacker News and let you choose which links to open in firefox.
Use the keys j/k/g/G/SPACE to navigate and press ENTER/q to open the links in firefox.
Select the links with the keys 0-9/a-z. A green link will open the site, a yellow one the comments.
The software can only be used once a day. It will save the last time you used it in ~/.hacker_news.

""", formatter_class=argparse.RawDescriptionHelpFormatter)
    args = argparser.parse_args()

    if not check_time():
        print("You already checked today")
        exit(0)

    # Setup curses
    stdscr = curses.initscr()
    stdscr.clear()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    # Setup colors
    curses.init_pair(State.UNSELECTED.value,
                     curses.COLOR_WHITE, -1)
    curses.init_pair(State.SITE.value, curses.COLOR_GREEN, -1)
    curses.init_pair(State.COMMENTS.value,
                     curses.COLOR_YELLOW, -1)

    # Scrap and choose links
    data = get_links()

    data = menu(stdscr, data)

    # Close curses
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()

    # Open links in firefox
    links = []

    for k in data.keys():
        if data[k]["state"] == State.SITE:
            if data[k]["url"] == data[k]["item_path"]:  # Post without link
                links.append(f"{HN_URL}{data[k]['item_path']}")
            else:
                links.append(data[k]["url"])
        elif data[k]["state"] == State.COMMENTS:
            links.append(f"{HN_URL}{data[k]['item_path']}")

    for link in links:
        os.system(f"firefox {link}")
