"""This script aims to produce the same results as ZONEMAP."""

from os.path import basename
from operator import itemgetter
import numpy as np
from shapely.geometry import Polygon
import shapely.geometry as sg
from lib.utils import (zones_from_gedi_xml, square, xmls_from_folder, dsum, daverage,
                   get_filename)
from lib.display import display_errors, display_graph

__MS__ = 0.5

def compute_link(zone_1, zone_2):
    """Compute a link between two zones."""
    intersect = zone_1.intersection(zone_2)
    if intersect.area == 0:
        return 0
    return (square(float(intersect.area)/float(zone_1.area))
            + square(float(intersect.area)/float(zone_2.area)))

def compute_links(gt_rects, sys_rects):
    """Compute all links."""
    links = []
    for gt_key, gt_rect in gt_rects.items():
        for sys_key, sys_rect in sys_rects.items():
            strength = compute_link(gt_rect, sys_rect)
            if strength > 0:
                links.append({'strength':strength,
                              'gt_id':gt_key,
                              'sys_id':sys_key})
    return links

def sort_links(links):
    """Sort the links."""
    return sorted(links, key=itemgetter('strength'), reverse=True)

def make_groups(links):
    """Make groups from links."""
    groups = []
    for link in links:
        gt_group_id = find_in_groups(link['gt_id'], groups, 'gt')
        sys_group_id = find_in_groups(link['sys_id'], groups, 'sys')

        if gt_group_id == -1:
            if sys_group_id == -1: # Gt not matched && sys not matched
                group = {'gt':[], 'sys':[]}
                group['gt'].append(link['gt_id'])
                group['sys'].append(link['sys_id'])
                groups.append(group)
            else: # Gt not matched && sys matched
                card_sys = len(groups[sys_group_id]['sys'])
                if card_sys == 1:
                    groups[sys_group_id]['gt'].append(link['gt_id'])
        elif sys_group_id == -1: # Gt matched && sys not matched
            card_ref = len(groups[gt_group_id]['gt'])
            if card_ref == 1:
                groups[gt_group_id]['sys'].append(link['sys_id'])

    return groups

def add_generic_unmatched(groups, rects, tag):
    """Add items that are not in a group in a group of one."""
    for key, _ in rects.items():
        group_id = find_in_groups(key, groups, tag)
        if group_id == -1:
            group = {'gt':[], 'sys':[]}
            group[tag].append(key)
            groups.append(group)

def add_unmatched(groups, gt_rects, sys_rects):
    """Add items that are not in a group for gt and sys."""
    add_generic_unmatched(groups, gt_rects, 'gt')
    add_generic_unmatched(groups, sys_rects, 'sys')
    return groups

def find_in_groups(zone_id, groups, tag):
    """Find a zone id in groups."""
    for i in range(0, len(groups)):
        group = groups[i]
        for zone in group[tag]:
            if zone == zone_id:
                return i
    return -1

def get_error_type(group):
    """Return the error type depending on the cardinality."""
    ngt = len(group['gt'])
    nsys = len(group['sys'])
    if ngt == 0:
        if nsys == 1:
            return "False alarm"
    elif ngt == 1:
        if nsys == 0:
            return "Miss"
        elif nsys == 1:
            return "Match"
        elif nsys > 1:
            return "Split"
    elif ngt > 1:
        if nsys == 1:
            return "Merge"
    return "UNKNOWN"

def get_coef(error_type):
    """Return the penalty coefficient by error type."""
    if error_type == "False alarm" or error_type == "Miss" or error_type == "Match":
        return 1.0
    elif error_type == "Split" or error_type == "Merge":
        return 0.5

def compute_errors(groups, gt_rects, sys_rects):
    """Compute errors from groups."""
    for group in groups:
        error_type = get_error_type(group)
        group['error'] = error_type
        if error_type == "False alarm":
            group['error_details'] = compute_false_alarm(group, sys_rects)
        elif error_type == "Miss":
            group['error_details'] = compute_miss(group, gt_rects)
        elif error_type == "Match":
            group['error_details'] = compute_match(group, gt_rects, sys_rects)
        elif error_type == "Split":
            group['error_details'] = compute_split(group, gt_rects, sys_rects)
        elif error_type == "Merge":
            group['error_details'] = compute_merge(group, gt_rects, sys_rects)
        else:
            print("Unknown error type !! => {}".format(error_type))
            exit(0)
    return groups

