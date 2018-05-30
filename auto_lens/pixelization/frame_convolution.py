import numpy as np

"""
This module is for the application of convolution to sparse_grid vectors.

Take a simple mask:

[[0, 1, 0],
 [1, 1, 1],
 [0, 1, 0]]

A set of values in a corresponding image_grid might be represented in a 1D array:

[2, 8, 2, 5, 7, 5, 3, 1, 4]

This module allows us to find the relationships between image_to_pixel in a mask for a kernel of a given size so that
convolutions can be efficiently applied to reduced arrays such as the one above.

A FrameMaker can be created for a given mask:

frame_maker = FrameMaker(mask)

This can then produce a convolver for any given kernel shape:

convolver = frame_maker.convolver_for_kernel_shape((3, 3))

A convolver can then be made for any given kernel:

kernel_convolver = convolver.convolver_for_kernel(kernel)

Which is applied to a reduced vector:

convolved_vector = convolver.convolve_vector(vector)

The returned convolved vector is also in the dictionary format.

The convolver can also be applied for some sub_grid-shape of the kernel:

convolved_vector = convolver.convolve_vector(vector, sub_shape=(3, 3))

Or applied to a whole mapping matrix:

convolved_mapping_matrix = convolver.convolve_mapping_matrix(mapping_matrix)

Where the mapping matrix is an array of dictionaries with each index of the array corresponding to a source pixel.

"""


class KernelException(Exception):
    pass


class FrameMaker(object):
    def __init__(self, mask, blurring_region_mask):
        """
        Class to create number array and frames used in 1D convolution
        Parameters
        ----------
        blurring_region_mask
        mask: ndarray
                A mask where 0 eliminates data
        """
        self.mask = mask
        self.blurring_region_mask = blurring_region_mask
        self.number_array = -1 * np.ones(self.mask.shape, dtype=np.int64)
        self.mask_number_array = -1 * np.ones(self.mask.shape, dtype=np.int64)

        number_array_count = 0
        mask_array_count = 0
        for x in range(self.mask.shape[0]):
            for y in range(self.mask.shape[1]):
                if self.mask[x, y] == 1:
                    self.number_array[x, y] = number_array_count
                    number_array_count += 1
                elif self.blurring_region_mask is None or self.blurring_region_mask[x, y] == 1:
                    self.mask_number_array[x, y] = mask_array_count
                    mask_array_count += 1

    def make_frame_array(self, kernel_shape):
        """
        Parameters
        ----------
            An array in which non-masked elements have been numbered 0, 1, 2,...N
        kernel_shape: (int, int)
            The shape of the kernel for which frames will be used
        Returns
        -------
        frame_array: [ndarray]
            A list of frames where the position of a frame corresponds to the number at the centre of that frame
        """
        if kernel_shape[0] % 2 == 0 or kernel_shape[1] % 2 == 0:
            raise KernelException("Kernel must be odd")
        frame_array = []
        for x in range(self.number_array.shape[0]):
            for y in range(self.number_array.shape[1]):
                if self.number_array[x][y] > -1:
                    frame_array.append(self.frame_at_coords((x, y), kernel_shape))

        return frame_array

    def make_mask_frame_array(self, kernel_shape):
        if kernel_shape[0] % 2 == 0 or kernel_shape[1] % 2 == 0:
            raise KernelException("Kernel must be odd")
        frame_array = []
        for x in range(self.number_array.shape[0]):
            for y in range(self.number_array.shape[1]):
                if self.mask_number_array[x][y] > -1:
                    frame_array.append(self.frame_at_coords((x, y), kernel_shape))
        return frame_array

    def frame_at_coords(self, coords, kernel_shape):
        """
        Parameters
        ----------
        coords: (int, int)
            The image_grid of number_array on which the frame should be centred
        kernel_shape: (int, int)
            The shape of the kernel for which this frame will be used
        Returns
        -------
        frame: ndarray
            A subset of number_array of shape kernel_shape where elements with image_grid outside of frame_array have
            value -1
        """
        half_x = int(kernel_shape[0] / 2)
        half_y = int(kernel_shape[1] / 2)

        frame = np.full((kernel_shape[0] * kernel_shape[1],), -1)

        for i in range(kernel_shape[0]):
            for j in range(kernel_shape[1]):
                x = coords[0] - half_x + i
                y = coords[1] - half_y + j
                if 0 <= x < self.number_array.shape[0] and 0 <= y < self.number_array.shape[1]:
                    value = self.number_array[x, y]
                    if value >= 0:
                        frame[j + kernel_shape[1] * i] = value

        return frame

    def convolver_for_kernel_shape(self, kernel_shape):
        """
        Create a convolver that can be used to apply a kernel of any shape to a 1D vector of non-masked values
        Parameters
        ----------
        kernel_shape: (int, int)
            The shape of the kernel
        Returns
        -------
            convolver: Convolver
        """
        return Convolver(self.make_frame_array(kernel_shape))


