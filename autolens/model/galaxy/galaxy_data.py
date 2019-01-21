import numpy as np

from autolens import exc
from autolens.data.array import grids, mask as msk, scaled_array


class GalaxyData(object):

    def __init__(self, array, noise_map, mask, sub_grid_size=2, use_intensities=False, use_surface_density=False,
                 use_potential=False, use_deflections_y=False, use_deflections_x=False):
        """ A galaxy-hyper is a collection of hyper components which are used to fit a galaxy to another galaxy. \
        This is where a component of a galaxy's light profiles (e.g. intensities) or mass profiles (e.g. surface \
        density, potential or deflection angles) are fitted to one another.

        This is primarily performed for automatic prior linking, as a means to efficiently link the priors of a galaxy \
        using one inferred parametrization of light or mass profiles to a new galaxy with a different parametrization \
        of light or mass profiles.

        This omits a number of the hyper components typically used when fitting an image (e.g. the observed image, PSF, \
        exposure time map), but still has a number of the other components (e.g. an effective noise_map-map, grid_stacks).

        Parameters
        ----------
        array : scaled_array.ScaledSquarePixelArray
            An array of the quantity of the galaxy that is being fitted (e.g. its intensities, surface density, etc.).
        noise_map : scaled_array.ScaledSquarePixelArray
            The noise_map-map used for computing the likelihood of each fit. This can be chosen arbritarily.
        mask: msk.Mask
            The 2D masks that is applied to image hyper.
        sub_grid_size : int
            The size of the sub-grid used for computing the SubGrid (see ccd.masks.SubGrid).

        Attributes
        ----------
        noise_map_1d : ndarray
            The masked 1D array of the noise_map-map
        grid_stacks : ccd.masks.GridStack
            Grids of (y,x) Cartesian coordinates which map over the masked 1D hyper array's pixels (includes an \
            regular-grid, sub-grid, etc.)
        padded_grid_stack : ccd.masks.GridStack
            Grids of padded (y,x) Cartesian coordinates which map over the every hyper array's pixel in 1D and a \
            padded regioon to include edge's for accurate PSF convolution (includes an regular-grid, sub-grid, etc.)
        """
        self.array = array
        self.pixel_scale = array.pixel_scale
        self.mask = mask
        self.noise_map = noise_map

        self.array_1d = mask.map_2d_array_to_masked_1d_array(array_2d=array)
        self.noise_map_1d = mask.map_2d_array_to_masked_1d_array(array_2d=noise_map)
        self.mask_1d = mask.map_2d_array_to_masked_1d_array(array_2d=mask)
        self.sub_grid_size = sub_grid_size

        self.grid_stack = grids.GridStack.grid_stack_from_mask_sub_grid_size_and_psf_shape(mask=mask,
                                                                                           sub_grid_size=sub_grid_size,
                                                                                           psf_shape=(1, 1))

        self.padded_grid_stack = grids.GridStack.padded_grid_stack_from_mask_sub_grid_size_and_psf_shape(
            mask=mask, sub_grid_size=sub_grid_size, psf_shape=(1, 1))

        if all(not element for element in [use_intensities, use_surface_density, use_potential,
                                           use_deflections_y, use_deflections_x]):
            raise exc.GalaxyException('The galaxy hyper has not been supplied with a use_ method.')

        if sum([use_intensities, use_surface_density, use_potential, use_deflections_y, use_deflections_x]) > 1:
            raise exc.GalaxyException('The galaxy hyper has not been supplied with multiple use_ methods, only supply '
                                      'one.')

        self.use_intensities = use_intensities
        self.use_surface_density = use_surface_density
        self.use_potential = use_potential
        self.use_deflections_y = use_deflections_y
        self.use_deflections_x = use_deflections_x

    def __array_finalize__(self, obj):
        super(GalaxyData, self).__array_finalize__(obj)
        if isinstance(obj, GalaxyData):
            self.array = obj.array
            self.pixel_scale = obj.pixel_scale
            self.mask = obj.mask
            self.noise_map = obj.noise_map
            self.array_1d = obj.array_1d
            self.noise_map_1d = obj.noise_map_1d
            self.mask_1d = obj.mask_1d
            self.sub_grid_size = obj.sub_grid_size
            self.grid_stack = obj.grid_stack
            self.padded_grid_stack = obj.padded_grid_stack
            self.use_intensities = obj.use_intensities
            self.use_surface_density = obj.use_surface_density
            self.use_potential = obj.use_potential
            self.use_deflections_y = obj.use_deflections_y
            self.use_deflections_x = obj.use_deflections_x

    def map_to_scaled_array(self, array_1d):
        return self.grid_stack.regular.scaled_array_from_array_1d(array_1d=array_1d)

    def profile_quantity_from_galaxy_and_sub_grid(self, galaxy, sub_grid):

        if self.use_intensities:
            return sub_grid.sub_data_to_regular_data(sub_array=galaxy.intensities_from_grid(grid=sub_grid))
        elif self.use_surface_density:
            return sub_grid.sub_data_to_regular_data(sub_array=galaxy.surface_density_from_grid(grid=sub_grid))
        elif self.use_potential:
            return sub_grid.sub_data_to_regular_data(sub_array=galaxy.potential_from_grid(grid=sub_grid))
        elif self.use_deflections_y:
            deflections = galaxy.deflections_from_grid(grid=sub_grid)
            deflections = np.asarray([sub_grid.sub_data_to_regular_data(deflections[:, 0]),
                                      sub_grid.sub_data_to_regular_data(deflections[:, 1])]).T
            return deflections[:,0]
        elif self.use_deflections_x:
            deflections = galaxy.deflections_from_grid(grid=sub_grid)
            deflections = np.asarray([sub_grid.sub_data_to_regular_data(deflections[:, 0]),
                                      sub_grid.sub_data_to_regular_data(deflections[:, 1])]).T
            return deflections[:,1]