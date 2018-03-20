"""This is example code to show how to use the bean classifier."""
import cv2
import numpy as np

from keras.preprocessing.image import img_to_array
from model import create_model

# Create the neural network and load its weights.
nn = create_model(150, 150)
nn.load_weights('bean_classifier.h5')

classify_dir = 'data/classify'

# load an image and resize it accordingly.
image_path = '/Users/ielashi/dev/coffee-cobra/classifier/data/validation/bad/Set05-bad.09.29.png'
image = cv2.imread(image_path)
image = cv2.resize(image, (150, 150))
image = img_to_array(image)

# Predict if the image is of a good bean or a bad bean (0 is bad, 1 is good)
print(nn.predict(np.array([image])))
