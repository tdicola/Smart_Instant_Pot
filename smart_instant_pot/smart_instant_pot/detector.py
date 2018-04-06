# Smart Instant Pot Detector
# This code will attempt to find an Instant Pot (6qt. DUO model only!) in an
# input image and parse out information from its simple 7-segment LED display.
# Author: Tony DiCola
import logging

import cv2
import numpy as np

from smart_instant_pot.services.settings import Settings
import smart_instant_pot.image_utils as image_utils


logger = logging.getLogger(__name__)


class DetectorParameters(Settings):
    # Parameters and settings to adjust the instant pot detection logic.

    # Maximum pixel size dimension of input images.
    # This is a balance between performance and memory usage.
    # Larger size images might be more accurate but can take
    # very large amounts of memory for feature detection.
    # If the program crashes a lot then your images are too
    # big (unfortunate side-effect of OpenCV's detection
    # algorithms, they fail in spectacular process destroying
    # ways when out of memory).
    max_dimension = Settings.IntValue(default=1000)

    # Feature matches must be this percent (0-1.0) of each
    # other to be considered a good match.
    match_ratio = Settings.FloatValue(default=0.7)

    # Minimum number of good matches that must be found
    # between an input and the control panel source image
    # to consider the Instant Pot detected in the input.
    min_good_matches = Settings.IntValue(default=10)



# FLANN feature matcher options.  These aren't configurable through parameters
# above because they're complex dicts that rarely change.
FLANN_INDEX_OPTIONS = { 'algorithm': 0,
                        'trees': 5
                      }
FLANN_SEARCH_PARAMS = { 'checks': 50
                      }


class Detector:
    """Create an Instant Pot detector instance.  Must specify the front panel
    image as an OpenCV/numpy image which will be used as the basis for
    template matching and homography.  This image should be a clear head on
    view cropped tightly to just the Instant Pot's front panel, ideally in
    very neutral/bright lighting (i.e. avoid hard shadows or dim conditions).
    Optionally pass a parameter store to read and write the detector's config
    parameters in a specific store (like a config file or Redis DB).
    """

    def __init__(self, panel_img, parameters_store=None):
        self._params = DetectorParameters(store=parameters_store)
        # Convert the target image to grayscale and constrain it to the max
        # pixel dimensions.
        self._panel_img, _ = image_utils.constrain_size(panel_img,
            self._params.max_dimension, self._params.max_dimension)
        self._panel_img = image_utils.to_grayscale(self._panel_img)
        # Create a SIFT algorithm feature detector and FLANN feature matcher
        # with default parameters.  This is influenced from:
        #   http://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_feature2d/py_feature_homography/py_feature_homography.html
        self._sift = cv2.xfeatures2d.SIFT_create()
        self._flann = cv2.FlannBasedMatcher(FLANN_INDEX_OPTIONS, FLANN_SEARCH_PARAMS)
        # Detect control panel features once at the start and store them.
        kp, desc = self._sift.detectAndCompute(self._panel_img, None)
        self._panel_keypoints = kp
        self._panel_descriptors = desc

    def detect_panel(self, img):
        """Attempt to detect an Instant Pot somewhere in the provided image. If
        one is found then a homography of the control panel (i.e. projection of
        the pot control panel from the source image into a flat 'head-on' view)
        is returned.  If no pot is detected then None is returned.
        """
        # Scale the input to the max pixel dimensions and convert to grayscale
        # for efficient feature detection.
        color_img, scaling = image_utils.constrain_size(img,
            self._params.max_dimension, self._params.max_dimension)
        feature_img = image_utils.to_grayscale(color_img)
        # Perform feature detection on the input.
        kp, desc = self._sift.detectAndCompute(feature_img, None)
        # Perform feature matching between input and control panel (whose features
        # were previously detected at initialization).
        matches = self._flann.knnMatch(desc, self._panel_descriptors, k=2)
        logger.debug('Total feature matches: {0}'.format(len(matches)))
        # Find 'good' features that have two matches within a certain ratio
        # distance of each other.
        good = [m for m, n in matches \
                if m.distance < self._params.match_ratio*n.distance]
        # Stop if not enough good matches were found.
        logger.debug('Good feature matches: {0}'.format(len(good)))
        if len(good) < self._params.min_good_matches:
            return None
        # Found enough good matches, compute the homography and warp the input
        # image to extract the control panel from it.
        img_pts = np.zeros((len(good), 2), np.float32)
        panel_pts = np.zeros((len(good), 2), np.float32)
        for i, match in enumerate(good):
            img_pts[i, :] = kp[match.queryIdx].pt
            panel_pts[i, :] = self._panel_keypoints[match.trainIdx].pt
        homography, mask = cv2.findHomography(img_pts, panel_pts, cv2.RANSAC)
        height, width = self._panel_img.shape[:2]
        return cv2.warpPerspective(color_img, homography, (width, height))