def compute_match(group, gt_rects, sys_rects):
    """Compute error for match."""
    gt = gt_rects[group['gt'][0]]
    sys = sys_rects[group['sys'][0]]

    match = gt.intersection(sys)
    misses = []
    false_alarms = []
    misses.append(gt.difference(match))
    false_alarms.append(sys.difference(match))

    return {'match':[match],
            'miss':misses,
            'false_alarm':false_alarms,
            'split':None,
            'merge':None}

def compute_miss(group, gt_rects):
    """Compute error for miss."""
    misses = []
    misses.append(gt_rects[group['gt'][0]])
    return {'match':None,
            'miss':misses,
            'false_alarm':None,
            'split':None,
            'merge':None}

def compute_false_alarm(group, sys_rects):
    """Compute error for false alarm."""
    false_alarms = []
    false_alarms.append(sys_rects[group['sys'][0]])
    return {'match':None,
            'miss':None,
            'false_alarm':false_alarms,
            'split':None,
            'merge':None}

def compute_split(group, gt_rects, sys_rects):
    """Compute the split error."""
    gt_rect = gt_rects[group['gt'][0]]

    # Match
    best_value = 0
    best_intersection = None
    best_id = 0
    for sys_id in group['sys']:
        link_strength = compute_link(gt_rect, sys_rects[sys_id])
        if link_strength > best_value:
            best_value = link_strength
            best_intersection = gt_rect.intersection(sys_rects[sys_id])
            best_id = sys_id
    match = [best_intersection]

    # Split
    splits = []
    for sys_id in group['sys']:
        if sys_id != best_id:
            splits.append(gt_rect.intersection(sys_rects[sys_id]))

    # False alarm
    false_alarms = []
    for sys_id in group['sys']:
        intersection = sys_rects[sys_id].intersection(gt_rect)
        false_alarms.append(sys_rects[sys_id].difference(intersection))

    # Miss
    miss = gt_rect
    for sys_id in group['sys']:
        intersection = sys_rects[sys_id].intersection(gt_rect)
        miss = miss.difference(intersection)
    misses = []
    misses.append(miss)

    return {'match':match,
            'miss':misses,
            'false_alarm':false_alarms,
            'split':splits,
            'merge':None}

def compute_merge(group, gt_rects, sys_rects):
    """Compute the merge error."""
    sys_rect = sys_rects[group['sys'][0]]

    # Match
    best_value = 0
    best_intersection = None
    best_id = 0
    for gt_id in group['gt']:
        link_strength = compute_link(sys_rect,gt_rects[gt_id])
        if link_strength > best_value:
            best_value = link_strength
            best_intersection = sys_rect.intersection(gt_rects[gt_id])
            best_id = gt_id
    match = [best_intersection]

    # Split
    merges = []
    for gt_id in group['gt']:
        if gt_id != best_id:
            merges.append(sys_rect.intersection(gt_rects[gt_id]))

    # Miss
    misses = []
    for gt_id in group['gt']:
        intersection = gt_rects[gt_id].intersection(sys_rect)
        misses.append(gt_rects[gt_id].difference(intersection))

    # False alarm
    false_alarm = sys_rect
    for gt_id in group['gt']:
        intersection = gt_rects[gt_id].intersection(false_alarm)
        false_alarm = false_alarm.difference(intersection)
    false_alarms = []
    false_alarms.append(false_alarm)

    return {'match':match,
            'miss':misses,
            'false_alarm':false_alarms,
            'split':None,
            'merge':merges}

def get_total_area(gt_rects):
    """Compute the sum of area of a set."""
    area = 0
    for _, gt_rect in gt_rects.items():
        area += gt_rect.area
    return area

def get_area(error_detail):
    """Return the area from an error detail."""
    area = 0
    if error_detail is not None:
        for item in error_detail:
            if isinstance(item, sg.collection.GeometryCollection):
                for geom in item:
                    area += geom.area
            else:
                area = item.area
    return area

