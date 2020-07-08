# -*- coding: utf8 -*-
import os
import re
import sqlite3
import argparse
import sys
import glob
import datetime
import json
from collections import OrderedDict
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTImage
from pdfminer.layout import LTRect, LTTextLineHorizontal, LTChar, LTLine, LTText

# name text font size tipical value is 26
NAME_FONTSIZE = 26

# section title font size, such as Summary, Experience, etc
# Education
# typical value is 15.75
SECTION_HEAD_FONTSIZE_MAIN = 15.75

# section title font size, such as Contact, Top Skills, Honors-Awards
# typical value is 13
SECTION_HEAD_FONTSIZE_LEFTPANEL = 13

# experience company name font size
EXP_COMPANY_FONT_SIZE = 12
# experience job name font size
EXP_TITLE_FONT_SIZE = 11.5
# experience duration font size
EXP_DURARION_FONT_SIZE = 10.5

# education university font size
EDU_UNIVERITY_FONT_SIZE = 12
# education university font size, including major, degree and duration
EDU_INFO_FONT_SIZE = 10.5


RESUME_WIDTH = 612
SPLIT = RESUME_WIDTH / 3

OBJ_FILTER = [LTRect, LTLine, LTFigure, LTImage]
TEXT_FILTER = ['\xa0\n']

EOL = ['\n', '\r\n', '\r']

CLEAN_CHAR = ['\xa0']


def getfilelist(path, extension='.pdf'):
    """Returns a list of files in a given path

    Args:
        path (str): path you want to traverse
        extension (str, optional): filename endwith this extension will be returned . Defaults to '.pdf'.

    Returns:
        list: a list of files in a given path
    """
    filenames = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if (extension):
                if file.endswith(extension):
                    filenames.append(os.path.join(path, file))
            else:
                filenames.append(os.path.join(path, file))
    return filenames


