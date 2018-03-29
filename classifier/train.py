#!/usr/bin/env python3

# Train a convolutional neural network to recognize good and bad coffee beans.
#
# For documentation on setup and usage, see /docs/coffee_classifier.md .
#
# Source code structure follows along the tutorial "Building powerful image classification models
# using very little data", see:
# - https://blog.keras.io/building-powerful-image-classification-models-using-very-little-data.html
# - https://gist.github.com/fchollet/0830affa1f7f19fd47b06d4cf89ed44d

from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras import backend as K

from model import create_model

import numpy as np
import tensorflow as tf
import random as rn


## (1) Ensure reproducible training results.
#
# Follows this FAQ entry (except that it keeps multi-threading in place for training performance reasons):
# https://keras.io/getting-started/faq/#how-can-i-obtain-reproducible-results-using-keras-during-development

# Make Python hash-based operations reproducible. See:
# https://docs.python.org/3.4/using/cmdline.html#envvar-PYTHONHASHSEED
# https://github.com/keras-team/keras/issues/2280#issuecomment-306959926
import os
os.environ['PYTHONHASHSEED'] = '0'

# Start Numpy generated random numbers from a well-defined initial state.
np.random.seed(42)

# Start core Python generated random numbers from a well-defined state.
rn.seed(12345)

# Force TensorFlow to use single thread, as multiple ones are a source of non-reproducible results.
# For details, see: https://stackoverflow.com/q/42022950
session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)

# Start Tensorflow generated random numbers from a well-defined initial state.
# For details, see: https://www.tensorflow.org/api_docs/python/tf/set_random_seed
tf.set_random_seed(1234)

# Activate the config built above (single thread, fixed random seed).
sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
K.set_session(sess)


## (2) Set up and run the training.

# Input data sources.
train_data_dir = 'data/train'
validation_data_dir = 'data/validation'
nb_train_samples = 1367 # TODO: Determine this by counting files in train_data_dir.
nb_validation_samples = 440 # TODO: Determine this by counting files in validation_data_dir.

# Input image dimensions (scaled down from variable source sizes).
img_width, img_height = 150, 150

# Number of iterations (epochs) when training the model.
# Each epoch utilizes all training images once.
epochs = 30

# Number of training images to process in each step of each epoch.
# Each epoch utilizes all training images, so  batch_size * steps = nb_train_samples. The model weights are updated
# after each step of an epoch.
batch_size = 16

# Build the model as defined in model.py.
model = create_model(img_width, img_height)
model.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

# Setup to generate validation images (augmentation used: multiple types).
train_datagen = ImageDataGenerator(
    rescale=1. / 255,
    shear_range=0.2,
    rotation_range=180,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True)
train_generator = train_datagen.flow_from_directory(
    train_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    class_mode='binary')

# Setup to generate validation images (augmentation used: rescaling only).
test_datagen = ImageDataGenerator(rescale=1. / 255)
validation_generator = test_datagen.flow_from_directory(
    validation_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    class_mode='binary')

# Actual training process.
model.fit_generator(
    train_generator,
    steps_per_epoch=nb_train_samples // batch_size,
    epochs=epochs,
    validation_data=validation_generator,
    validation_steps=nb_validation_samples // batch_size)

# Save the training results to a file.
model.save_weights('classifier_weights.current.h5')
# TODO Save to classifier_weights.yyyy-mm-dd.nn.h5 based on the current date and a file count per day.
