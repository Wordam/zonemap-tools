"""This script aims to compute the ZoneMapAlt algorithm."""

import copy
from os.path import basename
from tqdm import tqdm
from shapely.geometry import Polygon
import shapely.geometry as sg
import numpy as np
import cv2
from operator import itemgetter

from lib.utils import (square, zones_from_gedi_xml, xmls_from_folder, dsum, daverage,
                   get_filename)
from lib.display import display_matches, display_graph

__MS__ = 0.5

def compute_link(zone_1, zone_2):
    """Compute a link between two zones."""
    intersect = zone_1.intersection(zone_2)
    if intersect.area == 0:
        return 0
    return (square(float(intersect.area)/float(zone_1.area))
            + square(float(intersect.area)/float(zone_2.area)))

def compute_links(ref_zones, hyp_zones):
    """Compute all links."""
    links = []
    for ref_key, ref_zone in ref_zones.items():
        for hyp_key, hyp_zone in hyp_zones.items():
            strength = compute_link(ref_zone, hyp_zone)
            if strength > 0:
                links.append({'strength':strength,
                              'ref_id':ref_key,
                              'hyp_id':hyp_key})
    return links

def sort_links(links):
    """Sort the links."""
    return sorted(links, key=itemgetter('strength'), reverse=True)

def make_matches(links, ref_zones, hyp_zones, threshold):
    """Make groups from links."""
    ref_links = {}
    hyp_links = {}
    matches = {}
    for i, link in enumerate(links):
        ref_link = find_in_links(link['ref_id'], ref_links)
        hyp_link = find_in_links(link['hyp_id'], hyp_links)

        # Get original zones
        ref_zone = copy.copy(ref_zones[link['ref_id']])
        hyp_zone = copy.copy(hyp_zones[link['hyp_id']])

        ref_card = 1
        hyp_card = 1
        if hyp_link is not None: # hyp matched
            ref_card += len(hyp_link)
            for matched_ref_id in hyp_link:
                matched_ref = copy.copy(ref_zones[matched_ref_id])
                ref_zone = ref_zone.difference(ref_zone.intersection(matched_ref))
                hyp_zone = hyp_zone.difference(hyp_zone.intersection(matched_ref))

        if ref_link is not None: # ref matched
            hyp_card += len(ref_link)
            for matched_hyp_id in ref_link:
                matched_hyp = copy.copy(hyp_zones[matched_hyp_id])
                ref_zone = ref_zone.difference(ref_zone.intersection(matched_hyp))

        # Compute ratio
        hyp_ref_intersection = ref_zone.intersection(hyp_zone)
        matching_ratio = 0
        if ref_zone.area > 0:
            matching_ratio = hyp_ref_intersection.area / ref_zone.area

        if matching_ratio > threshold:
            # Match them all
            if ref_link is not None:
                ref_links[link['ref_id']].append(link['hyp_id'])
            else:
                ref_links[link['ref_id']] = [link['hyp_id']]
            if hyp_link is not None:
                hyp_links[link['hyp_id']].append(link['ref_id'])
            else:
                hyp_links[link['hyp_id']] = [link['ref_id']]

            matches[i] = {'ref_id':link['ref_id'],
                          'hyp_id':link['hyp_id'],
                          'ref_card':ref_card,
                          'hyp_card':hyp_card,
                          'zone':hyp_ref_intersection,
                          'error_class':get_error_class(ref_card, hyp_card)}

    return matches, ref_links, hyp_links

def get_error_class(ref_card, hyp_card):
    """Return the error class depending on the cardinality of ref and hyp."""
    error_class = "UNKNOWN"
    if ref_card == 0:
        if hyp_card == 1:
            error_class = "False alarm"
    elif ref_card == 1:
        if hyp_card == 0:
            error_class = "Miss"
        elif hyp_card == 1:
            error_class = "Match"
        elif hyp_card > 1:
            error_class = "Split"
    elif ref_card > 1:
        if hyp_card == 1:
            error_class = "Merge"
        if hyp_card > 1:
            error_class = "Multiple"
    return error_class


def find_in_links(zone_id, links):
    """Find a zone id in groups."""
    if zone_id in links.keys():
        return links[zone_id]
    return None

def get_coef(error_type):
    """Return the penalty coefficient by error type."""
    if error_type == "False alarm" or error_type == "Miss" or error_type == "Match":
        return 1.0
    elif error_type == "Split" or error_type == "Merge" or error_type == "Multiple":
        return 0.5

