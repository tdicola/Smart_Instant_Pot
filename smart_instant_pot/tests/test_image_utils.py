# Smart Instant Pot Image Utilities Tests
# Author: Tony DiCola
import unittest

import numpy as np

import smart_instant_pot.image_utils as image_utils


class TestConstrainSize(unittest.TestCase):

    def test_shrink_square(self):
        # Create a 200x200 square test image and verify it will shrink to the
        # constrained 100x100 size as a square.
        test_img = np.zeros((200, 200, 3), np.uint8)
        result, scaling = image_utils.constrain_size(test_img, 100, 100)
        self.assertTupleEqual(result.shape, (100, 100, 3))
        self.assertEqual(scaling, 0.5)

    def test_shrink_wide(self):
        # Create a 200x100 test image and verify it will shrink to the
        # constrained 100x100 max size appropriately.
        test_img = np.zeros((100, 200, 3), np.uint8)
        result, scaling = image_utils.constrain_size(test_img, 100, 100)
        self.assertTupleEqual(result.shape, (50, 100, 3))
        self.assertEqual(scaling, 0.5)

    def test_shrink_tall(self):
        # Create a 100x200 test image and verify it will shrink to the
        # constrained 100x100 max size appropriately.
        test_img = np.zeros((200, 100, 3), np.uint8)
        result, scaling = image_utils.constrain_size(test_img, 100, 100)
        self.assertTupleEqual(result.shape, (100, 50, 3))
        self.assertEqual(scaling, 0.5)

    def test_no_change_of_small_input(self):
        # Create a 50x50 test image and verify it will be returned unmodified
        # if constrained to a larger size.
        test_img = np.zeros((50, 50, 3), np.uint8)
        result, scaling = image_utils.constrain_size(test_img, 100, 100)
        self.assertTupleEqual(result.shape, (50, 50, 3))
        self.assertIs(result, test_img)
        self.assertEqual(scaling, 1.0)

    def test_scaling(self):
        # Create a 100x100 test image and verify the scale factor is 0.25 if
        # scaled down to 25x25 max size.
        test_img = np.zeros((100, 100, 3), np.uint8)
        result, scaling = image_utils.constrain_size(test_img, 25, 25)
        self.assertEqual(scaling, 0.25)


class TestToGrayscale(unittest.TestCase):

    def test_bgr_input(self):
        # Create a BGR color image and verify it's converted to one channel/gray.
        test_img = np.zeros((50, 50, 3), np.uint8)
        result = image_utils.to_grayscale(test_img)
        self.assertTupleEqual(result.shape, (50, 50))

    def test_grayscale_input(self):
        # Create a grayscale image and verify it's converted to one channel/gray.
        test_img = np.zeros((50, 50), np.uint8)
        result = image_utils.to_grayscale(test_img)
        self.assertTupleEqual(result.shape, (50, 50))