def compute_score(group):
    """Compute scores from a group."""
    details = group['error_details']
    # Compute match area
    details['match'] = {'area':details['match'], 'surf':get_area(details['match'])}
    # Compute missed area
    details['miss'] = {'area':details['miss'], 'surf':get_area(details['miss'])}
    # Compute false alarm area
    details['false_alarm'] = {'area':details['false_alarm'],
                              'surf':get_area(details['false_alarm'])}
    # Compute split area
    details['split'] = {'area':details['split'],
                        'surf':get_area(details['split'])*len(group['sys'])*__MS__}
    # Compute merge area
    details['merge'] = {'area':details['merge'],
                        'surf':get_area(details['merge'])*len(group['gt'])*__MS__}

def compute_scores(groups):
    """Compute scores from groups."""
    for group in groups:
        compute_score(group)
    return groups

def compute_zonemap(groups, gt_rects):
    """Compute the zonemap score with details."""
    gt_area = get_total_area(gt_rects)
    match, miss, false_alarm, split, merge = (0, 0, 0, 0, 0)
    n_match, n_miss, n_false_alarm, n_split, n_merge = (0, 0, 0, 0, 0)
    for group in groups:
        error_details = group['error_details']
        match += error_details['match']['surf']
        if error_details['match']['surf'] > 0:
            n_match += 1
        miss += error_details['miss']['surf']
        if error_details['miss']['surf'] > 0:
            n_miss += 1
        false_alarm += error_details['false_alarm']['surf']
        if error_details['false_alarm']['surf'] > 0:
            n_false_alarm += 1
        split += error_details['split']['surf']
        if error_details['split']['surf'] > 0:
            n_split += 1
        merge += error_details['merge']['surf']
        if error_details['merge']['surf'] > 0:
            n_merge += 1
    zonemap_score = (miss + false_alarm + split + merge) * 100 / float(gt_area)
    return {'zonemap_score':zonemap_score,
            'total_gt_area':gt_area,
            'match':match,
            'miss':miss,
            'false_alarm': false_alarm,
            'split': split,
            'merge': merge}, {'match':n_match,
                              'miss':n_miss,
                              'false_alarm':n_false_alarm,
                              'split':n_split,
                              'merge':n_merge}

def zonemap(gt_zones, sys_zones, mask_path=None):
    """Perform the zonemap algorithm."""
    links = compute_links(gt_zones, sys_zones)
    sorted_links = sort_links(links)
    groups = make_groups(sorted_links)
    groups = add_unmatched(groups, gt_zones, sys_zones)
    groups = compute_errors(groups, gt_zones, sys_zones)

    if mask_path != None:
        display_errors(groups, mask_path)

    groups = compute_scores(groups)
    results, n_results = compute_zonemap(groups, gt_zones)
    return groups, results, n_results

def zonemap_xml(gt_xml_path, sys_xml_path, mask_path=None):
    """Compute ZoneMap with given gedi xml files."""
    gt_zones = zones_from_gedi_xml(gt_xml_path)
    sys_zones = zones_from_gedi_xml(sys_xml_path)
    groups, results, n_results = zonemap(gt_zones, sys_zones, mask_path)
    return groups, results, n_results

def zonemap_xmls(ref_folder, hyp_folder, mask_folder=None):
    """Perform the zonemapalt algorithm on xmls folders."""
    file_pairs = xmls_from_folder(ref_folder, hyp_folder)
    sum_scores = {}
    sum_n_scores = {}
    for pair in file_pairs:
        mask_path = None
        filename = basename(get_filename(pair['hyp_file']))
        if mask_folder is not None:
            mask_path = '{}/{}.{}'.format(mask_folder, filename, 'jpg')
        _, current_score, n_scores = zonemap_xml(pair['ref_file'], pair['hyp_file'], mask_path)
        sum_scores = dsum(sum_scores, current_score)
        sum_n_scores = dsum(sum_n_scores, n_scores)

    nb_files = len(file_pairs)
    avg_scores = {}
    for key, value in sum_scores.items():
        avg_scores[key] = float(value)/float(nb_files)

    return sum_scores, avg_scores, sum_n_scores

if __name__ == '__main__':
    print(zonemap_xmls("input/all/reference/", "input/all/hypothesis", "input/all/images"))
