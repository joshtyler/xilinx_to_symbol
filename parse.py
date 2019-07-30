# Parse a Xilinx netlist into a format suitable for EDA tools

import sys
import csv
import re
from functools import reduce
from copy import deepcopy

# Lexographic comparison. From stack overflow 4623446
def tryint(s):
    try:
        return int(s)
    except:
        return s

def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]


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
    assert not list(filter(lambda line: "," in line, lines)), "File contains a comma"
    # Then do the real work
    lines = list(map(lambda x: re.sub(r'[\s]{2,}', r',', x), lines))

    #for line in lines:
    #    print(line)

    reader = csv.DictReader(lines)

    list_of_dicts = list(reader)

    assert len(list_of_dicts) == num_pins,\
         "num. pins in dict is different to number reported by file"
    print("File parsed successfully")
    return list_of_dicts

def print_bank_summary(banks):
    for key, value in banks.items():
        print("Bank %s, len %d" %(key, len(value)))

def filter_to_new_list(lst, key, regex):
    # First get the new list
    new_lst = list(filter(lambda itm: re.match(regex, itm[key]), lst))
    # Then remove the elements from the old list
    for itm in new_lst:
        lst.remove(itm)
    return new_lst


# This is the sort function for sorting pins within a bank
# As a baseline we do an lexographic sort (i.e. human/filename sort)
# One level above this we give one more sorting value based upon our own heuristic of what looks good
# We also ensure to sort by bytelane (if present)
def bank_sort_key(pin):
    name = pin["Pin Name"]

    key = alphanum_key(name)

    # Keep all the pins in a bytelane together
    assert False, "Implement this"
    assert False, "Also need to keep MGTs together"

    if re.match("VCCO", name): # It's convenient to have VCCO at the top because it connects to power pins
        extra = 0
    elif re.match("VREF", name): # Likewise 
        extra = 1
    elif re.match("MGTREFCLK", name): # Put MGT refclks above the MGTs themselves
        extra = 2
    else:
        extra = 3
        
    key.insert(0,extra)
    return key

# N is before P in the alphabet, meaning our lexographic sort puts all the complement pins before the true
# We solve this by iterating through pairs of pins, and if the only differences between the two are N and P being swapped
def swap_ps_and_ns(bank):
    for i in range(0,len(bank)-1):
        namea = bank[i]["Pin Name"]
        nameb = bank[i+1]["Pin Name"]
        # Very small performance improvement :)
        if namea == nameb:
            continue
        # Zip truncates names if different lengths
        if len(namea) != len(nameb):
            continue

        u = zip(namea, nameb)
        # If we find any difference that isn't a simple p/n swap, mark the candidate as bad
        okay = True
        for l, m in u:
            if l != m and not((l in ['P', 'N']) and (m in ['P', 'N'])):
                okay = False
                break
        if okay:
            print("Swapping %s and %s (%s,%s)" %(namea, nameb, l, m))

if len(sys.argv) != 2:
    print("Usage: %s [filename]" %(sys.argv[0]))
    exit(1)

# Get pins from Xilinx file
pins = file_to_list_of_dicts(sys.argv[1])

# The super logic region should be NA for all pins
# Check this and remove the field since we will not use it
assert not list(filter(lambda pin: pin["Super Logic Region"] != "NA", pins)),\
    "Found pin where SLR is not NA"
for pin in pins:
    del pin["Super Logic Region"]

# There is exactly one pin in bank 0, and of type config - PUDC_B
# Since it is alone, pretend it is in bank NA and of type NA
assert len(list(filter(lambda pin: pin["Bank"] == "0" or pin["I/O Type"] == "CONFIG", pins))) == 1,\
     "More than one pin in bank 0 or I/O type of CONFIG"
for pin in pins:
    if pin["Bank"] == "0" and pin["I/O Type"] == "CONFIG":
        pin["Bank"] = "NA"
        pin["I/O Type"] = "NA"

# We want our elements to be grouped by bank
# Do this by forming a dictionary of lists of dictionaries
# The top level dictionary is indexed by bank name
banks = {}
for pin in pins:
    bank = pin["Bank"]
    del pin["Bank"]
    banks.setdefault(bank, []).append(pin)

print("Intial bank filtering:")
print_bank_summary(banks)
print("")

# The I/O Type should be the same for all I/Os in each bank (except vcco pins)
# Check that this is the case, then if so make it part of the key

# Take a copy because we will be modifying the keys as we go
old_banks = deepcopy(banks)

for key, value in old_banks.items():
    io_type = value[0]["I/O Type"]
    for pin in value:
        if not "VCCO_" in pin["Pin Name"]:
            assert pin["I/O Type"] == io_type,\
                ("Pin with bad I/O type (exp %s, got %s. Bank %s)"%(io_type, pin["I/O Type"], key))
        del pin["I/O Type"]
    # Rename key
    banks[key+"/"+io_type] = banks.pop(key)
print("Banks after removing I/O Type")
print_bank_summary(banks)
print("")

# The NA bank is massive because it contains all the VCC and GND pins
# Split this bank up into other banks

# First take out all the ground pins
banks["GND"] = filter_to_new_list(banks["NA/NA"], "Pin Name", r"GND")


# Then take out all the VCCINT pins
banks["VCCINT"] = filter_to_new_list(banks["NA/NA"], "Pin Name", r"VCCINT")


# Then take out all the PS Power pins
banks["PSVCC"] = filter_to_new_list(banks["NA/NA"], "Pin Name", r"(VCC_PS)|(PS_(.*)V)")

# Then the PL MGT Power Pins
banks["PLMGTV"] = filter_to_new_list(banks["NA/NA"], "Pin Name", r"MGT(A)*V")

# Then any other power pins
banks["OTHERVCC"] = filter_to_new_list(banks["NA/NA"], "Pin Name", r"VCC")

print("Banks after splitting up NA/NA")
print_bank_summary(banks)
print("")

# The PS DDR Bank is massive too
# Split it up in groups

banks["504/PSDDR_ADDR"] = filter_to_new_list(banks["504/PSDDR"], "Pin Name", r"PS_DDR_A")
banks["504/PSDDR_DQS"]  = filter_to_new_list(banks["504/PSDDR"], "Pin Name", r"PS_DDR_DQS")
banks["504/PSDDR_DQ"]   = filter_to_new_list(banks["504/PSDDR"], "Pin Name", r"PS_DDR_DQ")
banks["504/PSDDR_DM"]   = filter_to_new_list(banks["504/PSDDR"], "Pin Name", r"PS_DDR_DM")
banks["504/PSDDR_CK"]   = filter_to_new_list(banks["504/PSDDR"], "Pin Name", r"PS_DDR_CK") # Also includes CKE
banks["504/PSDDR_VCCO"] = filter_to_new_list(banks["504/PSDDR"], "Pin Name", r"VCCO")

print_bank_summary(banks)
print("")

# At this point the pins are still in the order that Xilinx gave us
# This ordering isn't great
# Sort the pins into a sensible order
# See the definition of bank_sort_key for the heavy lifting
# The only patchup is swapping P and N

for key, bank in banks.items():
    bank.sort(key=bank_sort_key)
    swap_ps_and_ns(bank)

for pin in banks["64/HP"]:
    print(pin["Pin Name"])

print('')

for pin in banks["224/GTH"]:
    print(pin["Pin Name"])