class LinkedInResume:
    def __init__(self, resume_file):
        self.resume_file = resume_file
        self.data = {}

    def parse_pages(self):
        """Extract objects in pdf pages, and populate them in a nested list

        Raises:
            PDFTextExtractionNotAllowed: given pdf is not allowed to be parsed
        """
        fp = open(self.resume_file, 'rb')
        # Create a PDF parser object associated with the file object.
        parser = PDFParser(fp)
        # Create a PDF document object that stores the document structure.
        document = PDFDocument(parser)
        # Check if the document allows text extraction. If not, abort.
        if not document.is_extractable:
            raise PDFTextExtractionNotAllowed
        # Create a PDF resource manager object that stores shared resources.
        rsrcmgr = PDFResourceManager()
        # Create a PDF device object.
        laparams = LAParams()
        # Create a PDF page aggregator object.
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        self.pages = []
        for page in PDFPage.create_pages(document):
            interpreter.process_page(page)
            # receive the LTPage object for the page.
            layout = device.get_result()
            # collecting objects from the all pages, sorting them by their Y coordinate
            # self.pages.append(sorted(self.get_objects(layout),
            #                          key=lambda x: x.y0, reverse=True))
            self.pages.append(layout)

    def filter(self, obj):
        """A simple filter for pdfminer.layout.LTXXX objects

        Args:
            obj (object): Any objects want to be tested

        Returns:
            bool: True indicates this object should be included
        """
        for o in OBJ_FILTER:
            if isinstance(obj, o):
                return False
        for t in TEXT_FILTER:
            if obj.get_text() == t:
                return False
        return True

    def split(self):
        """Split the objects into two parts acoording the layout of
        the Linkedin resume.
        """
        left_panel_objs = []
        main_panel_objs = []
        for page in self.pages:
            for obj in page:
                # remove page text object like "Page 1 of 2" etc
                if obj.y1 > 25:
                    # split objects based on the boundary
                    if obj.x0 >= SPLIT:
                        if(self.filter(obj)):
                            main_panel_objs.append(obj)
                    else:
                        if(self.filter(obj)):
                            left_panel_objs.append(obj)

        self.left_panel_objs = left_panel_objs
        self.main_panel_objs = main_panel_objs

    def is_name(self, obj):
        """Decide whether the given obj is or contains the name of
        the person who this resume belongs to acoording to the fontsize

        Args:
            obj (object): given object

        Returns:
            bool: True means the given obj is or contains the name
        """
        font = self.get_font(obj)
        return self.check_font_size(font, NAME_FONTSIZE, 0.5)

    def is_section_head(self, obj, name):
        """Decide whether given obj is or contains a section header of this resume.

        Args:
            obj (object): given obj
            name (str): resume section header name

        Returns:
            bool: True indicates the given obj is or contains the header
        """
        font = self.get_font(obj)
        return self.check_font_size(font, SECTION_HEAD_FONTSIZE_MAIN, 0.5) and obj.get_text().startswith(name)

    def get_section_name(self, obj):
        """Extract the section header name from a given obj,
        make sure isname(obj) or is_section_head(obj) returns True.

        Args:
            obj (object): given obj

        Returns:
            str: name of the section header, such as "Summary", "Experience" etc.
        """
        if isinstance(obj, LTTextBox):
            if(len(obj._objs) > 0 and isinstance(obj._objs[0], LTText)):
                return self.remove_ending_eol(obj._objs[0].get_text().strip())
        elif isinstance(obj, LTText):
            return self.remove_ending_eol(obj.get_text().strip())
        return ''

    def remove_ending_eol(self, string):
        """Remove the ending eol characters of a given string

        Args:
            string (str): the string you want to remove ending eol

        Returns:
            str: the string has no ending eol
        """
        for eol in EOL:
            while string.endswith(eol):
                string = string[:len(string) - 1]
        return string

    def clean(self, string):
        string = self.remove_ending_eol(string.strip())
        for ch in CLEAN_CHAR:
            string = string.replace(ch, '')
        return string

    def get_font(self, obj):
        """Extract the font from a given obj

        Args:
            obj (object): given obj, either LTTextBox or LTText

        Returns:
            int: font size
        """
        if isinstance(obj, LTTextBox):
            if(len(obj._objs) > 0 and isinstance(obj._objs[0], LTText)):
                return obj._objs[0].height
        elif isinstance(obj, LTText):
            return obj.height
        return 0

    def check_font_size(self, font_size, typical_value, offset):
        return font_size > typical_value - offset and font_size < typical_value + offset

    def parse_main_panel(self):
        """Parse the main panel objects into sections.
        """
        sections = {}
        section_objs = []
        for obj in self.main_panel_objs:
            if self.is_name(obj):
                section_objs = []
                self.name = self.get_section_name(obj)
                self.data['name'] = self.name
                sections["Basic Info"] = section_objs
            elif self.is_section_head(obj, ''):
                section_objs = []
                sections[self.get_section_name(obj)] = section_objs
            section_objs.append(obj)
        self.sections = sections

    def box_to_text(self, li):
        ret = []
        for l in li:
            if isinstance(l, LTTextBox):
                for text in l:
                    if isinstance(text, LTText):
                        ret.append(text)
            elif isinstance(l, LTText):
                ret.append(l)
        return ret

    def parse_exp(self):
        exp = self.box_to_text(self.sections["Experience"])
        ret = []

        index = 0
        count = len(exp)

        while index < count:
            obj = exp[index]
            font = self.get_font(obj)
            # search for company
            if self.check_font_size(font, EXP_COMPANY_FONT_SIZE, 0.5):
                company = obj.get_text()
                index = index + 1
                # search for job title
                while index < count:
                    obj = exp[index]
                    font = self.get_font(obj)
                    if self.check_font_size(font, EXP_TITLE_FONT_SIZE, 0.5):
                        title = obj.get_text()
                        index = index + 1
                        # search for job title
                        while index < count:
                            obj = exp[index]
                            font = self.get_font(obj)
                            if self.check_font_size(font, EXP_DURARION_FONT_SIZE, 0.5):
                                duration = obj.get_text()
                                ret.append(
                                    {"company": self.clean(company),
                                        "job_title": self.clean(title),
                                        "duration":
                                        self.parse_exp_duration(self.clean(duration))})
                                break
                            index = index + 1
                    elif self.check_font_size(font, EXP_COMPANY_FONT_SIZE, 0.5):
                        index = index - 1
                        break
                    index = index + 1
            index = index + 1
        self.experience = ret
        self.data['experience'] = self.experience

    def parse_exp_duration(self, duration):
        """Parse experience date string like 'February 2019-Present(1 year 6 months)'

        Args:
            duration (str): a experience date string

        Returns:
            dict: a date dict like {"from_year": 2019, "to_year": "Present"}
        """
        from_year = ''
        from_year = ''
        to_year = ''
        year_list = re.findall(r'\d{4}', duration)
        if len(year_list) == 1:
            from_year = year_list[0]
            if ("present" in duration.lower()):
                to_year = datetime.date.today().year
        elif len(year_list) == 2:
            from_year = year_list[0]
            to_year = year_list[1]
        return {"from_year": from_year, "to_year": to_year}

    def parse_edu(self):
        edu = self.box_to_text(self.sections["Education"])
        ret = []

        index = 0
        count = len(edu)

        while index < count:
            obj = edu[index]
            font = self.get_font(obj)
            # search for unversity
            if self.check_font_size(font, EDU_UNIVERITY_FONT_SIZE, 0.5):
                univerity = obj.get_text()
                index = index + 1
                # search for info
                while index < count:
                    obj = edu[index]
                    font = self.get_font(obj)
                    if self.check_font_size(font, EDU_INFO_FONT_SIZE, 0.5):
                        info = obj.get_text()
                        edu_item = {"university": self.clean(univerity)}
                        edu_item.update(self.parse_edu_info(self.clean(info)))
                        ret.append(edu_item)
                        break
                    elif self.check_font_size(font, EXP_COMPANY_FONT_SIZE, 0.5):
                        index = index - 1
                        break
                    index = index + 1
            index = index + 1
        self.education = ret
        self.data['education'] = self.education

    def parse_edu_info(self, info):
        info_list = re.split(',|·', info)

        degree = ''
        major = ''
        duration = {}

        if len(info_list) == 1:
            degree = info
        elif len(info_list) == 2:
            if '·' in info:
                degree = info_list[0]
                duration = self.parse_edu_date(info_list[1])
            else:
                degree = info_list[0]
                major = info_list[1]
        else:
            degree = info_list[0]
            major = info_list[1]
            duration = self.parse_edu_date(info_list[2])
        return {"degree": degree, "major": major, "duration": duration}

    def parse_edu_date(self, date):
        """Parse eduation date string like "(2005-2006)" or "(September 1992-August 1996)"

        Args:
            date (str): education date string

        Returns:
            dict: a dict like this {"from_year": "2005", "to_year": "2006"}
        """
        from_year = ''
        to_year = ''
        year_list = re.findall(r'\d{4}', date)
        if len(year_list) == 1:
            from_year = year_list[0]
        elif len(year_list) == 2:
            from_year = year_list[0]
            to_year = year_list[1]
        return {"from_year": from_year, "to_year": to_year}

    def backup_json(self, filename="results.json"):
        with open(filename, 'w') as f:
            json.dump(self.data, f)

    def _parse(self):
        self.split()
        self.parse_main_panel()
        self.parse_exp()
        self.parse_edu()
        self.backup_json()
        pass

    def parse(self):
        self._parse()