def find_missed_areas(matches, ref_zones, hyp_zones, ref_links, hyp_links):
    """Find missed areas."""
    for ref_zone_id, ref_zone in ref_zones.items(): # For each zones
        ref_zone_tmp = copy.copy(ref_zone)
        ref_link = find_in_links(ref_zone_id, ref_links) # Look for it in links
        if ref_link is not None:
            for hyp_zone_id in ref_link:
                hyp_zone = hyp_zones[hyp_zone_id]
                ref_zone_tmp = ref_zone_tmp.difference(ref_zone_tmp.intersection(hyp_zone))
        if ref_zone_tmp.area > 0:
            matches['miss_{}'.format(ref_zone_id)] = {'ref_id':ref_zone_id,
                                                      'hyp_id':None,
                                                      'zone':ref_zone_tmp,
                                                      'error_class':'Miss'}
    for hyp_zone_id, hyp_zone in hyp_zones.items():
        hyp_zone_tmp = copy.copy(hyp_zone)
        hyp_link = find_in_links(hyp_zone_id, hyp_links)
        if hyp_link is not None:
            for ref_zone_id in hyp_link:
                ref_zone = ref_zones[ref_zone_id]
                hyp_zone_tmp = hyp_zone_tmp.difference(hyp_zone_tmp.intersection(ref_zone))
        if hyp_zone_tmp.area > 0:
            matches['fa_{}'.format(hyp_zone_id)] = {'ref_id':None,
                                                    'hyp_id':hyp_zone_id,
                                                    'zone':hyp_zone_tmp,
                                                    'error_class':'False alarm'}

    return matches

def compute_errors(matches):
    """Compute surface errors."""
    matchh, miss, false_alarm, split, merge, multiple = (0, 0, 0, 0, 0, 0)
    n_match, n_miss, n_fa, n_split, n_merge, n_multiple = (0, 0, 0, 0, 0, 0)
    for _, match in matches.items():
        if match['error_class'] == "Match":
            matchh += match['zone'].area
            n_match += 1
        if match['error_class'] == "Miss":
            miss += match['zone'].area
            n_miss += 1
        if match['error_class'] == "False alarm":
            false_alarm += match['zone'].area
            n_fa += 1
        if match['error_class'] == "Split":
            split += match['zone'].area * __MS__ * match['hyp_card']
            n_split += 1
        if match['error_class'] == "Merge":
            merge += match['zone'].area * __MS__ * match['ref_card']
            n_merge += 1
        if match['error_class'] == "Multiple":
            multiple += match['zone'].area * __MS__ * (match['ref_card']+match['hyp_card'])
            n_multiple += 1
    return {'match':matchh,
            'miss':miss,
            'false_alarm': false_alarm,
            'split': split,
            'merge': merge,
            'multiple': multiple}, {'match':n_match,
                                    'miss':n_miss,
                                    'false_alarm':n_fa,
                                    'split':n_split,
                                    'merge':n_merge,
                                    'multiple':n_multiple}

def get_total_area(zones):
    """Compute the sum of area of a set."""
    area = 0
    for _, zone in zones.items():
        area += zone.area
    return area

def compute_scores(scores, ref_zones):
    """Compute zonemapalt score."""
    ref_zones_area = get_total_area(ref_zones)
    total_error = (scores['miss'] + scores['false_alarm'] + scores['split']
                   + scores['merge'] + scores['multiple'])
    zonemapalt_score = float(total_error)*100/float(ref_zones_area)
    scores['zonemapalt_score'] = zonemapalt_score
    scores['total_ref_area'] = ref_zones_area
    return scores

def zonemapalt(ref_zones, hyp_zones, threshold, mask_path=None):
    """Perform the zonemapalt algorithm."""
    links = compute_links(ref_zones, hyp_zones)
    sorted_links = sort_links(links)
    matches, ref_links, hyp_links = make_matches(sorted_links, ref_zones, hyp_zones, threshold)
    matches = find_missed_areas(matches, ref_zones, hyp_zones, ref_links, hyp_links)
    if mask_path is not None:
        print('Displaying matches')
        display_matches(matches, mask_path, hyp_zones)
    scores,n_scores = compute_errors(matches)
    scores = compute_scores(scores, ref_zones)
    return scores, n_scores

def zonemapalt_xml(ref_path, hyp_path, threshold, mask_path=None):
    """Read xml files before performing the zonemapalt algorithm."""
    ref_zones = zones_from_gedi_xml(ref_path)
    sys_zones = zones_from_gedi_xml(hyp_path)
    scores, n_scores = zonemapalt(ref_zones, sys_zones, threshold, mask_path)
    return scores, n_scores

def zonemapalt_xmls(ref_folder, hyp_folder, mask_folder=None, threshold=0.15):
    """Perform the zonemapalt algorithm on xmls folders."""
    file_pairs = xmls_from_folder(ref_folder, hyp_folder)
    sum_scores = {}
    sum_n_scores = {}
    with tqdm(total=len(file_pairs)) as pbar:
        for pair in file_pairs:
            mask_path = None
            filename = basename(get_filename(pair['hyp_file']))
            if mask_folder is not None:
                mask_path = '{}/{}.{}'.format(mask_folder, filename, 'jpg')
            current_score, n_scores = zonemapalt_xml(pair['ref_file'], pair['hyp_file'], threshold, mask_path)
            sum_scores = dsum(sum_scores, current_score)
            sum_n_scores = dsum(sum_n_scores, n_scores)

            pbar.update()

    nb_files = len(file_pairs)
    avg_scores = {}
    for key, value in sum_scores.items():
        avg_scores[key] = float(value)/float(nb_files)

    return sum_scores, avg_scores, sum_n_scores

if __name__ == '__main__':
    print(zonemapalt_xmls("input/all/reference/", "input/all/hypothesis", "input/all/images"))
