# Using the Coffee Classifier


## 1. Installation

The following instructions apply to Ubuntu Linux 17.10.


### 1.1. Install required software

We install requirements with `pip`, the Python package management system. (So unfortunately there will be redundancy if
you already have OpenCV etc. installed with Ubuntu packages on your system.)

The file [`requirements.txt`](https://github.com/edgeryders/coffee-cobra/blob/master/classifier/requirements.txt)
informs `pip` about the software versions required for this installation. Updated versions _should_ work, too, but may
not.

The installation also contains `jupyter`, a Python IDE to work with annotated source code ("notebooks"). This is used in
`Coffee Classifier Trainer.ipynb`. However, this is optional, as you can always extract the actual Python source code
itself from that file and run it.


1. Install Python 3.x and pip for Python 3.x:

        sudo apt install python3
        sudo apt install python3-pip

2. Create `~/.bash_aliases` and enter:

        alias python=python3
        alias pip=pip3

3. Re-login to make this effective.

4. Confirm by executing `python --version` and `pip --version` that you have Python 3.x and pip for Python 3.x.

5. Install the requirements with `pip`. Tensorflow is an unmentioned requirement of Keras (seems to be a bug?), and we
install version 1.5 to work around [issue #17411](https://github.com/tensorflow/tensorflow/issues/17411). On new CPUs,
version 1.6 will work as well. `h5py` is a requirement of Keras when importing a pre-trained model.

        pip install -r classifier/requirements.txt
        pip install tensorflow==1.5
        pip install h5py


### 1.2. Install the coffee beans dataset

1. Download the full dataset of singled-out coffee bean images. (Currently
[here](https://drive.google.com/drive/folders/1CvEiDe5V_2zKDQWTssJhesFqkI1S99vJ) on Google Drive, but will move soon.)

2. Fill the images into the directory directory structure that you find inside the `classifier/` directory:

  * data/
    * train/
      * good/
      * bad/
    * validation/
      * good/
      * bad/


## 2. Run the Classifier

1. Edit `classify.py` to add the path to the image file you want to classify.

2. Run the classifier:

        python classify.py --image data/validation/good/Set04-good.55.enhanced.25.png


This will use the model definition in `model.py` and the weights as saved in `bean_classifier.h5` to classify the
input image.


## 3. Re-create the model

Run `Coffee Classifier Trainer.ipynb`. Effects:

* uses the model definition in `model.py`
* re-creates `bean_classifier.h5`
