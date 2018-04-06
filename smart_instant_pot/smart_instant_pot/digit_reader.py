# Smart Instant Pot Digit Reader
# Given a photo cropped to the control panel of an instant pot this will
# attempt to decode the digits displayed by the 7-segment LED display.
# Author: Tony DiCola
import logging

import cv2
import numpy as np

from smart_instant_pot.services.settings import Settings
import smart_instant_pot.image_utils as image_utils


logger = logging.getLogger(__name__)

# Lookup table to convert individual LED segment state into character values.
# The order for each of the key tuples is:
#  - 0: Upper left segment
#  - 1: Tpp segment
#  - 2: Upper right segment
#  - 3: Middle segment
#  - 4: Lower left segment
#  - 5: Bottom segment
#  - 6: Lower right segment
_digit_segments = {
    (True, True, True, False, True, True, True):     '0',
    (False, False, True, False, False, False, True): '1',
    (False, True, True, True, True, True, False):    '2',
    (False, True, True, True, False, True, True):    '3',
    (True, False, True, True, False, False, True):   '4',
    (True, True, False, True, False, True, True):    '5',
    (True, True, False, True, True, True, True):     '6',
    (False, True, True, False, False, False, True):  '7',
    (True, True, True, True, True, True, True):      '8',
    (True, True, True, True, False, True, True):     '9',
    (True, False, False, False, True, True, False):  'L',
    (True, True, False, True, True, False, False):   'F',
    (False, False, False, True, True, False, True):  'n'
}


class DigitReaderParameters(Settings):
    # Parameters that can be adjusted to change how the detection works.

    # These are the HSV color hues ranges for red LED digits (note OpenCV hues
    # range from 0 to 180, not 0-360).  A value of 160-180 is red.
    led_threshold_h_min = Settings.IntValue(default=160)
    led_threshold_h_max = Settings.IntValue(default=180)

    # These are both the HSV saturation and value ranges for red LED digits.
    # This range covers a range of bright / high intensity values.
    led_threshold_sv_min = Settings.IntValue(default=100)
    led_threshold_sv_max = Settings.IntValue(default=255)

    # Size in pixels of the open operation.  This is done to remove small bright
    # red noise from the image and make panel LED digit area detection more
    # robust.  In particular the on/off indicator lights need to be ignored by
    # opening the image (i.e. erode then dilate).
    open_kernel_size = Settings.IntValue(default=5)

    # Size in pixels of the dilation operation.  This is done to expand the
    # thresholded digits and make them chunkier and easier to detect (and fill
    # in any disconnected segments that break continuous digit contours).
    dilate_kernel_size = Settings.IntValue(default=5)

    # How much of the image to crop horizontally when retrying a digit after
    # a colon was detected.  This removes the right 20% to try excluding the
    # colon.
    colon_retry_crop_percent = Settings.FloatValue(default=0.8)

    # Percent of a segment's area that must be lit for the segment to be
    # considered on.
    segment_filled_area_percent = Settings.FloatValue(default=0.5)

    # Aspect ratio to be near for a digit contour to be a '1' special case.
    # This is a tall, skinny rectangle.
    one_digit_aspect_ratio = Settings.FloatValue(default=0.33)

    # Percent of the digit contour area that must be lit for a '1' digit
    # special case.  This looks for a digit contour that's significantly lit.
    one_digit_filled_area = Settings.FloatValue(default=0.66)


def _filled_area(image, rect=None):
    # Count the number of filled pixels in the specified rect region of the
    # image.  Return the percent of pixels that are filled as a float value
    # from 0 to 1.
    if rect is None:
        # No bounding box, compute filled pixels of entire image.
        height, width = image.shape[:2]
        rect = ((0, 0), (width-1, height-1))
    p0, p1 = rect
    x0, y0 = p0
    x1, y1 = p1
    total = (x1-x0)*(y1-y0)
    if total == 0:
        return 0
    filled = cv2.countNonZero(image[y0:y1,x0:x1])
    return filled / total


