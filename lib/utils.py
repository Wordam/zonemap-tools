"""All utility function not really related to ZoneMap."""

import random
import os
from os.path import basename
from os import listdir
from collections import defaultdict
import xml.etree.ElementTree as ET
from collections import defaultdict
from xml.etree.ElementTree import Element, SubElement, tostring
from shapely.geometry import Polygon

__red__, __green__, __blue__ = (255, 0, 0), (0, 255, 0), (0, 0, 255)
__rgb__ = [__red__, __green__, __blue__]

def get_random_color():
    """Return a random rgb color."""
    return __rgb__[random.randint(0, 2)]

def zones_from_file(path):
    """Parse zones from file."""
    zones = {}
    fil = open(path, 'r')
    for line in fil:
        splits = line.split(',')
        zone_id = int(splits[0])
        left, top, width, height = int(splits[1]), int(splits[2]), int(splits[3]), int(splits[4])
        bottom = top+height
        right = left + width
        zones[zone_id] = Polygon([[left, top], [right, top], [right, bottom], [left, bottom]])
    return zones

def zones_from_gedi_xml(xml_path, gedi_type="Area"):
    """Parse zones from a GEDI xml."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    document = root.find('.//{http://lamp.cfar.umd.edu/media/projects/GEDI/}DL_DOCUMENT')
    page = document.find('.//{http://lamp.cfar.umd.edu/media/projects/GEDI/}DL_PAGE')
    zones = {}
    for child in page:
        if child.attrib['gedi_type'] == gedi_type:
            zone_id = int(child.attrib['id'])
            left = int(child.attrib['col'])
            top = int(child.attrib['row'])
            right = left + int(child.attrib['width'])
            bottom = top + int(child.attrib['height'])
            zones[zone_id] = Polygon([[left, top], [right, top], [right, bottom], [left, bottom]])
    return zones

def square(value):
    """Return the square value."""
    return value*value

def xmls_from_folder(ref_folder, hyp_folder):
    """Return matching pair of xml files from ref and hyp folders."""
    file_pairs = []
    for ref_file in listdir(ref_folder):
        for hyp_file in listdir(hyp_folder):
            if basename(ref_file) == basename(hyp_file):
                file_pairs.append({'ref_file':'{}/{}'.format(ref_folder, ref_file),
                                   'hyp_file':'{}/{}'.format(hyp_folder, hyp_file)})
    return file_pairs

def dsum(*dicts):
    """Return the sum of dict by keys."""
    ret = defaultdict(float)
    for dictt in dicts:
        for key, value in dictt.items():
            ret[key] += value
            ret[key] = round(ret[key],2)
    return dict(ret)

def daverage(*dicts):
    """Return the sum of dict by keys."""
    ret = defaultdict(float)
    for dictt in dicts:
        for key, value in dictt.items():
            ret[key] += value
            ret[key] /= 2
    return dict(ret)

def get_filename(path):
    return os.path.splitext(path)[0]
