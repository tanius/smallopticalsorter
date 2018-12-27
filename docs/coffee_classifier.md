# Coffee Classifier Documentation


## 1. Installation

The following instructions apply to Ubuntu Linux 17.10.


### 1.1. Install required software

We install requirements with `pip`, the Python package management system. (So unfortunately there will be redundancy if you already have OpenCV etc. installed with Ubuntu packages on your system.)

The file [`requirements.txt`](https://github.com/edgeryders/coffee-cobra/blob/master/classifier/requirements.txt) informs `pip` about the software versions required for this installation. Updated versions _should_ work, too, but may not.

The installation also contains `jupyter`, a Python IDE to work with annotated source code ("notebooks"). This is used in `Coffee Classifier Trainer.ipynb`. However, this is optional, as you can always extract the actual Python source code itself from that file and run it.


1. Install Python 3.x and pip for Python 3.x:

        sudo apt install python3
        sudo apt install python3-pip

2. Create `~/.bash_aliases` and enter:

        alias python=python3
        alias pip=pip3

3. Re-login to make this effective.

4. Confirm by executing `python --version` and `pip --version` that you have Python 3.x and pip for Python 3.x.

5. Install the requirements with `pip`. Tensorflow is an unmentioned requirement of Keras (seems to be a bug?). `h5py` is a requirement of Keras when importing a pre-trained model.

        pip install -r classifier/requirements.txt
        pip install tensorflow==1.5
        pip install h5py
        
6. Try to run the classifier with one image (see below). If this results in an error, it is because the newest version of Tensorflow requires CPU features that your (older) CPU does not support – see [issue #17411](https://github.com/tensorflow/tensorflow/issues/17411). In that case, try downgrading to Tensorflow 1.6, and if that still does to Tensorflow 1.5. Downgrading gradually will result in the highest version of Tensorflow that works with your CPU, resulting in the highest speed you can achieve with it because new versions tend to use more CPU capabilities.


### 1.2. Install the coffee beans dataset

1. Download the full dataset of singled-out coffee bean images. (Currently [here](https://drive.google.com/drive/folders/1CvEiDe5V_2zKDQWTssJhesFqkI1S99vJ) on Google Drive, but will move soon.)

2. Fill the images into the directory directory structure that you find inside the `classifier/` directory:

  * data/
    * train/
      * good/
      * bad/
    * validation/
      * good/
      * bad/


## 2. Using the Classifier

1. Edit `classify.py` to add the path to the image file you want to classify.

2. Run the classifier:

        python classify.py --image data/validation/good/Set04-good.55.enhanced.25.png


This will use the model definition in `model.py` and the weights as saved in `bean_classifier.h5` to classify the
input image.


## 3. Trainig the Classifier

To train the classifier, run any of the `classifier/train*.py` scripts. Each script will create a model, train it with the data in the `data/` directory, and save the resulting weights to a `.h5` file. You can then save that file to a different name for later to prevent it from being overwritten.

Training a classifier is not easy (it's a "fuzzy" task – results will often be quite bad without a clear reason). So we collect here our experience of what helped to improve results.

Training runs and results:

* `train_inceptionv3.weights.2018-03-29.h5`: **78%** final accuracy. Ca. 1650 training images, 550 validation images. 10 epochs for the upper layers, 20 epochs for the lower layers.

* `train_inceptionv3.weights.2018-04-01.h5`: **83%** final accuracy. Parameters: ca. 2000 training images, 845 validation images. 150x150 px image size. 20 epochs for the upper layers, 30 epochs for the lower layers. Change from last run: ca. 450 images added to the training set and 300 images added to the validation set, all taken of bad beans, with a smartphone camera in good outdoor lighting and using automatic image splitting.

* `train_inceptionv3.weights.2018-04-02.h5`: **78%** final accuracy. Parameters: 2507 training images, 845 validation images. 150x150 px image size. 20 epochs for the upper layers, 30 epochs for the lower layers. Change from last run: ca. 550 images added to the training set, all taken of bad beans, with a smartphone camera in good outdoor lighting and using automatic image splitting.
