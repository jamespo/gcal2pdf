#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a printable calendar in PDF format, pulling events from
Google Calendar.

Tested with Python 3.11

Dependencies:
- Python 3
- Reportlab
- Google Calendar APIs

Resources Used:
- https://stackoverflow.com/a/37443801/435253
  (Originally present at http://billmill.org/calendar )
- https://www.reportlab.com/docs/reportlab-userguide.pdf
- https://gist.github.com/ssokolow/7eace74070778abe637bcd56b105e0d4

Originally created by Bill Mill on 11/16/05, this script is in the public
domain. There are no express warranties, so if you mess stuff up with this
script, it's not my fault.

Refactored and improved 2017-11-23 by Stephan Sokolow (http://ssokolow.com/).

TODO:
- Implement diagonal/overlapped cells for months which touch six weeks to avoid
  wasting space on six rows.
"""

__author__ = "Bill Mill; Stephan Sokolow (deitarion/SSokolow); James Powell"
__license__ = "CC0-1.0"  # https://creativecommons.org/publicdomain/zero/1.0/

import calendar
import collections
import datetime
from contextlib import contextmanager

from reportlab.lib import pagesizes
from reportlab.pdfgen.canvas import Canvas

# Supporting languages like French should be as simple as editing this
ORDINALS = {
    1: 'st', 2: 'nd', 3: 'rd',
    21: 'st', 22: 'nd', 23: 'rd',
    31: 'st',
    None: 'th'}

# Something to help make code more readable
Font = collections.namedtuple('Font', ['name', 'size'])
Geom = collections.namedtuple('Geom', ['x', 'y', 'width', 'height'])
Size = collections.namedtuple('Size', ['width', 'height'])


@contextmanager
def save_state(canvas):
    """Simple context manager to tidy up saving and restoring canvas state"""
    canvas.saveState()
    yield
    canvas.restoreState()


def add_calendar_page(canvas, rect, datetime_obj, cell_cb,
                      first_weekday=calendar.MONDAY):
    """Create a one-month pdf calendar, and return the canvas

    @param rect: A C{Geom} or 4-item iterable of floats defining the shape of
        the calendar in points with any margins already applied.
    @param datetime_obj: A Python C{datetime} object specifying the month
        the calendar should represent.
    @param cell_cb: A callback taking (canvas, day, rect, font) as arguments
        which will be called to render each cell.
        (C{day} will be 0 for empty cells.)

    @type canvas: C{reportlab.pdfgen.canvas.Canvas}
    @type rect: C{Geom}
    @type cell_cb: C{function(Canvas, int, Geom, Font)}
    """
    calendar.setfirstweekday(first_weekday)
    cal = calendar.monthcalendar(datetime_obj.year, datetime_obj.month)
    rect = Geom(*rect)

    # set up constants
    scale_factor = min(rect.width, rect.height)
    line_width = scale_factor * 0.0025
    font = Font('Helvetica', scale_factor * 0.028)
    rows = len(cal)

    # Leave room for the stroke width around the outermost cells
    rect = Geom(rect.x + line_width,
                rect.y + line_width,
                rect.width - (line_width * 2),
                rect.height - (line_width * 2))
    cellsize = Size(rect.width / 7, rect.height / rows)

    # now fill in the day numbers and any data
    for row, week in enumerate(cal):
        for col, day in enumerate(week):
            # Give each call to cell_cb a known canvas state
            with save_state(canvas):

                # Set reasonable default drawing parameters
                canvas.setFont(*font)
                canvas.setLineWidth(line_width)

                cell_cb(canvas, day, Geom(
                    x=rect.x + (cellsize.width * col),
                    y=rect.y + ((rows - row) * cellsize.height),
                    width=cellsize.width, height=cellsize.height),
                    font, scale_factor)

    # finish this page
    canvas.showPage()
    return canvas


def draw_cell(canvas, day, rect, font, scale_factor):
    """Draw a calendar cell with the given characteristics

    @param day: The date in the range 0 to 31.
    @param rect: A Geom(x, y, width, height) tuple defining the shape of the
        cell in points.
    @param scale_factor: A number which can be used to calculate sizes which
        will remain proportional to the size of the entire calendar.
        (Currently the length of the shortest side of the full calendar)

    @type rect: C{Geom}
    @type font: C{Font}
    @type scale_factor: C{float}
    """
    # Skip drawing cells that don't correspond to a date in this month
    if not day:
        return

    margin = Size(font.size * 0.5, font.size * 1.3)

    # Draw the cell border
    canvas.rect(rect.x, rect.y - rect.height, rect.width, rect.height)

    day = str(day)
    ordinal_str = ORDINALS.get(int(day), ORDINALS[None])

    # Draw the number
    text_x = rect.x + margin.width
    text_y = rect.y - margin.height
    canvas.drawString(text_x, text_y, day)

    # Draw the lifted ordinal number suffix
    number_width = canvas.stringWidth(day, font.name, font.size)
    canvas.drawString(text_x + number_width,
                      text_y + (margin.height * 0.1),
                      ordinal_str)
    # JP: dummy text
    smallfont = Font('Helvetica', scale_factor * 0.018)
    canvas.setFont(*smallfont)
    for rownum in range(1,4):
        canvas.drawString(text_x,
                          text_y - (smallfont.size * rownum),
                          'DUMMY %s' % rownum)


def generate_pdf(datetime_obj, outfile, size, first_weekday=calendar.MONDAY):
    """Helper to apply add_calendar_page to save a ready-to-print file to disk.

    @param datetime_obj: A Python C{datetime} object specifying the month
        the calendar should represent.
    @param outfile: The path to which to write the PDF file.
    @param size: A (width, height) tuple (specified in points) representing
        the target page size.
    """
    size = Size(*size)
    canvas = Canvas(outfile, size)

    # margins
    wmar, hmar = size.width / 50, size.height / 50
    size = Size(size.width - (2 * wmar), size.height - (2 * hmar))

    add_calendar_page(canvas,
                      Geom(wmar, hmar, size.width, size.height),
                      datetime_obj, draw_cell, first_weekday).save()


if __name__ == "__main__":
    generate_pdf(datetime.datetime.now(), 'calendar.pdf',
                 pagesizes.landscape(pagesizes.letter))
