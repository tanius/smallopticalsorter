import cv2
import numpy as np

# Load the image
img = cv2.imread('coffee.jpg') # TODO pass image filename from command line

# convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# smooth the image to avoid noises
gray = cv2.medianBlur(gray, 5)

# Apply adaptive threshold
thresh = cv2.adaptiveThreshold(gray, 255, 1, 1, 11, 2)

# Find the contours
contours,hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

# For each contour, find the bounding rectangle and draw it
for cnt in contours:
    x,y,w,h = cv2.boundingRect(cnt)
    cv2.rectangle(img, (x,y), (x+w,y+h), (0, 255, 0), 2) # TODO saving the image instead of painting the bounding box

# Finally show the image
cv2.imshow('img', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