class Convolver(object):
    def __init__(self, frame_array):
        """
        Class to convolve a kernel with a 1D vector of non-masked values
        Parameters
        ----------
        frame_array: [ndarray]
            An array of frames created by the frame maker. A frame maps positions in the kernel to values in the 1D
            vector.
        """
        self.frame_array = frame_array

    def convolver_for_kernel(self, kernel):
        return KernelConvolver(self.frame_array, kernel)


class KernelConvolver(object):
    def __init__(self, frame_array, kernel):
        self.shape = kernel.shape
        self.length = self.shape[0] * self.shape[1]
        self.kernel = kernel.flatten()
        self.frame_array = frame_array

    def convolve_mapping_matrix(self, mapping_matrix):
        """
        Simple version of function that applies this convolver to a whole mapping matrix.

        Parameters
        ----------
        mapping_matrix: [{int: float}]
            A matrix representing the mapping of source image_to_pixel to image_grid image_to_pixel

        Returns
        -------
        convolved_mapping_matrix: [{int: float}]
            A matrix representing the mapping of source image_to_pixel to image_grid image_to_pixel accounting for convolution
        """
        return map(self.convolve_vector, mapping_matrix)

    def convolve_vector(self, pixel_dict, sub_shape=None):
        """
        Convolves a kernel with a 1D vector of non-masked values
        Parameters
        ----------
        sub_shape: (int, int)
            Defines a sub_grid-region of the kernel for which the result should be calculated
        pixel_dict: [int: float]
            A dictionary that maps image_grid pixel indices to values
        Returns
        -------
        convolved_vector: [float]
            A vector convolved with the kernel
        """

        # noinspection PyUnresolvedReferences
        result = {}
        for key in pixel_dict.keys():
            new_dict = self.convolution_for_pixel_index_vector(key, pixel_dict, sub_shape)
            for new_key in new_dict.keys():
                if new_key in result:
                    result[new_key] += new_dict[new_key]
                else:
                    result[new_key] = new_dict[new_key]

        return result

    def convolution_for_pixel_index_vector(self, pixel_index, pixel_dict, sub_shape=None):
        """
        Creates a vector of values describing the convolution of the kernel with a value in the vector
        Parameters
        ----------
        sub_shape: (int, int)
            Defines a sub_grid-region of the kernel for which the result should be calculated
        pixel_index: int
            The index in the vector to be convolved
        pixel_dict: [int: float]
            A dictionary that maps image_grid pixel indices to values
        Returns
        -------
        convolution_dict: [int: float]
            A dictionary with values populated according to the convolution of the kernel
            with one particular value
        """

        # noinspection PyUnresolvedReferences
        new_dict = {}

        value = pixel_dict[pixel_index]

        frame = self.frame_array[pixel_index]

        limits = None
        if sub_shape is not None:
            limits = calculate_limits(self.shape, sub_shape)

        for kernel_index in range(self.length):
            if sub_shape is not None and not is_in_sub_shape(kernel_index, limits, self.shape):
                continue
            vector_index = frame[kernel_index]
            if vector_index == -1:
                continue
            result = value * self.kernel[kernel_index]
            if result > 0:
                new_dict[vector_index] = result

        return new_dict


def calculate_limits(shape, sub_shape):
    """
    Finds limits from a shape and subshape for calculation of subsize kernel convolutions
    Parameters
    ----------
    shape: (int, int)
        The shape of the kernel
    sub_shape: (int, int)
        The shape of the subkernel to be considered

    Returns
    -------

    """
    lower_x = (shape[0] - sub_shape[0]) / 2
    lower_y = (shape[1] - sub_shape[1]) / 2
    upper_x = shape[0] - lower_x
    upper_y = shape[1] - lower_y
    return lower_x, lower_y, upper_x, upper_y


def is_in_sub_shape(kernel_index_1d, limits, shape):
    # """
    # Determines if a particular index is within given limits inside of a given shape
    # Parameters
    # ----------
    # kernel_index_1d: int
    #     The index in a flattened kernel
    # limits: Tuple[int, int, int, int]
    #     x_min, y_min, x_max, y_max limits
    # shape: (int, int)
    #     The shape of the kernel
    #
    # Returns
    # -------
    #
    # """
    return limits[1] <= kernel_index_1d / \
           shape[0] < limits[3] and limits[0] <= kernel_index_1d % shape[0] < shape[0] - limits[1]