class DigitReader:
    """Digit reader will attempt to detect the digits being displayed in an
    Instant Pot control panel image.  You can pass an optional parameter store
    to read/write the reader's configuration parameters to a special backing
    store (like a config file or Redis DB).  In addition the debug_plot keyword
    is a function that will be called with OpenCV images to plot intermediate
    image processing results useful for debugging (keep this unspecified to
    disable the debug plotting).  In addition this class logs useful intermediate
    processing state with standard logging DEBUG level messages.
    """

    def __init__(self, parameters_store=None, debug_plot=None):
        self._params = DigitReaderParameters(store=parameters_store)
        self._debug_plot_func = debug_plot

    def _debug_plot(self, image, title=None):
        # Allow caller to pass in a plotting function that draws intermediate
        # images to help debug the detection logic (useful in a Jupyter notebook).
        if self._debug_plot_func is not None:
            self._debug_plot_func(image, title)

    def _detect_digit(self, digit_img):
        # Given a single channel 7-segment LED digit image attempt to detect
        # which segments are turned on.  Will return None if no digit detected
        # or the character value for the detected digit.
        # This works by looking at 7 different areas of the image centered around
        # the center of each LED segment position.  If enough pixels are turned
        # on in that area then consider the segment lit.
        height, width = digit_img.shape
        aspect = width / height
        area = height * width
        logger.debug('Digit aspect ratio: {0:0.2f}'.format(aspect))
        # Handle a 1 as a special case with a tall aspect ratio and large majority
        # turned on pixels.
        filled_area = _filled_area(digit_img)
        logger.debug('Digit filled area: {0:0.2f}%)'.format(filled_area * 100.0))
        if abs(aspect - self._params.one_digit_aspect_ratio) <= 0.1 and \
           filled_area >= self._params.one_digit_filled_area:
            return '1'
        # General segment detection logic.
        # Calculate rectangles that bound each of the 7 segment digit areas.
        # This is all calculated relative to the digit size so it scales to any
        # size of shape digit.
        ss = int(width/3)   # ss = segment size
        hss = ss//2         # hss = half segment size
        vq = int(height/4)  # vq = vertical quarter size
        vq1 = vq            # vq1-3 are the locations of each vertical quarter
        vq2 = 2*vq
        vq3 = 3*vq
        x1 = width-1        # x1, y1 are the far edges of the image
        y1 = height-1
        # Check if there might be a colon lit on the far right side.  Look for
        # the right third column and break it into 5ths vertically.  Compute the
        # area of lit pixels for each fifth and fail if we see from top to bottom:
        # not lit, lit, not lit, lit, not lit (i.e. alternating not lit & lit).
        colon_lit = [False]*5
        for i in range(5):
            # Calculate the y range for each fifth of the image moving from top
            # to the bottom.
            y0 = i*int(height/5)
            y1 = (i+1)*int(height/5)
            # Generate bounds for the far right side of the image at each of
            # these fifth-size positions.  If enough of the pixels are lit
            # consider it turned on.
            d = ((x1-ss, y0), (x1, y1))
            if _filled_area(digit_img, d) > self._params.segment_filled_area_percent:
                colon_lit[i] = True
        # Now test if the vertical fifths are lit in an order that would indicate
        # the colon (i.e. alternating off and on).
        if not colon_lit[0] and colon_lit[1] and not colon_lit[2] and \
            colon_lit[3] and not colon_lit[4]:
            logger.debug('Digit appears to have a colon!')
            # Just fail when we detect the colon.  The digit detection will be
            # retried by the parent after cropping off the right portion.
            return None
        # Now calculate the bounds of each of the 7 areas that will test for
        # the segments.  This goes in order from:
        # - s0 = upper left segment
        # - s1 = top segment
        # - s2 = upper right segment
        # - s3 = middle segment
        # - s4 = lower left segment
        # - s5 = bottom segment
        # - s6 = lower right segment
        s0 = ((    0,  vq1-hss),  # upper left, look on left side around top quarter
              (   ss,  vq1+hss))
        s1 = ((   ss,  0),        # top, look on top middle
              (x1-ss,  ss))
        s2 = ((x1-ss,  vq1-hss),  # upper right, look on right side around top quarter
              (   x1,  vq1+hss))
        s3 = ((   ss,  vq2-hss),  # middle, look exactly in the middle area
              (x1-ss,  vq2+hss))
        s4 = ((    0,  vq3-hss),  # lower left, look on left side around bottom quarter
              (   ss,  vq3+hss))
        s5 = ((   ss,  y1-ss),    # bottom, look at bottom middle
              (x1-ss,  y1))
        s6 = ((x1-ss,  vq3-hss),  # lower right, look on right side around bottom quarter
              (   x1,  vq3+hss))
        # Calculate the percent of each segment area that's turned on and if it
        # exceeds a threshold consider that entire segment lit.
        segments = []
        for i, s in enumerate((s0, s1, s2, s3, s4, s5, s6)):
            p1, p2 = s
            x0, y0 = p1
            x1, y1 = p2
            area = (x1-x0)*(y1-y0)
            segment_image = digit_img[y0:y1, x0:x1]
            if area == 0:
                return None  # Bad input, not able to find areas of pixels.
            filled_area = _filled_area(segment_image)
            lit = filled_area >= self._params.segment_filled_area_percent
            segments.append(lit)
            self._debug_plot(segment_image, 'Segment {0} - {1:0.2f}% filled - {2}'.format(i,
                filled_area * 100.0, 'lit' if lit else 'NOT lit'))
        # Finally look up in a table how the lit segments map to digit values.
        return _digit_segments.get(tuple(segments), None)

    def read_digits(self, panel_img):
        """Given an image of an instant pot control panel try to read the digits
        being displayed. Will return a string with the digits that were found,
        or the value None if no digits could be successfully read.
        """
        # At a high level the digit reading just uses image processing to isolate
        # the LED segments and count which ones are on vs. off to decode the
        # digits being displayed.  The steps are as follows:
        #  1. Isolate the LED display from the panel image.  Use a threshold
        #     on the bright red hues of the LED segments to find them and a
        #     bounding contour that contains them all.
        #  2. Crop to just the LED display and apply a binarization threshold
        #     and dilation to enlarge the digits and make them easy to detect.
        #  3. Find up to 4 of the largest LED digit contours and process each
        #     one individually to decode which segments are turned on vs. off.
        #     Make sure these contours are sorted in left to right order too.
        #  4. For each digit crop to its contour bounding box and examine 7
        #     areas that are the center of each LED segment.  If these areas
        #     are mostly lit pixels then assume the segment is turned on and
        #     look up in a table which lit segments map to digit values.
        #  5. There are a few special cases to the above digit detection logic:
        #       - Look for a 1 digit as a tall, skinny mostly turned on contour.
        #         These digits are otherwise hard to detect because they only
        #         occupy a fraction of the horizontal space compared to other
        #         digits and the general digit detection logic would get confused.
        #       - If one of the 4 largest digit contours is significantly smaller
        #         in height than the other contours, expand up its contour bounds
        #         to match the tallest.  This handles the character 'n' and
        #         other lower-case values that don't occupy the upper segments.
        #       - Look for a colon on the right hand side of a digit by
        #         checking for an alternating off, on, off, on, off vertical
        #         slice.  If this is found then crop off the right side of the
        #         digit boundary and try the detection again.  In practice it's
        #         hard to filter out the colon as it's quite close to the second
        #         digit and typically bleeds into it during the dilation and
        #         contour finding.

        # Convert to HSV color space and apply threshold to find bright red
        # digits (colors within a range of bright red hues).
        panel_hsv = cv2.cvtColor(panel_img, cv2.COLOR_BGR2HSV)
        lower = np.array((self._params.led_threshold_h_min,
                          self._params.led_threshold_sv_min,
                          self._params.led_threshold_sv_min))
        upper = np.array((self._params.led_threshold_h_max,
                          self._params.led_threshold_sv_max,
                          self._params.led_threshold_sv_max))
        panel_led = cv2.inRange(panel_hsv, lower, upper)
        self._debug_plot(panel_led, 'LED HSV color threshold')
        # Apply open morphologic operation to get rid of small noise like tiny
        # lit indicator LEDs elsewhere on the panel.
        open_kernel = np.ones((self._params.open_kernel_size,
                               self._params.open_kernel_size), np.uint8)
        panel_led = cv2.morphologyEx(panel_led, cv2.MORPH_OPEN, open_kernel)
        self._debug_plot(panel_led, 'Opened threshold')
        # Find contour to bound entire LED panel region (bounding box around
        # all the LED digit contours).
        _, contours, _ = cv2.findContours(panel_led.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        logger.debug('LED contours: {0}'.format(len(contours)))
        if len(contours) < 1:
            # Failed to find any red digits.
            return None
        # Find the rectangle to bound all the LED display contours and extract
        # the entire LED area using it.
        x0, y0, w, h = cv2.boundingRect(contours[0])
        x1 = x0+w
        y1 = y0+h
        for i in range(1, len(contours)):
            x, y, w, h = cv2.boundingRect(contours[i])
            x0 = min(x, x0)
            y0 = min(y, y0)
            x1 = max(x+w, x1)
            y1 = max(y+h, y1)
        panel_led = panel_img[y0:y1, x0:x1]
        self._debug_plot(panel_led, 'Cropped LED panel')
        # Apply Otsu binarization to threshold to a single channel image.
        # This works well because the cropped LED panel has a bimodal histogram,
        # i.e. one bump for the LED digits and glow and another bump for the
        # dark background of the unlit display.
        _, panel_digits = cv2.threshold(cv2.cvtColor(panel_led, cv2.COLOR_BGR2GRAY),
            0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Dilate to fill in any gaps between segments.
        dilate_kernel = np.ones((self._params.dilate_kernel_size,
                                 self._params.dilate_kernel_size), np.uint8)
        panel_digits = cv2.dilate(panel_digits, dilate_kernel)
        self._debug_plot(panel_digits, 'Thresholded and dilated digits')
        # Find contours for each digit.
        _, contours, _ = cv2.findContours(panel_digits.copy(),
            cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        logger.debug('LED digit contours: {0}'.format(len(contours)))
        # If there are more than 4 contours, grab the 4 largest by area and
        # assume they're the digits vs. others that must be small noise.
        digit_contours = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            contour_area = w*h
            # Calculate and keep track of the total area, height, and
            # rectangle corners (bounds) of each digit contour.
            digit_contours.append((contour_area, h, ((x, y), (x+w, y+h))))
        # Sort contours by total area descending and grab the top 4 in size.
        digit_contours.sort(key=lambda x: x[0], reverse=True)
        if len(digit_contours) > 4:
            logger.debug('Pruning {0} digit contours down to top 4.'.format(len(digit_contours)))
            digit_contours = digit_contours[:4]
        # Now sort the remaining contours by ascending x position, i.e. left to
        # right order.
        digit_contours.sort(key=lambda x: x[2][0][0])
        # Special case to increase the height of short contours to match that of
        # the largest one. This catches lower-case characters like 'n' that don't
        # occupy the upper segments.
        # First find the tallest contour size.
        tallest = 0
        for dc in digit_contours:
            area, height, bounds = dc
            tallest = max(tallest, height)
        logger.debug('Tallest digit contour: {0}'.format(tallest))
        # Now check each contour and expand up short ones to match the tallest.
        for i, dc in enumerate(digit_contours):
            area, height, bounds = dc
            # Expand up the size of this contour if it's significantly shorter
            # than the tallest contour.
            if height/tallest <= 0.6:
                logger.debug('Expanding digit {0} up in size to match tallest.'.format(i))
                # Calculate new area, height, and bounds for this contour by
                # keeping its bottom fixed but height expanded up.  Be careful
                # to clamp it to a zero y value (i.e. no negative values).
                height = tallest
                p1, p2 = bounds
                p1 = (p1[0], max(p2[1]-tallest, 0))
                area = (p2[0]-p1[0])*tallest
                digit_contours[i] = (area, height, (p1, p2))
        # Go through each contour and attempt to decode which segments are lit
        # in order to decode the digit being displayed.
        decoded_digits = ''
        for i, dc in enumerate(digit_contours):
            area, height, bounds = dc
            p1, p2 = bounds
            digit_image = panel_digits[p1[1]:p2[1], p1[0]:p2[0]]
            self._debug_plot(digit_image, 'Digit {0}'.format(i))
            digit_value = self._detect_digit(digit_image)
            logger.debug('Digit {0} first detection value: {1}'.format(i, digit_value))
            # If digit wasn't detected try again with the right 20% cropped off.
            # This will ignore the colon that can interfere with the left middle
            # digit detection.
            if digit_value is None:
                cropped_width = int(self._params.colon_retry_crop_percent*(p2[0]-p1[0]))
                cropped_p2 = (p1[0] + cropped_width, p2[1])
                cropped_image = panel_digits[p1[1]:cropped_p2[1], p1[0]:cropped_p2[0]]
                self._debug_plot(cropped_image, 'Cropped digit {0}'.format(i))
                digit_value = self._detect_digit(cropped_image)
                logger.debug('Digit {0} cropped detection value: {1}'.format(i, digit_value))
            # Fail if still couldn't detect the digit after cropping.
            if digit_value is None:
                return None
            # Found the digit!  Add it to the result in order.
            decoded_digits += digit_value
        return decoded_digits
