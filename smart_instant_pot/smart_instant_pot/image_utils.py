# Smart Instant Pot Image Processing Utility Functions
# These are handy utility functions to perform common image processing tasks
# that OpenCV doesn't implement or implements in very cumbersome ways.
# Author: Tony DiCola
import cv2


def constrain_size(img, max_width, max_height, interpolation=cv2.INTER_LINEAR):
    """Resize the specified image so it is at most max_width pixels wide and
    max_height pixels tall.  Will honor the aspect ratio of the input image
    and resize accordingly so the largest side is at the max.  This will
    _never_ upscale the image--if the provided image is not as large as
    the maximums then it is returned as-is.  A 2-tupe with the new resized image
    (or the original if no resizing was performed) and a scale factor value
    (number from 0 to 1.0 with the percent the image was downscaled)
    will be returned.

    You can optionally override the type of resizing interpolation with the
    interpolation keyword.  Specify a valid cv2.resize interpolation
    parameter value.  The default is cv2.INTER_LINEAR for bilinear interpolation.
    """
    # Handle if the image is smaller than the specified maximums.
    # In this case do no resizing.
    height, width = img.shape[:2]
    if width <= max_width and height <= max_height:
        return (img, 1.0)  # No scaling, 1.0 unity value.
    # Find the largest side and resize accordingly-based on the aspect
    # ratio.
    aspect_ratio = width / height
    if width > height:
        # Wide image, compute new height honoring the aspect ratio.
        scaled_height = int(max_width / aspect_ratio)
        scaled_size = (max_width, scaled_height)
        scaling = scaled_height / height
    else:
        # Tall or square image.
        scaled_width = int(max_height * aspect_ratio)
        scaled_size = (scaled_width, max_height)
        scaling = scaled_width / width
    return (cv2.resize(img, scaled_size, interpolation=interpolation), scaling)

def to_grayscale(img):
    """Convert the specified image to grayscale.  Handles both BGR (3 channel)
    and grayscale (1 channel) images automatically.
    """
    # Handle if already grayscale, just return it unmodified.
    if len(img.shape) < 3:
        return img
    # Otherwise assume BGR and perform conversion to grayscale.
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
