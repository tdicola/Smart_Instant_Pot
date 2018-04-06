# Smart Instant Pot Evaluation Script
# This will process a CSV file with input images and their expected digit
# detection.  Each image will be processed by the detection code and the actual
# result compared to the expected to generate statistics on how well the
# algorithm is working.
import argparse
import csv
import os

import cv2

import smart_instant_pot.detector as detector
import smart_instant_pot.digit_reader as digit_reader


# Setup command line arguments.
parser = argparse.ArgumentParser(description='Smart Instant Pot Evaluation')
parser.add_argument('input_csv',
                    help='input CSV with columns for input image and expected result')
parser.add_argument('result_csv',
                    nargs='?',
                    help='optional output CSV with columns for input image, expected, actual pot detected (boolean), actual digit value (string)')
parser.add_argument('--panel_image',
                    metavar='FILENAME',
                    default='/home/jovyan/work/test_images/pi_control_panel.jpg',
                    help='control panel template for detection (default is an image from Pi camera with wide angle lens)')
args = parser.parse_args()

# Check input file exists and load all the input image filenames and expected
# results from the CSV.
if not os.path.isfile(args.input_csv):
    raise RuntimeError('Failed to find input CSV file!')
with open(args.input_csv, 'r') as infile:
    reader = csv.reader(infile)
    input_data = [row for row in reader]
print('Processing {0} images...'.format(len(input_data)), end='')

# Change to the directory of the CSV so images are loaded relative to its location.
start_dir = os.getcwd()
os.chdir(os.path.dirname(args.input_csv))

# Setup detector and digit reader.
if not os.path.isfile(args.panel_image):
    raise RuntimeError('Failed to find control panel template image!')
pot_detector = detector.Detector(cv2.imread(args.panel_image))
pot_digit_reader = digit_reader.DigitReader()

# Loop through the input images and run detection logic to compute actual result.
results = []
found_pot = 0
correct_digits = 0
for i, row in enumerate(input_data):
    # Print a dot every 10 images to show the script is still running.
    if i % 10 == 0:
        print('.', end='')
    image_file, expected = row
    # Look for the pot control panel in the input image.
    panel_image = pot_detector.detect_panel(cv2.imread(image_file))
    if panel_image is None:
        results.append((image_file, expected, False, None))
        continue
    # Found a control panel, now detect the digits and save result.
    found_pot += 1
    digits = pot_digit_reader.read_digits(panel_image)
    if digits == expected:
        correct_digits += 1
    results.append((image_file, expected, True, digits))
print()

# Print stats of the detection results.
total_input = len(input_data)
found_pot_percent = found_pot / total_input * 100.0
correct_digits_percent = correct_digits / total_input * 100.0
print('Found the pot in {0} images: {1:0.2f}%'.format(found_pot, found_pot_percent))
print('Correctly detected digits in {0} images: {1:0.2f}%'.format(correct_digits,
    correct_digits_percent))

# Write output results if a file was specified.
if args.result_csv is not None:
    # Change back to the directory the script was run to create output relative to it.
    os.chdir(start_dir)
    with open(args.result_csv, 'w') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(results)
    print('Wrote results to: {0}'.format(args.result_csv))
