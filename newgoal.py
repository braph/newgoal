#!/usr/bin/python3
# Copyright 2018 Benjamin Abendroth (braph93@gmx.de)

import re
import sys
import csv
import time
import argparse
import urllib.request

url = 'http://www.nowgoal.com/data/bf_en2.js?%s'

argp = argparse.ArgumentParser(description='Export data from newgoal.com as csv')
argp.add_argument('outfile', metavar='FILE', nargs='?', help='Output file. Stdout if not given')
args = argp.parse_args()

# Storage of arrays A and B
dataArrays = { }

# Storage of array C (as dict!)
dataCountries = { }

# Column names for arrays A and B.
# >None< indicates that the purpose of this field is unknown and won't be used.
# No duplicates, names may NOT collide!
dataColumns = {
    'A': [ # 10 per row makes it easier to count
        None, 'B_KEY', None, None, 'Home', 'Away', 'Year', 'Month', 'Day', 'Hour',
        'Minute', 'Seconds', 'Year2?', 'Month2?', 'Day2?', 'Hour2?', 'Minutes2?', 'Seconds2?', None, 'Home_Score',
        'Away_Score', 'CHT_3', 'CHT_4', 'Home_Redcards', 'Away_Redcards', 'Home_Yellowcards', 'Away_Yellowcards', None, None, None,
        'Bool?', None, 'Currency?', 'C_KEY', None, None, None, 'CHT_1', 'CHT_2', None, None,
        None, None, None
    ],

    'B': [
        'sclassid', 'League_Short', 'League_Long', 'Color?', None, 'Link?', None, None
    ]
}

def remove_tags(s):
    ''' Remove tags from string '''
    return re.sub('<[^>]*>', '', s)

def regex_arbitrary_whitespaces(regex):
    ''' Two spaces will be turned into arbitray whitespace '''
    return regex.replace('  ', '\\s*')

export = [
    # This must either be a string or a tuple of size 2.
    # string: column name to export (see dataColumns)
    # tuple:
    #   arg0: Column name as string (for headline)
    #   arg1: Callback function for generating the column value

    'League_Short', 'League_Long', 'Leauge_Country',
    # Home and Away may contain <span> tags
    ( 'Home', lambda r: remove_tags(r['Home']) ),
    ( 'Away', lambda r: remove_tags(r['Away']) ),
    'Home_Score', 'Away_Score',
    'Home_Redcards', 'Away_Redcards',
    'Home_Yellowcards', 'Away_Yellowcards',
    'CHT_1', 'CHT_2', 'CHT_3', 'CHT_4',
    'Year',
    # Month is counting from 0
    ( 'Month', lambda r: str(1 + int(r['Month'])) ),
    'Day', 'Hour', 'Minute', 'Seconds',
]

timestamp = str(int(time.time()))
response = urllib.request.urlopen(url % timestamp)
js_text = response.read().decode('utf-8')
#print(js_text)

# this is likely to be called
# >>  A[2]=['$$',62,'',,'',4,2,1,,'','',''];
regex_assign = '([ABC])  \[  (\d+)  \]  =  (.*)'
regex_assign = re.compile(regex_arbitrary_whitespaces(regex_assign))

# >>  var A=Array(146);
regex_declare = '.*var  ([AB])  =  Array  \(  (\d+)  \)'
regex_declare = re.compile(regex_arbitrary_whitespaces(regex_declare))

for line in re.split("[\n\r]+", js_text):
    #print(line)

    match = regex_assign.match(line)
    if match:
        array, index, values = match.groups()
        values = values.strip(' [];\r')
        values = values.split(',') # TODO: right parsing
        values = list(map(lambda v: v.strip("'"), values))

        if array == 'C':
            dataCountries[ int(values[0]) ] = values[1]
        else:
            dataArrays[array][int(index)] = values
        next

    match = regex_declare.match(line)
    if match:
        array, size = match.groups()
        dataArrays[array] = [None] * int(size)


def combine_arrays():
    ''' Generator for combining the dataArrays returning a list of dicts '''
    for A_row in dataArrays['A']:
        if A_row is None:
            #print('first row empty (as usual)')
            continue

        row = {}

        for i, col in enumerate(dataColumns['A']):
            if col:
                row[col] = A_row[i]

        # field 2 of A-array contains key to B-array
        B_row = dataArrays['B'][int( A_row[1] )]
        if B_row:
            for i,col in enumerate(dataColumns['B']):
                if col:
                    row[col] = B_row[i]

        # field 34 of A-array contains key to C-array
        row['Leauge_Country'] = dataCountries[int(A_row[33])]

        yield row


if not args.outfile:
    args.outfile = '/dev/stdout'

with open(args.outfile, 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile,
        delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)

    # headline
    csv_row = []
    for ex in export:
        if type(ex) is str:
            csv_row.append(ex)
        else:
            csv_row.append(ex[0])
    csvwriter.writerow(csv_row)

    # rows
    for row in combine_arrays():
        csv_row = []
        for ex in export:
            if type(ex) is str:
                csv_row.append(row[ex])
            else:
                csv_row.append( ex[1](row) )
        csvwriter.writerow(csv_row)

