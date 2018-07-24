import sys

sys.path.append("../../")
import numpy as np
from src.imaging import mask
from src.pixelization import frame_convolution
import time
import os
import numba

path = os.path.dirname(os.path.realpath(__file__))

def load(name):
    return np.load("{}/{}.npy".format(path, name))

grid = load("deflection_data/grid")

psf_shape = (11, 11)

ma = mask.Mask.for_simulate(shape_arc_seconds=(4.0, 4.0), pixel_scale=0.1, psf_size=psf_shape)

data = ma.masked_1d_array_from_2d_array(np.ones(ma.shape))

mapping = np.ones((len(data), 60))

frame = frame_convolution.FrameMaker(mask=ma)
convolver = frame.convolver_for_kernel_shape(kernel_shape=psf_shape)
# This PSF leads to no blurring_coords, so equivalent to being off.
kernel_convolver = convolver.convolver_for_kernel(kernel=np.ones(psf_shape))

kernel_convolver.convolve_mapping_matrix_jit(mapping)
repeats = 1

def tick_toc(func):
    def wrapper():
        start = time.time()
        for _ in range(repeats):
            func()

        diff = time.time() - start
        print("{}: {}".format(func.__name__, diff))

    return wrapper

@tick_toc
def current_solution():

    kernel_convolver.convolve_mapping_matrix(mapping)


@tick_toc
def jitted_solution():
    kernel_convolver.convolve_mapping_matrix_jit(mapping)

if __name__ == "__main__":
    current_solution()
    jitted_solution()