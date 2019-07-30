# Parse a Xilinx netlist into a format suitable for EDA tools

import sys
import csv
import re
from functools import reduce

def file_to_list_of_dicts(fname):
    with open(fname) as in_f:
        lines = list(in_f)

    # Naive filter for comment lines
    lines = filter(lambda line: line[0:2] != "--", lines)

    # Remove lines that are just whitespace
    lines = list(filter(lambda a: not a.isspace(), lines))

    # The last line is a printout of the number of pins
    # Use this to sanity check
    nums = re.findall(r'Total Number of Pins (\d+)', lines[-1])
    assert len(nums) == 1, "Last string doesn't appear to be correct format"
    num_pins = int(nums[0])
    print("File claims %d pins" %(num_pins))
    del lines[-1]

    # Our delimiter is space, but the heading names also contain spaces
    # The python csv library only supports single character delimiters
        # So we can't just use double space as a delimiter
    # Therefore replace all instances of more than one space with a comma
    # Then we have a standard CSV

    # First we need to make sure that the file doesn't already contain commas
    assert not reduce(lambda found, line: found or "," in line, lines, False), "File contains"\
                                                                               " a comma"
    # Then do the real work
    lines = list(map(lambda x: re.sub(r'[\s]{2,}', r',', x), lines))

    #for line in lines:
    #    print(line)

    reader = csv.DictReader(lines)

    list_of_dicts = list(reader)

    assert len(list_of_dicts) == num_pins, "num. pins in dict is different"\
                                           " to number reported by file"
    print("File parsed successfully")
    return list(reader)

if len(sys.argv) != 2:
    print("Usage: %s [filename]" %(sys.argv[0]))
    exit(1)

# Get pins from Xilinx file
pins = file_to_list_of_dicts(sys.argv[1])


