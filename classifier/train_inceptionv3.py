#!/usr/bin/env python3

# Train a convolutional neural network to recognize good and bad coffee beans.
#
# Based on the InceptionV3 model and weights, with fine tuning following along "Fine-tune InceptionV3 on a new set of
# classes" in https://keras.io/applications/#usage-examples-for-image-classification-models
#
# For documentation on setup and usage, see /docs/coffee_classifier.md .
#
# Source code structure follows along the tutorial "Building powerful image classification models
# using very little data", see:
# - https://blog.keras.io/building-powerful-image-classification-models-using-very-little-data.html
# - https://gist.github.com/fchollet/0830affa1f7f19fd47b06d4cf89ed44d

from keras.applications.inception_v3 import InceptionV3
from keras.preprocessing import image
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Model, Sequential
from keras.layers import Dense, GlobalAveragePooling2D
from keras import backend as K

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


## (2) Set up the data sources.

# Input data sources.
train_data_dir = 'data/train'
validation_data_dir = 'data/validation'
nb_train_samples = 1367 # TODO: Determine this by counting files in train_data_dir.
nb_validation_samples = 440 # TODO: Determine this by counting files in validation_data_dir.

# Input image dimensions (scaled down from variable source sizes).
# 299x299 is the standard input size for InceptionV3, but we can configure it.
img_width, img_height = 150,150

# Number of iterations (epochs) when training the model.
# Each epoch utilizes all training images once.
epochs = 30

# Number of training images to process in each step of each epoch.
# Each epoch utilizes all training images, so  batch_size * steps = nb_train_samples. The model weights are updated
# after each step of an epoch.
batch_size = 16


# Data source for training images (augmentation used: multiple types).
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

# Data source for validation images (augmentation used: rescaling only).
test_datagen = ImageDataGenerator(rescale=1. / 255)
validation_generator = test_datagen.flow_from_directory(
    validation_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    class_mode='binary')


## (3) Set up the model (InceptionV3 with some additional layers).

# Create the base pre-trained model.
# The input_shape argument is in channels_last format, which has to be configured in ~/.keras/keras.json as:
#   "image_data_format": "channels_last"
base_model = InceptionV3(include_top=False, weights='imagenet', input_shape=(img_width, img_height, 3))

# Add a global spatial average pooling layer.
x = base_model.output
x = GlobalAveragePooling2D()(x)

# Add a fully-connected layer.
x = Dense(1024, activation='relu')(x)

# Add a logistic layer (for two classes only: good and bad beans).
predictions = Dense(2, activation='softmax')(x)

# Assemble the model we will train.
model = Model(inputs=base_model.input, outputs=predictions)


## (4) First training step: top layers
#
# This trains only the top layers (which were randomly initialized), freezing all convolutional InceptionV3 layers.

for layer in base_model.layers:
    layer.trainable = False

# Compile the model (should be done *after* setting layers to non-trainable).
model.compile(optimizer='rmsprop', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
# model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy'])

# Train the model on the new data for a few epochs.
model.fit_generator(
    train_generator,
    steps_per_epoch=nb_train_samples // batch_size,
    epochs=3,
    validation_data=validation_generator,
    validation_steps=nb_validation_samples // batch_size)


## (5) Second training step: fine-tuning upper convolutional layers from InceptionV3
#
# At this point, the top layers are well trained and we can start fine-tuning
# convolutional layers from inception V3. We will freeze the bottom N layers
# and train the remaining top layers.

# let's visualize layer names and layer indices to see how many layers
# we should freeze:
# for i, layer in enumerate(base_model.layers):
#    print(i, layer.name)

# We chose to train the top 2 inception blocks, i.e. we will freeze the first 249 layers and unfreeze the rest:
for layer in model.layers[:249]:
   layer.trainable = False
for layer in model.layers[249:]:
   layer.trainable = True

# Recompile the model for these modifications to take effect. We use SGD with a low learning rate.
from keras.optimizers import SGD
model.compile(optimizer=SGD(lr=0.0001, momentum=0.9), loss='categorical_crossentropy', metrics=['accuracy'])

# We train our model again (this time fine-tuning the top 2 inception blocks alongside the top Dense layers).
model.fit_generator(
    train_generator,
    steps_per_epoch=nb_train_samples // batch_size,
    epochs=30,
    validation_data=validation_generator,
    validation_steps=nb_validation_samples // batch_size)



# Save the training results to a file.
model.save_weights('train_inceptionv3.weights.current.h5')
# TODO Save to classifier_weights.yyyy-mm-dd.nn.h5 based on the current date and a file count per day.
