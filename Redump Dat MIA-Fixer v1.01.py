## Import modules and get basic program config set up.

# Set up logging.
import os
current_working_directory = os.getcwd()
new_folder = "logs"
logs_output_folder = os.path.join(current_working_directory, new_folder)
os.makedirs(logs_output_folder, exist_ok=True)

from datetime import datetime
timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

import logging
logging.basicConfig(level=logging.DEBUG,
                    filename=f"logs\mia-fix({timestamp}).log",
                    format="%(message)s")
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_logger = logging.getLogger()
console_logger.addHandler(console_handler)

logging.debug(f"Program start: {timestamp}\n")

# Print unhandled exceptions to log file.
import sys
def custom_except_handler(exc_type, exc_value, exc_traceback):
    logging.exception('', exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = custom_except_handler

# More graceful Ctrl+C handling.
import signal
def custom_sigint_handler(signalnum, frame):
    logging.info("\n\nCtrl-C was pressed. Exiting program.\n\n")
    sys.exit()
signal.signal(signal.SIGINT, custom_sigint_handler)

import re
import urllib.request, urllib.parse, urllib.error

try:
    from bs4 import BeautifulSoup
    from lxml import etree
except Exception:
    logging.error(
        """Error: Program requires external modules 'BeautifulSoup' and 'lxml' to run properly.\n\nInstallation instructions for 'BeautifulSoup' can be found at:\nhttps://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-beautiful-soup\n\nand installation instructions for 'lxml' can be found at:\nhttps://lxml.de/installation.html""")
    input("\nPress enter to exit.\n")
    quit()


## Gather input files from user (accepts drag & drop or manual input.)
## 'inputted_dats_list' variable will be a list of the full filepaths
## for each user-inputted DAT.

user_input = sys.argv[1:]
if len(user_input) == 0:
    user_input = input("Please enter individual file or folder path: ")
logging.debug(f"user_input = {user_input}")
if not type(user_input) is list:
    user_input = [user_input.strip('"')]
logging.debug(f"--Number of files/folders to check: {len(user_input)}")

inputted_dats_list = list()

# os.walk method takes a directory path as input, and then recursively
# iterates through each directory within, returning a 3-item tuple for
# each one. Tuple is composed of the directory path being "walked," a
# list of the smaller directories within that path and a list of the
# files within as well.
logging.info("\n**Checking...")
for inp_path in user_input:
    if os.path.isdir(inp_path):
        for path, dirs, files in os.walk(inp_path):
            for filename in files:
                if filename.endswith(".dat"):
                    full_path = os.path.join(path, filename)
                    inputted_dats_list.append(full_path)
    elif os.path.isfile(inp_path):
        if inp_path.endswith(".dat"):
            inputted_dats_list.append(inp_path)

inputted_dats_list = sorted(inputted_dats_list, key=str.casefold)

if len(inputted_dats_list) == 0:
    logging.error("\nInvalid path specified. No .dat files found.")
    input("\nPress enter to exit.")
    quit()
elif len(inputted_dats_list) == 1:
    logging.info(f"{len(inputted_dats_list)} DAT file detected.")
else:
    logging.info(f"{len(inputted_dats_list)} DAT files detected.")

logging.debug("\ninputted_dats_list =")
for dat in inputted_dats_list:
    logging.debug(dat)
logging.debug(f"---Total files: {len(inputted_dats_list)}")


# For clarity, from this point forward any variables starting with
# 'dat_' refer to something regarding the user's inputted DAT files and
# any variables starting with 'mialist_' are referring to something in
# the online MIA lists in the Redump Wiki. Several variables below will
# be used a lot, and I have camel-cased those to make them more notable.


## Extract different substrings from the full filepath string of each
## inputted-DAT file. Create dictionary of each part, with the keys
## being just the filename of each .dat file.

logging.debug("\n\n**Constructing dictionary of substrings from user-inputted DAT files...")

dat_Dict = dict()

max_filename_length = 0  # To be used later for console output formatting.

for dat_Fullpath in inputted_dats_list:
    dat_Filename = os.path.split(dat_Fullpath)[1]
    if len(dat_Filename) > max_filename_length:
        max_filename_length = len(dat_Filename)
    # Extract system name, taking into account unique naming schemes of
    # fixdats, BIOS dats, and several popular custom dats.
    dat_SystemName = dat_Filename.replace("_", " ")
    for prefix_check in ["fixdat", "fix"]:
        dat_SystemName = re.sub(prefix_check, "", dat_SystemName, flags=re.IGNORECASE)
        dat_SystemName = dat_SystemName.lstrip()
    if "BIOS" in dat_SystemName:
        dat_SystemName = dat_SystemName.split(" Datfile")[0]
        dat_SystemName += " Images"  # To match how named online with MIA lists
    else:
        dat_SystemName = dat_SystemName.split(" - ")[:-1]
        dat_SystemName = ' - '.join(dat_SystemName)

    dat_Dict[dat_Filename] = (dat_SystemName, dat_Fullpath)

logging.debug("\ndat_Dict[dat_Filename] = (dat_SystemName, dat_Fullpath):")
logging.debug("--------------------------------------------------------")
for key in dat_Dict:
    logging.debug(f"{key} : {dat_Dict[key]}")
logging.debug(f"---Total dictionary items: {len(dat_Dict)}\n")


## Extract important pieces of info for each system from the main "MIA
## Lists" page on the Redump Wiki, and save this info in a dictionary,
## with the keys being the name of each system as its listed.

logging.info("\n**Accessing online MIA Lists...")
logging.debug("url = http://wiki.redump.org/index.php?title=MIA_Lists")

url_domain = "http://wiki.redump.org"
try:
    url_handle = urllib.request.urlopen(url_domain+'/index.php?title=MIA_Lists')
except Exception:
    logging.error("'http://wiki.redump.org/index.php?title=MIA_Lists' failed to load. Please try again.\n\n")
    quit()

logging.debug('\n**Creating "BeautifulSoup"...')
soup = BeautifulSoup(url_handle, "html.parser")

#logging.debug(f"\n{soup.prettify()}")

logging.debug("\n\n**Constructing dictionary of system information from the online MIA lists...")

mialist_Dict = dict()

soup_section = soup.find(id='Systems_with_MIAs')
li_tags_list = soup_section.parent.next_sibling.next_sibling.select('li')
for tag in li_tags_list:
    mialist_SystemName = tag.get_text().rstrip()
    mialist_Category = "Systems with MIAs"
    mialist_Link = tag.a.get('href')
    mialist_Dict[mialist_SystemName] = (mialist_Category, mialist_Link)

soup_section = soup.find(id='Systems_with_no_reported_MIAs')
li_tags_list = soup_section.parent.next_sibling.next_sibling.select('li')
for tag in li_tags_list:
    mialist_SystemName = tag.get_text().rstrip()
    mialist_Category = "Systems with no MIAs"
    if tag.find('a'):
        mialist_Link = tag.a.get('href')
    else:
        mialist_Link = None
    mialist_Dict[mialist_SystemName] = (mialist_Category, mialist_Link)

logging.debug(
"\nmialist_Dict[mialist_SystemName] = (mialist_Category, mialist_Link):")
logging.debug(
"--------------------------------------------------------------------")
for key in mialist_Dict:
    logging.debug(f"{key} : {mialist_Dict[key]}")
logging.debug(f"---Total dictionary items: {len(mialist_Dict)}\n")


## Start comparing each user-inputted DAT against the systems listed
## in the online MIA lists. This section is set up like a series of
## filters that filters out and categorizes DATs into lists based on
## what info is available for them in the MIA lists, ultimately
## resulting in there only being DATs left that have MIA discs needing
## to be tagged.
##
## (Note: This section ended up needing a lot more "for" loops and "if"
## statements, and different lists and dictionaries than I had expected.
## May come back later and rework using class instances and True/False
## flags instead.)


# Console and log output each handled differently for this next
# section. Log output is much more verbose. Console output has fancy
# tricks employed to create a special aligned column on the right, and
# also replace lines rapidly as they print.

logging.info("\n**Now processing DATs...")

logging.debug("\nDAT Processing Breakdown:")
logging.debug("-------------------------")

# Prepare everything needed for giant filter sequence.
dats_updated_previously = list()
systems_no_mialist = list()
systems_no_link = list()
systems_failed_link = list()
systems_empty_list = list()

dats_all_discs_unfound = list()
dats_some_discs_found = list()
dats_all_discs_found = list()

dats_MadeItThrough = list()

dats_outdated = list()
mialists_outdated = list()
dat_mialist_version_match = list()
mialist_version_not_present = list()

total_mia_discs_count = dict()
unfound_mia_discs_count = dict()
updated_mia_discs_count = dict()

# For console output formatting later (final program results section)
max_unfound_discs_syst_name_length = 0

# ANSI codes to allow moving between and replacing printed lines.
PREV_LINE_START = '\033[F'
LINE_CLEAR = '\x1b[2K'
os.system("")  # Makes ANSI codes work, but also causes weird glitch,
# where I had to add a space to the end of every printed line. You'll
# also see this figured into line length check below.

def prep_cursor_to_replace_prev_line(last_printed_string):
    """When doing carriage returns and ANSI code line movement, these commands don't take word wrap into account, so if window is too small, text can overflow and mess up your cursor navigation and resulting print output. This function deletes any overflow, and returns the cursor to where it would have been otherwise."""
    term_size = os.get_terminal_size().columns
    ratio = term_size / len(last_printed_string+" ")
    number_of_lines_string_now_spans = int(1/ratio) + 1
    if ratio < 1.00:
        for lines_to_back_up in range(number_of_lines_string_now_spans):
            print(PREV_LINE_START, end=LINE_CLEAR)
    else:
       print(PREV_LINE_START, end=LINE_CLEAR)
    # Cursor now prepared for new 'print_string' right after function ends.


# Commence giant filter sequence
for dat_Filename, (dat_SystemName, dat_Fullpath) in list(dat_Dict.items()):
    # First need to determine how much to indent each DAT's printed
    # update progress, based on its name length. Uses variable from
    # DAT dictionary creation before.
    column_alignment_position = max_filename_length + 2
    indent_needed = column_alignment_position - len(dat_Filename)
    indent = " " * indent_needed

    print_string = f"     '{dat_Filename}'{indent}Check in progress..."
    print(print_string, end=' \n')

    # 1st filter: Inputted DAT file has already been updated.
    if dat_Filename.endswith(" [mia-fixed].dat"):
        dats_updated_previously.append(dat_Filename)
        logging.debug(f"\nFile '{dat_Filename}' was updated previously.\n...")
        prep_cursor_to_replace_prev_line(print_string)
        print_string = f"     '{dat_Filename}'{indent}Check in progress... No update needed."
        print(print_string, end=' \n')
        continue

    # 2nd filter: Inputted DAT file has no MIA list listed.
    if dat_SystemName not in list(mialist_Dict.keys()):
        systems_no_mialist.append(dat_SystemName)
        logging.debug(f"\nFile '{dat_Filename}' could not be matched with any MIA list.\n...")
        prep_cursor_to_replace_prev_line(print_string)
        print_string = f"     '{dat_Filename}'{indent}Check in progress... No update needed."
        print(print_string, end=' \n')
        continue

    for mialist_SystemName, (mialist_Category, mialist_Link) in list(mialist_Dict.items()):
        if dat_SystemName == mialist_SystemName:

            # 3rd filter: Inputted DAT file's MIA list has no active hyperlink.
            if mialist_Link == None:
                systems_no_link.append(mialist_SystemName)
                logging.debug(f"\nSystem '{dat_SystemName}' is listed on the systems page, but has no actively-linked MIA list.\n...")
                prep_cursor_to_replace_prev_line(print_string)
                print_string = f"     '{dat_Filename}'{indent}Check in progress... No update needed."
                print(print_string, end=' \n')
                continue


## Systems without MIA lists are filtered out and set aside.
## Now (try to) open each link and check for discs.
            try:
                logging.debug(f"\nSystem '{dat_SystemName}' has an active MIA list. Opening '{url_domain+mialist_Link}'...")
                url_handle = urllib.request.urlopen(url_domain+mialist_Link)

            # 4th filter: Inputted DAT file's MIA list is failing to load.
            except Exception:
                logging.debug(f"MIA list for '{mialist_SystemName}' isn't loading. Continuing to next system.\n...")
                prep_cursor_to_replace_prev_line(print_string)
                print_string = f"     '{dat_Filename}'{indent}Check in progress... Error: MIA list failed to load."
                print(print_string, end=' \n')
                systems_failed_link.append(mialist_SystemName)
                continue

            logging.debug('Creating "BeautifulSoup"...')
            soup = BeautifulSoup(url_handle, "html.parser")
            #logging.debug(f"{soup.prettify()}")

            mialist_version_section = soup.find_all(
                string=re.compile("dat version", re.IGNORECASE))
            if len(mialist_version_section) < 1:
                mialist_version = None
                mialist_timestamp = None
                mialist_version_not_present.append(dat_Filename)
            else:
                mialist_version = mialist_version_section[0].next_element.strip()
                mialist_timestamp = mialist_version.split('(')[-1].rstrip(')')

            mia_Discs_List = list()

            # Account for alternate formatting styles in MIA lists
            # "Preformatted text" style
            if soup.find('pre'):
                discs_section = soup.find('pre')
                mia_Discs_List = discs_section.get_text().rstrip().split('\n')

            # "Table" style
            elif soup.find('table'):
                table_header = soup.find('th', string=re.compile("Title"))
                table_rows_list = table_header.parent.parent.select('tr')
                for row in table_rows_list[1:]:
                    table_data = row.find('td')
                    mia_Discs_List.append(table_data.get_text().strip())

            # 5th (final) filter: System's MIA list is empty.
            elif not soup.find('pre') or soup.find('table'):
                logging.debug(f"MIA List Version: {mialist_version}")
                logging.debug(f"This system has no MIA discs listed.\n...")
                prep_cursor_to_replace_prev_line(print_string)
                print_string = f"     '{dat_Filename}'{indent}Check in progress... No update needed."
                print(print_string, end=' \n')
                systems_empty_list.append(mialist_SystemName)
                continue

## With list of MIA discs extracted, start checking DAT and applying
## 'mia="yes"' attribute to each disc that needs it.
            prep_cursor_to_replace_prev_line(print_string)
            print_string = f"     '{dat_Filename}'{indent}Check in progress..... Updating....."
            print(print_string, end=' \n')
            logging.debug(f"Opening '{dat_Filename}'...\nCreating \"ElementTree\"...")

            with open(dat_Dict[dat_Filename][1], encoding='utf-8') as file_handle:
                tree = etree.parse(file_handle)
                root = tree.getroot()
                #logging.debug(f"{etree.tostring(tree, pretty_print=True).decode()}")

                # To indicate in program results if DAT or MIA list
                # needs updated.
                dat_timestamp = root.find('header').find('version').text
                dat_timestamp = dat_timestamp.replace(':', '-')  # For custom DATs
                if dat_timestamp < mialist_timestamp:
                    dats_outdated.append(dat_Filename)
                elif mialist_timestamp < dat_timestamp:
                    mialists_outdated.append(dat_Filename)
                elif mialist_timestamp == dat_timestamp:
                    dat_mialist_version_match.append(dat_Filename)

                logging.debug(f"MIA List Version: {mialist_version}")
                logging.debug(f"DAT Version: {dat_SystemName} ({dat_timestamp})")
                logging.debug("The following discs are being updated...")

                for disc in mia_Discs_List:
                    print_string = f"          {disc}"
                    print(print_string, end=' \n')
                    total_mia_discs_count[dat_Filename] = total_mia_discs_count.get(dat_Filename, 0) + 1
                    disc_name = disc.replace('&', '&amp;')
                    game_element = root.find(f'game[@name="{disc}"]')

                    if game_element == None:
                        unfound_mia_discs_count[mialist_SystemName] = unfound_mia_discs_count.get(mialist_SystemName, 0) + 1
                        # For aligning columns in printed program results later
                        if len(mialist_SystemName) > max_unfound_discs_syst_name_length:
                            max_unfound_discs_syst_name_length = len(mialist_SystemName)
                        if dat_Filename in mialists_outdated:
                            logging.debug(f"    {disc}    ***Disc could not be found in inputted DAT. (MIA list may need updated)***")
                        elif dat_Filename in dats_outdated:
                            logging.debug(f"    {disc}    ***Disc could not be found in inputted DAT. (DAT may need updated)***")
                        else:
                            logging.debug(f"    {disc}    ***Disc could not be found in inputted DAT.***")
                        updated_mia_discs_count[dat_Filename] = updated_mia_discs_count.get(dat_Filename, 0)
                        prep_cursor_to_replace_prev_line(print_string)
                        continue

                    else:
                        #logging.debug(f"game_element = \n{etree.tostring(game_element, pretty_print=True).decode()}")
                        for rom in game_element.findall('rom'):
                            if not rom.get('name').endswith(".cue"):
                                rom.set('mia', 'yes')
                        logging.debug(f"    {disc}")
                        updated_mia_discs_count[dat_Filename] = updated_mia_discs_count.get(dat_Filename, 0) + 1
                        prep_cursor_to_replace_prev_line(print_string)
                        continue

                # Disc-by-disc check sequence is done, so need to back
                # cursor up an additional line to replace printed string
                # before that, so assign 'print_string' to match that
                # previous line.
                print_string = f"     '{dat_Filename}'{indent}Check in progress..... Updating....."

                # Last minute stats gathering for later program results
                # output.
                logging.debug(f"        --{updated_mia_discs_count[dat_Filename]}/{total_mia_discs_count[dat_Filename]} discs updated.")
                if updated_mia_discs_count[dat_Filename] < 1:
                    dats_all_discs_unfound.append(dat_Filename)
                    prep_cursor_to_replace_prev_line(print_string)
                    print_string = f"     '{dat_Filename}'{indent}Check in progress..... Updating....... Done."
                    print(print_string, end=' \n')
                    continue
                elif updated_mia_discs_count[dat_Filename] < total_mia_discs_count[dat_Filename]:
                    dats_some_discs_found.append(dat_Filename)
                elif updated_mia_discs_count[dat_Filename] == total_mia_discs_count[dat_Filename]:
                    dats_all_discs_found.append(dat_Filename)

                # Save edited XML to new DAT file.
                dat_Fullpath_no_ext = dat_Fullpath.removesuffix(".dat")
                tree.write(f"{dat_Fullpath_no_ext} [mia-fixed].dat", xml_declaration=True, encoding='UTF-8')
                prep_cursor_to_replace_prev_line(print_string)
                print_string = f"     '{dat_Filename}'{indent}Check in progress..... Updating....... Done."
                print(print_string, end=' \n')
                dats_MadeItThrough.append(dat_Fullpath)
                file_handle.close()


## Operation results...

logging.debug("\n\n\n--------------------------")
logging.debug("Program Results Overview:")
logging.debug("--------------------------")

# Stuff printed to console & log file:
total_discs_updated = sum(list(updated_mia_discs_count.values()))

if len(dats_MadeItThrough) == 0:
    print("\n**No DATs have been updated. See log for more details.**")
    logging.debug('\n**No DATs have been updated. See "DAT Processing Breakdown" section above for details.**')
elif len(dats_MadeItThrough) == 1 and total_discs_updated == 1:
    logging.info("\n\n**1 DAT file and 1 disc entry have been updated.**")
elif len(dats_MadeItThrough) == 1 and total_discs_updated != 1:
    logging.info(f"\n\n**1 DAT file and {total_discs_updated} disc entries have been updated.**")
else:
    logging.info(f"\n\n**{len(dats_MadeItThrough)} DAT files and {total_discs_updated} disc entries have been updated.**")

if len(unfound_mia_discs_count) > 0:
    logging.error("\n\nNote: MIA lists for the following systems had discs that could not be found in their corresponding DAT (usually due to the discs having been added, renamed, or removed since either the MIA list or inputted DAT was last updated):")

    column_alignment_position = max_unfound_discs_syst_name_length + 5

    for syst_name, discs_count in list(unfound_mia_discs_count.items()):
        indent_needed = column_alignment_position - len(syst_name)
        logging.error(f"     {syst_name}{str(discs_count).rjust(indent_needed)} disc(s)")
    print("\nPlease see log for more details.")
    logging.debug('\nPlease see "DAT Processing Breakdown" section above for specific discs.')

# Printed to log file only.
logging.debug(f"""\n\n--Miscellaneous Statistics--
    Total DATs Inputted: {len(inputted_dats_list)}
        Updated previously: {len(dats_updated_previously)}
        Not listed on 'MIA Lists' page: {len(systems_no_mialist)}
        Listed but had no hyperlink: {len(systems_no_link)}
        Hyperlink failed to open: {len(systems_failed_link)}
        MIA list was empty: {len(systems_empty_list)}
        No listed discs found in DAT: {len(dats_all_discs_unfound)}
        Some listed discs found in DAT: {len(dats_some_discs_found)}
        All listed discs found & updated: {len(dats_all_discs_found)}

    DAT / MIA List Version Comparisons:
        Outdated DATs: {len(dats_outdated)}
        Outdated MIA lists: {len(mialists_outdated)}
        DAT/MIA list version matches: {len(dat_mialist_version_match)}
        MIA lists without version indicated: {len(mialist_version_not_present)}

    Total MIA Discs checked: {sum(total_mia_discs_count.values())}
        MIA discs not found in DATs: {sum(unfound_mia_discs_count.values())}
        MIA discs successfully found in DATs: {sum(updated_mia_discs_count.values())}

See \"DAT Processing Breakdown\" section above for details.""")

# Final stuff printed to both console & log file:
if len(dats_MadeItThrough) == 1:
    logging.info("\n\nOriginal version of updated DAT has been retained as a backup. Would you like to delete it?")
elif len(dats_MadeItThrough) > 1:
    logging.info("\n\nOriginal versions of updated DATs have been retained as backups. Would you like to delete them?")
while True:
    if len(dats_MadeItThrough) == 0:
        break
    delete_prompt = input("    y/n: ")
    if delete_prompt == "y":
        for dat_Fullpath in dats_MadeItThrough:
            os.remove(dat_Fullpath)
        logging.info(f"\n    {len(dats_MadeItThrough)} file(s) deleted.")
        break
    elif delete_prompt == "n":
        logging.info("\n    File(s) retained.")
        break
    else:
        print("Please only enter 'y' for yes or 'n' for no.")
        continue


timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
logging.debug(f"\n\nProgram end: {timestamp}")

input('\n\nPress enter to exit...\n')
