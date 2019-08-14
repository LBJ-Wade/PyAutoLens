import numpy as np
from astropy import cosmology as cosmo
from skimage import measure

import autofit as af
from autolens import exc, dimensions as dim
from autolens.data.array import scaled_array
from autolens.data.array.grids import (
    reshape_returned_array,
    reshape_returned_array_blurring,
    reshape_returned_grid,
)
from autolens.lens.util import lens_util
from autolens.model import cosmology_util
from autolens.data.array.util import grid_util


class Plane(object):

    def __init__(self, redshift, galaxies=None, cosmology=cosmo.Planck15):
        """A plane of galaxies where all galaxies are at the same redshift.

        Parameters
        -----------
        redshift : float or None
            The redshift of the plane.
        galaxies : [Galaxy]
            The list of lens galaxies in this plane.
        grid_stack : masks.GridStack
            The stack of grid_stacks of (y,x) arc-second coordinates of this plane.
        border : masks.RegularGridBorder
            The borders of the regular-grid, which is used to relocate demagnified traced regular-pixel to the \
            source-plane borders.
        compute_deflections : bool
            If true, the deflection-angles of this plane's coordinates are calculated use its galaxy's mass-profiles.
        cosmology : astropy.cosmology
            The cosmology associated with the plane, used to convert arc-second coordinates to physical values.
        """

        if redshift is None:

            if not galaxies:
                raise exc.RayTracingException(
                    "A redshift and no galaxies were input to a Plane. A redshift for the Plane therefore cannot be"
                    "determined"
                )
            elif not all(
                [galaxies[0].redshift == galaxy.redshift for galaxy in galaxies]
            ):
                raise exc.RayTracingException(
                    "A redshift and two or more galaxies with different redshifts were input to a Plane. A unique "
                    "Redshift for the Plane therefore cannot be determined"
                )
            else:
                redshift = galaxies[0].redshift


        self.redshift = redshift
        self.galaxies = galaxies
        self.cosmology = cosmology

    @property
    def galaxy_redshifts(self):
        return [galaxy.redshift for galaxy in self.galaxies]

    @property
    def arcsec_per_kpc(self):
        return cosmology_util.arcsec_per_kpc_from_redshift_and_cosmology(
            redshift=self.redshift, cosmology=self.cosmology
        )

    @property
    def kpc_per_arcsec(self):
        return 1.0 / self.arcsec_per_kpc

    def angular_diameter_distance_to_earth_in_units(self, unit_length="arcsec"):
        return cosmology_util.angular_diameter_distance_to_earth_from_redshift_and_cosmology(
            redshift=self.redshift, cosmology=self.cosmology, unit_length=unit_length
        )

    def cosmic_average_density_in_units(
        self, unit_length="arcsec", unit_mass="solMass"
    ):
        return cosmology_util.cosmic_average_density_from_redshift_and_cosmology(
            redshift=self.redshift,
            cosmology=self.cosmology,
            unit_length=unit_length,
            unit_mass=unit_mass,
        )

    @property
    def has_light_profile(self):
        return any(list(map(lambda galaxy: galaxy.has_light_profile, self.galaxies)))

    @property
    def has_mass_profile(self):
        return any(list(map(lambda galaxy: galaxy.has_mass_profile, self.galaxies)))

    @property
    def has_pixelization(self):
        return any([galaxy.pixelization for galaxy in self.galaxies])

    @property
    def has_regularization(self):
        return any([galaxy.regularization for galaxy in self.galaxies])

    @property
    def regularization(self):

        galaxies_with_regularization = list(
            filter(lambda galaxy: galaxy.has_regularization, self.galaxies)
        )

        if len(galaxies_with_regularization) == 0:
            return None
        if len(galaxies_with_regularization) == 1:
            return galaxies_with_regularization[0].regularization
        elif len(galaxies_with_regularization) > 1:
            raise exc.PixelizationException(
                "The number of galaxies with regularizations in one plane is above 1"
            )

    @property
    def has_hyper_galaxy(self):
        return any(list(map(lambda galaxy: galaxy.has_hyper_galaxy, self.galaxies)))

    @reshape_returned_array
    def profile_image_from_grid(self, grid, return_in_2d=True, return_binned=True):
        """Compute the profile-image plane image of the list of galaxies of the plane's sub-grid, by summing the
        individual images of each galaxy's light profile.

        The image is calculated on the sub-grid and binned-up to the original regular grid by taking the mean
        value of every set of sub-pixels, provided the *returned_binned_sub_grid* bool is *True*.

        If the plane has no galaxies (or no galaxies have mass profiles) an array of all zeros the shape of the plane's
        sub-grid is returned.

        Parameters
        -----------
        return_in_2d : bool
            If *True*, the returned array is mapped to its unmasked 2D shape, if *False* it is the masked 1D shape.
        return_binned : bool
            If *True*, the returned array which is computed on a sub-grid is binned up to the regular grid dimensions \
            by taking the mean of all sub-gridded values. If *False*, the array is returned on the dimensions of the \
            sub-grid.
        """
        if self.galaxies:
            return sum(
                map(
                    lambda galaxy: galaxy.profile_image_from_grid(
                        grid=grid,
                        return_in_2d=False,
                        return_binned=False,
                    ),
                    self.galaxies,
                )
            )
        else:
            return np.full((grid.shape[0]), 0.0)

    def profile_images_of_galaxies_from_grid(
        self, grid, return_in_2d=True, return_binned=True
    ):
        return list(
            map(
                lambda galaxy: self.profile_image_of_galaxy_from_grid_and_galaxy(
                    grid=grid,
                    galaxy=galaxy,
                    return_in_2d=return_in_2d,
                    return_binned=return_binned,
                ),
                self.galaxies,
            )
        )

    def profile_image_of_galaxy_from_grid_and_galaxy(
        self, grid, galaxy, return_in_2d=True, return_binned=True
    ):
        return galaxy.profile_image_from_grid(
            grid=grid,
            return_in_2d=return_in_2d,
            return_binned=return_binned,
        )

    @reshape_returned_array
    def convergence(self, return_in_2d=True, return_binned=True):
        """Compute the convergence of the list of galaxies of the plane's sub-grid, by summing the individual convergences \
        of each galaxy's mass profile.

        The convergence is calculated on the sub-grid and binned-up to the original regular grid by taking the mean
        value of every set of sub-pixels, provided the *returned_binned_sub_grid* bool is *True*.

        If the plane has no galaxies (or no galaxies have mass profiles) an array of all zeros the shape of the plane's
        sub-grid is returned.

        Parameters
        -----------
        grid : RegularGrid
            The grid (regular or sub) of (y,x) arc-second coordinates at the centre of every unmasked pixel which the \
            potential is calculated on.
        galaxies : [galaxy.Galaxy]
            The galaxies whose mass profiles are used to compute the surface densities.
        return_in_2d : bool
            If *True*, the returned array is mapped to its unmasked 2D shape, if *False* it is the masked 1D shape.
        return_binned : bool
            If *True*, the returned array which is computed on a sub-grid is binned up to the regular grid dimensions \
            by taking the mean of all sub-gridded values. If *False*, the array is returned on the dimensions of the \
            sub-grid.
        """
        if self.galaxies:
            return sum(
                map(
                    lambda g: g.convergence_from_grid(
                        grid=self.grid_stack.sub.unlensed_grid_1d,
                        return_in_2d=False,
                        return_binned=False,
                    ),
                    self.galaxies,
                )
            )
        else:
            return np.full((self.grid_stack.sub.shape[0]), 0.0)

    @reshape_returned_array
    def potential(self, return_in_2d=True, return_binned=True):
        """Compute the potential of the list of galaxies of the plane's sub-grid, by summing the individual potentials \
        of each galaxy's mass profile.

        The potential is calculated on the sub-grid and binned-up to the original regular grid by taking the mean
        value of every set of sub-pixels, provided the *returned_binned_sub_grid* bool is *True*.

        If the plane has no galaxies (or no galaxies have mass profiles) an array of all zeros the shape of the plane's
        sub-grid is returned.

        Parameters
        -----------
        grid : RegularGrid
            The grid (regular or sub) of (y,x) arc-second coordinates at the centre of every unmasked pixel which the \
            potential is calculated on.
        galaxies : [galaxy.Galaxy]
            The galaxies whose mass profiles are used to compute the surface densities.
        return_in_2d : bool
            If *True*, the returned array is mapped to its unmasked 2D shape, if *False* it is the masked 1D shape.
        return_binned : bool
            If *True*, the returned array which is computed on a sub-grid is binned up to the regular grid dimensions \
            by taking the mean of all sub-gridded values. If *False*, the array is returned on the dimensions of the \
            sub-grid.
        """
        if self.galaxies:
            return sum(
                map(
                    lambda g: g.potential_from_grid(
                        grid=self.grid_stack.sub.unlensed_grid_1d,
                        return_in_2d=False,
                        return_binned=False,
                    ),
                    self.galaxies,
                )
            )
        else:
            return np.full((self.grid_stack.sub.shape[0]), 0.0)

    @reshape_returned_grid
    def deflections_from_grid(self, grid, return_in_2d=True, return_binned=True):
        if self.galaxies:
            return sum(
                map(
                    lambda g: g.deflections_from_grid(
                        grid=grid,
                        return_in_2d=False,
                        return_binned=False,
                    ),
                    self.galaxies,
                )
            )
        else:
            return np.full((grid.shape[0], 2), 0.0)

    @reshape_returned_grid
    def traced_grid_from_grid(self, grid, return_in_2d=True):
        """Trace this plane's grid_stacks to the next plane, using its deflection angles."""

        return grid - self.deflections_from_grid(grid=grid, return_in_2d=False, return_binned=False)

    @reshape_returned_grid
    def deflections_via_potential(self, return_in_2d=True, return_binned=True):
        potential_2d = self.potential(return_in_2d=True, return_binned=False)

        deflections_y_2d = np.gradient(
            potential_2d, self.grid_stack.sub.in_2d[:, 0, 0], axis=0
        )
        deflections_x_2d = np.gradient(
            potential_2d, self.grid_stack.sub.in_2d[0, :, 1], axis=1
        )

        return np.stack((deflections_y_2d, deflections_x_2d), axis=-1)

    @reshape_returned_array
    def lensing_jacobian_a11_from_deflections_2d(
            self, return_in_2d=True, return_binned=True
    ):

        deflections_2d = self.deflections_from_grid(
            grid=grid, return_in_2d=True, return_binned=False
        )

        return 1.0 - np.gradient(
            deflections_2d[:, :, 1], self.grid_stack.in_2d[0, :, 1], axis=1
        )

    @reshape_returned_array
    def lensing_jacobian_a12_from_deflections_2d(
            self, return_in_2d=True, return_binned=True
    ):

        deflections_2d = self.deflections_from_grid(
            grid=grid, return_in_2d=True, return_binned=False
        )

        return -1.0 * np.gradient(
            deflections_2d[:, :, 1], self.grid_stack.in_2d[:, 0, 0], axis=0
        )

    @reshape_returned_array
    def lensing_jacobian_a21_from_deflections_2d(
            self, return_in_2d=True, return_binned=True
    ):

        deflections_2d = self.deflections_from_grid(
            grid=grid, return_in_2d=True, return_binned=False
        )

        return -1.0 * np.gradient(
            deflections_2d[:, :, 0], self.grid_stack.in_2d[0, :, 1], axis=1
        )

    @reshape_returned_array
    def lensing_jacobian_a22_from_deflections_2d(
            self, return_in_2d=True, return_binned=True
    ):

        deflections_2d = self.deflections_from_grid(
            grid=grid, return_in_2d=True, return_binned=False
        )

        return 1 - np.gradient(
            deflections_2d[:, :, 0], self.grid_stack.in_2d[:, 0, 0], axis=0
        )

    def lensing_jacobian(self, return_in_2d=True, return_binned=True):

        a11 = self.lensing_jacobian_a11_from_deflections_2d(
            grid=grid, return_in_2d=return_in_2d, return_binned=return_binned
        )

        a12 = self.lensing_jacobian_a12_from_deflections_2d(
            grid=grid, return_in_2d=return_in_2d, return_binned=return_binned
        )

        a21 = self.lensing_jacobian_a21_from_deflections_2d(
            grid=grid, return_in_2d=return_in_2d, return_binned=return_binned
        )

        a22 = self.lensing_jacobian_a22_from_deflections_2d(
            grid=grid, return_in_2d=return_in_2d, return_binned=return_binned
        )

        return np.array([[a11, a12], [a21, a22]])

    @reshape_returned_array
    def convergence_from_jacobian(self, return_in_2d=True, return_binned=True):

        jacobian = self.lensing_jacobian(return_in_2d=False, return_binned=False)

        convergence = 1 - 0.5 * (jacobian[0, 0] + jacobian[1, 1])

        return convergence

    @reshape_returned_array
    def shear_from_jacobian(self, return_in_2d=True, return_binned=True):

        jacobian = self.lensing_jacobian(return_in_2d=True, return_binned=False)

        gamma_1 = 0.5 * (jacobian[1, 1] - jacobian[0, 0])
        gamma_2 = -0.5 * (jacobian[0, 1] + jacobian[1, 0])

        return (gamma_1 ** 2 + gamma_2 ** 2) ** 0.5

    @reshape_returned_array
    def tangential_eigen_value_from_shear_and_convergence(
            self, return_in_2d=True, return_binned=True
    ):

        convergence = self.convergence_from_jacobian(
            return_in_2d=False, return_binned=False
        )

        shear = self.shear_from_jacobian(return_in_2d=False, return_binned=False)

        return 1 - convergence - shear

    @reshape_returned_array
    def radial_eigen_value_from_shear_and_convergence(
            self, return_in_2d=True, return_binned=True
    ):

        convergence = self.convergence_from_jacobian(
            return_in_2d=False, return_binned=False
        )

        shear = self.shear_from_jacobian(return_in_2d=False, return_binned=False)

        return 1 - convergence + shear

    @reshape_returned_array
    def magnification_from_grid(self, return_in_2d=True, return_binned=True):

        jacobian = self.lensing_jacobian(return_in_2d=False, return_binned=False)

        det_jacobian = jacobian[0, 0] * jacobian[1, 1] - jacobian[0, 1] * jacobian[1, 0]

        return 1 / det_jacobian

    def tangential_critical_curve_from_grid(self):

        lambda_tangential_2d = self.tangential_eigen_value_from_shear_and_convergence(
            return_in_2d=True, return_binned=False
        )

        tangential_critical_curve_indices = measure.find_contours(
            lambda_tangential_2d, 0
        )

        if tangential_critical_curve_indices == []:
            return []

        tangential_critical_curve = grid_util.grid_pixels_1d_to_grid_arcsec_1d(
            grid_pixels_1d=tangential_critical_curve_indices[0],
            shape=lambda_tangential_2d.shape,
            pixel_scales=(
                self.grid_stack.pixel_scale / self.grid_stack.sub_grid_size,
                self.grid_stack.pixel_scale / self.grid_stack.sub_grid_size,
            ),
            origin=self.grid_stack.mask.origin,
        )

        # Bug with offset, this fixes it for now

        tangential_critical_curve[:, 0] -= self.grid_stack.pixel_scale / 2.0
        tangential_critical_curve[:, 1] += self.grid_stack.pixel_scale / 2.0

        return tangential_critical_curve

    def tangential_caustic_from_grid(self):

        tangential_critical_curve = self.tangential_critical_curve_from_grid()

        if tangential_critical_curve == []:
            return []

        deflections_1d = self.deflections_from_grid(
            grid=tangential_critical_curve, return_in_2d=False, return_binned=False
        )

        return tangential_critical_curve - deflections_1d

    def radial_critical_curve_from_grid(self, grid):

        lambda_radial_2d = self.radial_eigen_value_from_shear_and_convergence(
            grid=grid, return_in_2d=True, return_binned=False
        )

        radial_critical_curve_indices = measure.find_contours(lambda_radial_2d, 0)

        if radial_critical_curve_indices == []:
            return []

        radial_critical_curve = grid_util.grid_pixels_1d_to_grid_arcsec_1d(
            grid_pixels_1d=radial_critical_curve_indices[0],
            shape=lambda_radial_2d.shape,
            pixel_scales=(
                grid.pixel_scale / grid.sub_grid_size,
                grid.pixel_scale / grid.sub_grid_size,
            ),
            origin=grid.mask.origin,
        )

        # Bug with offset, this fixes it for now

        radial_critical_curve[:, 0] -= grid.pixel_scale / 2.0
        radial_critical_curve[:, 1] += grid.pixel_scale / 2.0

        return radial_critical_curve

    def radial_caustic_from_grid(self, grid):

        radial_critical_curve = self.radial_critical_curve_from_grid(grid=grid)

        if radial_critical_curve == []:
            return []

        deflections_1d = self.deflections_from_grid(
            grid=radial_critical_curve, return_in_2d=False, return_binned=False
        )

        return radial_critical_curve - deflections_1d

    def critical_curves_from_grid(self, grid):
        return [
            self.tangential_critical_curve_from_grid(grid=grid),
            self.radial_critical_curve_from_grid(grid=grid),
        ]

    def caustics_from_grid(self, grid):
        return [
            self.tangential_caustic_from_grid(grid=grid),
            self.radial_caustic_from_grid(grid=grid),
        ]

    @property
    def plane_image(self):
        return lens_util.plane_image_of_galaxies_from_grid(
            shape=self.grid_stack.regular.mask.shape,
            grid=self.grid_stack.regular,
            galaxies=self.galaxies,
        )

    @property
    def mapper(self):

        galaxies_with_pixelization = list(
            filter(lambda galaxy: galaxy.pixelization is not None, self.galaxies)
        )

        if len(galaxies_with_pixelization) == 0:
            return None
        if len(galaxies_with_pixelization) == 1:

            pixelization = galaxies_with_pixelization[0].pixelization

            return pixelization.mapper_from_grid_stack_and_border(
                grid_stack=self.grid_stack,
                border=self.border,
                hyper_image=galaxies_with_pixelization[0].hyper_galaxy_image_1d,
            )

        elif len(galaxies_with_pixelization) > 1:
            raise exc.PixelizationException(
                "The number of galaxies with pixelizations in one plane is above 1"
            )

    @property
    def contribution_maps_1d_of_galaxies(self):

        contribution_maps_1d = []

        for galaxy in self.galaxies:

            if galaxy.hyper_galaxy is not None:

                contribution_map = galaxy.hyper_galaxy.contribution_map_from_hyper_images(
                    hyper_model_image=galaxy.hyper_model_image_1d,
                    hyper_galaxy_image=galaxy.hyper_galaxy_image_1d,
                )

                contribution_maps_1d.append(contribution_map)

            else:

                contribution_maps_1d.append(None)

        return contribution_maps_1d

    @property
    def centres_of_galaxy_mass_profiles(self):

        galaxies_with_mass_profiles = [
            galaxy for galaxy in self.galaxies if galaxy.has_mass_profile
        ]

        mass_profile_centres = [[] for _ in range(len(galaxies_with_mass_profiles))]

        for galaxy_index, galaxy in enumerate(galaxies_with_mass_profiles):
            mass_profile_centres[galaxy_index] = [
                profile.centre for profile in galaxy.mass_profiles
            ]
        return mass_profile_centres

    @property
    def axis_ratios_of_galaxy_mass_profiles(self):
        galaxies_with_mass_profiles = [
            galaxy for galaxy in self.galaxies if galaxy.has_mass_profile
        ]

        mass_profile_axis_ratios = [[] for _ in range(len(galaxies_with_mass_profiles))]

        for galaxy_index, galaxy in enumerate(galaxies_with_mass_profiles):
            mass_profile_axis_ratios[galaxy_index] = [
                profile.axis_ratio for profile in galaxy.mass_profiles
            ]
        return mass_profile_axis_ratios

    @property
    def phis_of_galaxy_mass_profiles(self):

        galaxies_with_mass_profiles = [
            galaxy for galaxy in self.galaxies if galaxy.has_mass_profile
        ]

        mass_profile_phis = [[] for _ in range(len(galaxies_with_mass_profiles))]

        for galaxy_index, galaxy in enumerate(galaxies_with_mass_profiles):
            mass_profile_phis[galaxy_index] = [
                profile.phi for profile in galaxy.mass_profiles
            ]
        return mass_profile_phis

    def luminosities_of_galaxies_within_circles_in_units(
        self, radius: dim.Length, unit_luminosity="eps", exposure_time=None
    ):
        """Compute the total luminosity of all galaxies in this plane within a circle of specified radius.

        See *galaxy.light_within_circle* and *light_profiles.light_within_circle* for details \
        of how this is performed.

        Parameters
        ----------
        radius : float
            The radius of the circle to compute the dimensionless mass within.
        unit_luminosity : str
            The units the luminosity is returned in (eps | counts).
        exposure_time : float
            The exposure time of the observation, which converts luminosity from electrons per second units to counts.
        """
        return list(
            map(
                lambda galaxy: galaxy.luminosity_within_circle_in_units(
                    radius=radius,
                    unit_luminosity=unit_luminosity,
                    exposure_time=exposure_time,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def luminosities_of_galaxies_within_ellipses_in_units(
        self, major_axis: dim.Length, unit_luminosity="eps", exposure_time=None
    ):
        """
        Compute the total luminosity of all galaxies in this plane within a ellipse of specified major-axis.

        The value returned by this integral is dimensionless, and a conversion factor can be specified to convert it \
        to a physical value (e.g. the photometric zeropoint).

        See *galaxy.light_within_ellipse* and *light_profiles.light_within_ellipse* for details
        of how this is performed.

        Parameters
        ----------
        major_axis : float
            The major-axis radius of the ellipse.
        unit_luminosity : str
            The units the luminosity is returned in (eps | counts).
        exposure_time : float
            The exposure time of the observation, which converts luminosity from electrons per second units to counts.
        """
        return list(
            map(
                lambda galaxy: galaxy.luminosity_within_ellipse_in_units(
                    major_axis=major_axis,
                    unit_luminosity=unit_luminosity,
                    exposure_time=exposure_time,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def masses_of_galaxies_within_circles_in_units(
        self, radius: dim.Length, unit_mass="solMass", redshift_source=None
    ):
        """Compute the total mass of all galaxies in this plane within a circle of specified radius.

        See *galaxy.angular_mass_within_circle* and *mass_profiles.angular_mass_within_circle* for details
        of how this is performed.

        Parameters
        ----------
        redshift_source
        radius : float
            The radius of the circle to compute the dimensionless mass within.
        unit_mass : str
            The units the mass is returned in (angular | solMass).

        """
        return list(
            map(
                lambda galaxy: galaxy.mass_within_circle_in_units(
                    radius=radius,
                    unit_mass=unit_mass,
                    redshift_source=redshift_source,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def masses_of_galaxies_within_ellipses_in_units(
        self, major_axis: dim.Length, unit_mass="solMass", redshift_source=None
    ):
        """Compute the total mass of all galaxies in this plane within a ellipse of specified major-axis.

        See *galaxy.angular_mass_within_ellipse* and *mass_profiles.angular_mass_within_ellipse* for details \
        of how this is performed.

        Parameters
        ----------
        redshift_source
        unit_mass
        major_axis : float
            The major-axis radius of the ellipse.

        """
        return list(
            map(
                lambda galaxy: galaxy.mass_within_ellipse_in_units(
                    major_axis=major_axis,
                    unit_mass=unit_mass,
                    redshift_source=redshift_source,
                    cosmology=self.cosmology,
                ),
                self.galaxies,
            )
        )

    def einstein_radius_in_units(self, unit_length="arcsec"):

        if self.has_mass_profile:
            return sum(
                filter(
                    None,
                    list(
                        map(
                            lambda galaxy: galaxy.einstein_radius_in_units(
                                unit_length=unit_length, cosmology=self.cosmology
                            ),
                            self.galaxies,
                        )
                    ),
                )
            )

    def einstein_mass_in_units(self, unit_mass="solMass", redshift_source=None):

        if self.has_mass_profile:
            return sum(
                filter(
                    None,
                    list(
                        map(
                            lambda galaxy: galaxy.einstein_mass_in_units(
                                unit_mass=unit_mass,
                                redshift_source=redshift_source,
                                cosmology=self.cosmology,
                            ),
                            self.galaxies,
                        )
                    ),
                )
            )

    # noinspection PyUnusedLocal
    def summarize_in_units(
        self,
        radii,
        whitespace=80,
        unit_length="arcsec",
        unit_luminosity="eps",
        unit_mass="solMass",
        redshift_source=None,
        **kwargs
    ):

        summary = ["Plane\n"]
        prefix_plane = ""

        summary += [
            af.text_util.label_and_value_string(
                label=prefix_plane + "redshift",
                value=self.redshift,
                whitespace=whitespace,
                format_string="{:.2f}",
            )
        ]

        summary += [
            af.text_util.label_and_value_string(
                label=prefix_plane + "kpc_per_arcsec",
                value=self.kpc_per_arcsec,
                whitespace=whitespace,
                format_string="{:.2f}",
            )
        ]

        angular_diameter_distance_to_earth = self.angular_diameter_distance_to_earth_in_units(
            unit_length=unit_length
        )

        summary += [
            af.text_util.label_and_value_string(
                label=prefix_plane + "angular_diameter_distance_to_earth",
                value=angular_diameter_distance_to_earth,
                whitespace=whitespace,
                format_string="{:.2f}",
            )
        ]

        for galaxy in self.galaxies:
            summary += ["\n"]
            summary += galaxy.summarize_in_units(
                radii=radii,
                whitespace=whitespace,
                unit_length=unit_length,
                unit_luminosity=unit_luminosity,
                unit_mass=unit_mass,
                redshift_source=redshift_source,
                cosmology=self.cosmology,
            )

        return summary

    @property
    def yticks(self):
        """Compute the yticks labels of this grid_stack, used for plotting the y-axis ticks when visualizing an image \
        """
        return np.linspace(
            np.amin(self.grid_stack.regular[:, 0]),
            np.amax(self.grid_stack.regular[:, 0]),
            4,
        )

    @property
    def xticks(self):
        """Compute the xticks labels of this grid_stack, used for plotting the x-axis ticks when visualizing an \
        image"""
        return np.linspace(
            np.amin(self.grid_stack.regular[:, 1]),
            np.amax(self.grid_stack.regular[:, 1]),
            4,
        )

    def blurred_profile_image_plane_image_1d_from_convolver_image(
        self, convolver_image
    ):

        image_array = self.profile_image_from_grid(
            return_in_2d=False, return_binned=True
        )
        blurring_array = self.profile_image_plane_blurring_image(return_in_2d=False)

        return convolver_image.convolve_image(
            image_array=image_array, blurring_array=blurring_array
        )

    def blurred_profile_image_plane_images_1d_of_galaxies_from_convolver_image(
        self, convolver_image
    ):

        return list(
            map(
                lambda profile_image_plane_image_1d, profile_image_plane_blurring_image_1d: convolver_image.convolve_image(
                    image_array=profile_image_plane_image_1d,
                    blurring_array=profile_image_plane_blurring_image_1d,
                ),
                self.profile_images_of_galaxies_from_grid(
                    return_in_2d=False, return_binned=True
                ),
                self.profile_image_plane_blurring_image_of_galaxies(return_in_2d=False),
            )
        )

    def visibilities_from_transformer(self, transformer):

        profile_image_plane_image_1d = self.profile_image_from_grid(
            return_in_2d=False, return_binned=True
        )

        return transformer.visibilities_from_intensities(
            intensities_1d=profile_image_plane_image_1d
        )

    def hyper_noise_map_1d_from_noise_map_1d(self, noise_map_1d):
        hyper_noise_maps_1d = self.hyper_noise_maps_1d_of_galaxies_from_noise_map_1d(
            noise_map_1d=noise_map_1d
        )
        hyper_noise_maps_1d = [
            hyper_noise_map
            for hyper_noise_map in hyper_noise_maps_1d
            if hyper_noise_map is not None
        ]
        return sum(hyper_noise_maps_1d)

    def hyper_noise_maps_1d_of_galaxies_from_noise_map_1d(self, noise_map_1d):
        """For a contribution map and noise-map, use the model hyper_galaxy galaxies to compute a hyper noise-map.

        Parameters
        -----------
        noise_map_1d : ccd.NoiseMap or ndarray
            An array describing the RMS standard deviation error in each pixel, preferably in units of electrons per
            second.
        """
        hyper_noise_maps_1d = []

        for galaxy in self.galaxies:
            if galaxy.hyper_galaxy is not None:

                hyper_noise_map_1d = galaxy.hyper_galaxy.hyper_noise_map_from_hyper_images_and_noise_map(
                    noise_map=noise_map_1d,
                    hyper_model_image=galaxy.hyper_model_image_1d,
                    hyper_galaxy_image=galaxy.hyper_galaxy_image_1d,
                )

                hyper_noise_maps_1d.append(hyper_noise_map_1d)

            else:

                hyper_noise_maps_1d.append(None)

        return hyper_noise_maps_1d


class PlanePositions(object):
    def __init__(
        self, redshift, galaxies, positions, compute_deflections=True, cosmology=None
    ):
        """A plane represents a set of galaxies at a given redshift in a ray-tracer_normal and the positions of image-plane \
        coordinates which mappers close to one another in the source-plane.

        Parameters
        -----------
        galaxies : [Galaxy]
            The list of lens galaxies in this plane.
        positions : [[[]]]
            The (y,x) arc-second coordinates of image-plane pixels which (are expected to) mappers to the same
            location(s) in the final source-plane.
        compute_deflections : bool
            If true, the deflection-angles of this plane's coordinates are calculated use its galaxy's mass-profiles.
        """

        self.redshift = redshift
        self.galaxies = galaxies
        self.positions = positions

        if compute_deflections:

            def calculate_deflections(pos):
                return sum(
                    map(lambda galaxy: galaxy.deflections_from_grid(pos), galaxies)
                )

            self.deflections = list(
                map(lambda pos: calculate_deflections(pos), self.positions)
            )

        self.cosmology = cosmology

    def trace_to_next_plane(self):
        """Trace the positions to the next plane."""
        return list(
            map(
                lambda positions, deflections: np.subtract(positions, deflections),
                self.positions,
                self.deflections,
            )
        )


class PlaneImage(scaled_array.ScaledRectangularPixelArray):
    def __init__(self, array, pixel_scales, grid, origin=(0.0, 0.0)):
        self.grid = grid
        super(PlaneImage, self).__init__(
            array=array, pixel_scales=pixel_scales, origin=origin
        )
