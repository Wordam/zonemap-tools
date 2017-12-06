"""Where all display method goes !."""

import cv2
import numpy as np
import shapely.geometry as sg
import matplotlib.pyplot as plt
import os
from os.path import basename
from utils import get_filename
import shutil

__color_map__ = {}
__color_map__['False alarm'] = (43, 243, 240)
__color_map__['Miss'] = (125, 125, 125)
__color_map__['Match'] = (90, 239, 73)
__color_map__['Merge'] = (255, 34, 255)
__color_map__['Split'] = (239, 131, 73)
__color_map__['Multiple'] = (228, 31, 31)

def draw_polygon(img, polygon, color):
    """Draw a shapely polygon."""
   # print(polygon)
    if (isinstance(polygon, sg.collection.GeometryCollection)
            or isinstance(polygon, sg.multipolygon.MultiPolygon)):
        for geom in polygon.geoms:
            if not isinstance(geom,sg.LineString):
                draw_polygon(img, geom, color)
    else:
        if isinstance(polygon,list):
            for geom in polygon:
                draw_polygon(img, geom, color)
        else:
            pts = np.array(polygon.exterior.coords)
            pts = np.int32([pts])
            # cv2.polylines(img, pts, True, color, 1)
            cv2.fillPoly(img, pts, color, 1)

def display_matches(matches, img_path, alpha=0.4):
    """Display errors groups."""
    img = cv2.imread(img_path)
    img_cpy = img.copy()
    img_match = img.copy()
    img_miss = img.copy()
    img_false_alarm = img.copy()
    img_split = img.copy()
    img_merge = img.copy()
    img_multiple = img.copy()

    for _, match in matches.items():
        # Draw miss(es)
        if match['error_class'] == 'Miss':
            draw_polygon(img_cpy, match['zone'], __color_map__["Miss"])
            draw_polygon(img_miss, match['zone'], __color_map__["Miss"])

        # Draw false alarm(s)
        if match['error_class'] == 'False alarm':
            draw_polygon(img_cpy, match['zone'], __color_map__["False alarm"])
            draw_polygon(img_false_alarm, match['zone'], __color_map__["False alarm"])

        # Draw splits
        if match['error_class'] == 'Split':
            draw_polygon(img_cpy, match['zone'], __color_map__["Split"])
            draw_polygon(img_split, match['zone'], __color_map__["Split"])

        # Draw merges
        if match['error_class'] == 'Merge':
            draw_polygon(img_cpy, match['zone'], __color_map__["Merge"])
            draw_polygon(img_merge, match['zone'], __color_map__["Merge"])

        # Draw match
        if match['error_class'] == 'Match':
            draw_polygon(img_cpy, match['zone'], __color_map__["Match"])
            draw_polygon(img_match, match['zone'], __color_map__["Match"])

        # Draw multiple
        if match['error_class'] == 'Multiple':
            draw_polygon(img_cpy, match['zone'], __color_map__["Match"])
            draw_polygon(img_multiple, match['zone'], __color_map__["Match"])

    out_folder = basename(get_filename(img_path))
    out_folder = "zonemapaltresults/" + out_folder
    if os.path.exists(out_folder):
        shutil.rmtree(out_folder)
    os.makedirs(out_folder)

    cpy = img.copy()
    cv2.addWeighted(img_match, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/match.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_miss, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/miss.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_false_alarm, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/false_alarm.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_split, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/split.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_merge, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/merge.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_multiple, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/multiple.png", cpy)

def display_errors(groups, img_path, alpha=0.4):
    """Display errors groups."""
    img = cv2.imread(img_path)
    img_cpy = img.copy()
    img_match = img.copy()
    img_miss = img.copy()
    img_false_alarm = img.copy()
    img_split = img.copy()
    img_merge = img.copy()

    for group in groups:
        details = group['error_details']
        # Draw miss(es)
        misses = details['miss']
        if misses is not None:
            for miss in misses:
                draw_polygon(img_cpy, miss, __color_map__["Miss"])
                draw_polygon(img_miss, miss, __color_map__["Miss"])

        # Draw false alarm(s)
        false_alarms = details['false_alarm']
        if false_alarms is not None:
            for false_alarm in false_alarms:
                draw_polygon(img_cpy, false_alarm, __color_map__["False alarm"])
                draw_polygon(img_false_alarm, false_alarm, __color_map__["False alarm"])

        # Draw splits
        splits = details['split']
        if splits is not None:
            for split in splits:
                draw_polygon(img_cpy, split, __color_map__["Split"])
                draw_polygon(img_split, split, __color_map__["Split"])

        # Draw merges
        merges = details['merge']
        if merges is not None:
            for merge in merges:
                draw_polygon(img_cpy, merge, __color_map__["Merge"])
                draw_polygon(img_merge, merge, __color_map__["Merge"])

        # Draw match
        match_poly = details['match']
        if match_poly is not None:
            draw_polygon(img_cpy, match_poly, __color_map__["Match"])
            draw_polygon(img_match, match_poly, __color_map__["Match"])

    out_folder = basename(get_filename(img_path))
    out_folder = "zonemapresults/" + out_folder
    if os.path.exists(out_folder):
        shutil.rmtree(out_folder)
    os.makedirs(out_folder)

    cpy = img.copy()
    cv2.addWeighted(img_match, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/match.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_miss, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/miss.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_false_alarm, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/false_alarm.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_split, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/split.png", cpy)

    cpy = img.copy()
    cv2.addWeighted(img_merge, alpha, cpy, 1 - alpha, 0, cpy)
    cv2.imwrite(out_folder + "/merge.png", cpy)

def display_graph(it_vect, datas):
    ax = plt.subplot(111, xlabel='β', ylabel='Number of class error')
    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(35)

    for name,data in datas.items():
        plt.plot(it_vect, data, label=name, linewidth=7.0)
    leg = plt.legend(loc='upper left', shadow=True, fancybox=True, prop={'size':35})
    leg.get_frame().set_alpha(0.3)
    plt.show()
    plt.savefig('out.png')