"""This is example code to show how to use the bean classifier.

Example runs:

  python classify.py --image data/validation/good/Set04-good.10.35.png
  python classify.py --image data/validation/bad/Set05-bad.09.27.png
"""
import argparse
import numpy as np
import sys

from keras.preprocessing import image
from PIL import Image

from model import create_model

target_size = (150, 150)


def predict(nn, img, target_size):
  """Run model prediction on image
  Args:
    model: keras model
    img: PIL format image
    target_size: (w,h) tuple
  Returns:
    list of predicted labels and their probabilities
  """
  if img.size != target_size:
    img = img.resize(target_size)

  x = image.img_to_array(img)
  x = np.expand_dims(x, axis=0)
  x /= 255.0
  return nn.predict(x)


if __name__=="__main__":
  a = argparse.ArgumentParser()
  a.add_argument("--image", help="path to image")
  args = a.parse_args()

  if args.image is None:
    a.print_help()
    sys.exit(1)

  png = Image.open(args.image)

  # PNG images have an alpha channel that we don't need. Remove it.
  img = Image.new("RGB", png.size, (255, 255, 255))
  img.paste(png, mask=png.split()[3])


  # Create the neural network and load its weights.
  nn = create_model(target_size[0], target_size[1])
  nn.load_weights('classifier_weights.h5')

  preds = predict(nn, img, target_size)
  print(preds)
