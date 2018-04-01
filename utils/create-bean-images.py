#!/usr/bin/env python3

"""create-bean-images

Usage:
  create-bean-images.py --resolution=<res> [--debug] <file>
  create-bean-images.py (-h | --help)
  create-bean-images.py --version

Options:
  -r <res>, --resolution=<res>  Image file resolution in px/mm.
  -d, --debug                   Also write an image showing the applied thresholding and recognized objects.
  -h, --help                    Show this screen.
  --version                     Show version.

"""
import cv2
import numpy as np
from docopt import docopt


#### SECTION 1: INPUT

arguments = docopt(__doc__, version='create-bean-images 0.1')
# print(arguments)

resolution = float(arguments['--resolution']) # px/mm

# Output image width and height.
# (Output images should cover a physical size of 14.35*14.35 mm always.)
img_target_size = int(14.35 * resolution)

filename = arguments['<file>']
filename_beans_prefix = 'coffee.bean' # TODO Derive the proper prefix part from the input filename.
filename_rois = filename + '.debug.jpg' # TODO: Better derived structure, without two file extensions inside.

# Load the image.
img = cv2.imread(filename)

# Determine the image dimensions.
img_height, img_width  = img.shape[:2]
# print("DEBUG: img_height = ", img_height, ", img_width =  ", img_width)

# Block size for OpenCV adaptive thresholding. (Must be an uneven number.)
thresh_blocksize = int( max(img_height, img_width) * 0.25 )
if thresh_blocksize % 2 == 0: thresh_blocksize += 1


#### SECTION 2: IMAGE PROCESSING

# Convert to grayscale.
img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Smooth the image to avoid noises.
# TODO Blur radius should be much higher (factor 200 for a 1200x1600 image), and adapted to the image size.
img_gray = cv2.medianBlur(img_gray, 5)

# Apply adaptive threshold.
# Reference: https://docs.opencv.org/3.4.0/d7/d1b/group__imgproc__misc.html#ga72b913f352e4a1b1b397736707afcde3
img_bw = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, thresh_blocksize, 0)

# Find the contours.
# Reference: https://docs.opencv.org/3.4.0/d3/dc0/group__imgproc__shape.html#ga17ed9f5d79ae97bd4c7cf18403e1689a
contours = cv2.findContours(img_bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[1]

# Convert the image from gray to color mode, so we can draw in color on it later.
img_bw = cv2.cvtColor(img_bw, cv2.COLOR_GRAY2BGR)

# For each contour, find the bounding box, draw it, save it.
img_num = 1
for cnt in contours:
    x,y,w,h = cv2.boundingRect(cnt)

    # Draw a green bounding box around the contour.
    cv2.rectangle(img_bw, (x,y), (x+w, y+h), (0,255,0), 2)

    # Skip fragments smaller than beans.
    # TODO Adapt the pixel count threshold based on image dimensions.
    if (h*w < 3000): continue

    # Grow the bounding box to img_target_size * img_target_size (where possible).
    center_x = x + w//2
    center_y = y + h//2
    x = max(center_x - (img_target_size//2), 0)
    y = max(center_y - (img_target_size//2), 0)
    w = img_target_size
    if (x+w > img_width): w = img_width - x
    h = img_target_size
    if (y+h > img_height): h = img_height - y

    # Extract the bounding box content ("region of interest", hopefully a bean)
    roi = img[y:y+h, x:x+w]

    # TODO If the bounding box is smaller than img_target_size * img_target_size, pad it.

    # Save the ROI as JPEG image. (Image format is chosen by extension. ".png" also works.)
    # TODO Use a high quality value for the JPG.
    cv2.imwrite(filename_beans_prefix + str(img_num).zfill(2) + ".jpg", roi)
    img_num += 1

# Save the b&w image with bounding boxes as visual control.
if arguments['--debug']:
    cv2.imwrite(filename_rois, img_bw)
    # TODO Also write the full-color image, with marked bounding boxes.
