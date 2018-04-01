import cv2
import numpy as np

## Configuration sectionself.
resolution = 8.0 # px/mm

img_width  = 1200
img_height = 1600
# TODO Determine the image dimensions from the given image.

# Output image width and height.
# (Output images should cover a physical size of 14.35*14.35 mm always.)
img_target_size = int(14.35 * resolution)

# Load the image.
# TODO Pass image filename from command line.
img = cv2.imread('coffee.jpg')

# Convert to grayscale.
img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Smooth the image to avoid noises.
# TODO Blur radius should be much higher (factor 200 for a 1200x1600 image), and adapted to the image size.
img_gray = cv2.medianBlur(img_gray, 5)

# Apply adaptive threshold.
# Reference: https://docs.opencv.org/3.4.0/d7/d1b/group__imgproc__misc.html#ga72b913f352e4a1b1b397736707afcde3
# TODO Calculate the adaptiveThreshold blocksize parameter as 25% of larger side of image.
img_bw = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 401, 0)

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

    # TODO Grow the bounding box to a square of the right (resolution dependent) "standard size".
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

    # TODO If the bounding box is smaller than the "standard size", pad it with white background.

    # Save the ROI as image.
    # TODO Derive the output file names from input file names.
    cv2.imwrite("bean_" + str(img_num).zfill(2) + ".png", roi)
    img_num += 1

# Save the b&w image with bounding boxes as visual control.
# TODO Only do this when required by a --debug command line argument.
cv2.imwrite('coffee.rois.png', img_bw)
