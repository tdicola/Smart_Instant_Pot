# Smart Instant Pot Detector Tests
# Author: Tony DiCola
import unittest

import cv2

import smart_instant_pot.detector as detector


TEST_IMG_PATH = '/home/jovyan/work/test_images'


class TestDetector(unittest.TestCase):

    def setUp(self):
        # Load the front panel image to simplify tests.
        self.panel_img = cv2.imread(f'{TEST_IMG_PATH}/control_panel.jpg')

    def test_detect_panel_in_image(self):
        # Test the front panel is detected when provided with an image that has
        # it reasonably visible.
        det = detector.Detector(self.panel_img)
        panel = det.detect_panel(cv2.imread(f'{TEST_IMG_PATH}/test.jpg'))
        self.assertIsNotNone(panel)
