"""Benchmark zonemap and zonemapalt algorithm based on beta value."""

from zonemapalt import *
from zonemap import *

if __name__ == '__main__':
    __abcisse__ = np.arange(0, 1.01, 0.1)
    __za_split__ = []
    __za_miss__ = []
    __za_merge__ = []
    __za_fa__ = []
    __za_match__ = []
    __za_multiple__ = []
    __z_split__ = []
    __z_miss__ = []
    __z_merge__ = []
    __z_fa__ = []
    __z_match__ = []

    print('abcisse vector {}'.format(__abcisse__))
    for __BETA__ in __abcisse__:
        print('Beta {}'.format(__BETA__))
        _, _, za_avg = zonemapalt_xmls("input/all/reference/", "input/all/hypothesis", __BETA__)
        __za_split__.append(za_avg['split'])
        __za_miss__.append(za_avg['miss'])
        __za_merge__.append(za_avg['merge'])
        __za_fa__.append(za_avg['false_alarm'])
        __za_match__.append(za_avg['match'])
        __za_multiple__.append(za_avg['multiple'])

    display_graph(__abcisse__,
                  {'split':__za_split__,
                   'miss':__za_miss__,
                   'merge':__za_merge__,
                   'false_alarm':__za_fa__,
                   'match':__za_match__,
                   'multiple':__za_multiple__})
