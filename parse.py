# Parse a Xilinx netlist into a format suitable for EDA tools

import sys
import csv
import re

def file_to_dict(fname):
    with open(fname) as in_f:
        # Naive filter for comment lines
        lines = filter(lambda line: line[0:2] != "--", in_f)

        # Remove lines that are just space
        lines = filter(lambda a: not a.isspace(), lines)

        # Convert filter object to list
        lines = list(lines)

        # Our delimiter is space, but the heading names also contain spaces
        # The python csv library only supports single character delimiters
        # Therefore we replace the single spaces in the first line with underscores
        # This lets us use spaces as delimiters, and ignore whitespace following delimiters
        lines[0] = re.sub(r'([^\s])\s([^\s])', r'\1_\2', lines[0])

        

        for line in lines:
            print(line)

        #reader = csv.DictReader(lines, delimiter=' ')
        #for row in reader:
        #    print(row)

if len(sys.argv) != 2:
    print("Usage: %s [filename]" %(sys.argv[0]))
    exit(1)

file_to_dict(sys.argv[1])
