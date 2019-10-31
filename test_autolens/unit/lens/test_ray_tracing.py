
import autolens as al
from skimage import measure
import numpy as np
import pytest
from astropy import cosmology as cosmo
from test_autoarray.mock import mock_inversion as mock_inv


def critical_curve_via_magnification_from_tracer_and_grid(tracer, grid):
    magnification = tracer.magnification_from_grid(grid=grid)

    inverse_magnification = 1 / magnification

    critical_curves_indices = measure.find_contours(inverse_magnification.in_2d, 0)

    no_critical_curves = len(critical_curves_indices)
    contours = []
    critical_curves = []

    for jj in np.arange(no_critical_curves):
        contours.append(critical_curves_indices[jj])
        contour_x, contour_y = contours[jj].T
        pixel_coord = np.stack((contour_x, contour_y), axis=-1)

        critical_curve = grid.geometry.grid_arcsec_from_grid_pixels_1d_for_marching_squares(
            grid_pixels_1d=pixel_coord, shape_2d=magnification.sub_shape_2d
        )

        critical_curve = al.grid_irregular.manual_1d(grid=critical_curve)

        critical_curves.append(critical_curve)

    return critical_curves


def caustics_via_magnification_from_tracer_and_grid(tracer, grid):
    caustics = []

    critical_curves = critical_curve_via_magnification_from_tracer_and_grid(
        tracer=tracer, grid=grid
    )

    for i in range(len(critical_curves)):
        critical_curve = critical_curves[i]

        deflections_1d = tracer.deflections_from_grid(grid=critical_curve)

        caustic = critical_curve - deflections_1d

        caustics.append(caustic)

    return caustics


class TestAbstractTracer(object):
    class TestProperties:
        def test__total_planes(self):

            tracer = al.Tracer.from_galaxies(galaxies=[al.galaxy(redshift=0.5)])

            assert tracer.total_planes == 1

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=1.0)]
            )

            assert tracer.total_planes == 2

            tracer = al.Tracer.from_galaxies(
                galaxies=[
                    al.galaxy(redshift=1.0),
                    al.galaxy(redshift=2.0),
                    al.galaxy(redshift=3.0),
                ]
            )

            assert tracer.total_planes == 3

            tracer = al.Tracer.from_galaxies(
                galaxies=[
                    al.galaxy(redshift=1.0),
                    al.galaxy(redshift=2.0),
                    al.galaxy(redshift=1.0),
                ]
            )

            assert tracer.total_planes == 2

        def test__has_galaxy_with_light_profile(self):

            gal = al.galaxy(redshift=0.5)
            gal_lp = al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile())
            gal_mp = al.galaxy(redshift=0.5, mass_profile=al.mp.SphericalIsothermal())

            tracer = al.Tracer.from_galaxies(galaxies=[gal, gal])

            assert tracer.has_light_profile is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_mp, gal_mp])

            assert tracer.has_light_profile is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal_lp])

            assert tracer.has_light_profile is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal])

            assert tracer.has_light_profile is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal_mp])

            assert tracer.has_light_profile is True

        def test_plane_with_galaxy(self, sub_grid_7x7):

            g1 = al.galaxy(redshift=1)
            g2 = al.galaxy(redshift=2)

            tracer = al.Tracer.from_galaxies(galaxies=[g1, g2])

            assert tracer.plane_with_galaxy(g1).galaxies == [g1]
            assert tracer.plane_with_galaxy(g2).galaxies == [g2]

        def test__has_galaxy_with_mass_profile(self, sub_grid_7x7):
            gal = al.galaxy(redshift=0.5)
            gal_lp = al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile())
            gal_mp = al.galaxy(redshift=0.5, mass_profile=al.mp.SphericalIsothermal())

            tracer = al.Tracer.from_galaxies(galaxies=[gal, gal])

            assert tracer.has_mass_profile is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_mp, gal_mp])

            assert tracer.has_mass_profile is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal_lp])

            assert tracer.has_mass_profile is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal])

            assert tracer.has_mass_profile is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal_mp])

            assert tracer.has_mass_profile is True

        def test__planes_indexes_with_inversion(self):

            gal = al.galaxy(redshift=0.5)
            gal_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[gal, gal])

            assert tracer.plane_indexes_with_pixelizations == []

            tracer = al.Tracer.from_galaxies(galaxies=[gal_pix, gal])

            assert tracer.plane_indexes_with_pixelizations == [0]

            gal_pix = al.galaxy(
                redshift=1.0,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[gal_pix, gal])

            assert tracer.plane_indexes_with_pixelizations == [1]

            gal_pix_0 = al.galaxy(
                redshift=0.6,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
            )

            gal_pix_1 = al.galaxy(
                redshift=2.0,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
            )

            gal0 = al.galaxy(redshift=0.25)
            gal1 = al.galaxy(redshift=0.5)
            gal2 = al.galaxy(redshift=0.75)

            tracer = al.Tracer.from_galaxies(
                galaxies=[gal_pix_0, gal_pix_1, gal0, gal1, gal2]
            )

            assert tracer.plane_indexes_with_pixelizations == [2, 4]

        def test__has_galaxy_with_pixelization(self, sub_grid_7x7):
            gal = al.galaxy(redshift=0.5)
            gal_lp = al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile())
            gal_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[gal, gal])

            assert tracer.has_pixelization is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal_lp])

            assert tracer.has_pixelization is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_pix, gal_pix])

            assert tracer.has_pixelization is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_pix, gal])

            assert tracer.has_pixelization is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_pix, gal_lp])

            assert tracer.has_pixelization is True

        def test__has_galaxy_with_regularization(self, sub_grid_7x7):
            gal = al.galaxy(redshift=0.5)
            gal_lp = al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile())
            gal_reg = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[gal, gal])

            assert tracer.has_regularization is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal_lp])

            assert tracer.has_regularization is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_reg, gal_reg])

            assert tracer.has_regularization is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_reg, gal])

            assert tracer.has_regularization is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_reg, gal_lp])

            assert tracer.has_regularization is True

        def test__has_galaxy_with_hyper_galaxy(self, sub_grid_7x7):

            gal = al.galaxy(redshift=0.5)
            gal_lp = al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile())
            gal_hyper = al.galaxy(redshift=0.5, hyper_galaxy=al.HyperGalaxy())

            tracer = al.Tracer.from_galaxies(galaxies=[gal, gal])

            assert tracer.has_hyper_galaxy is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_lp, gal_lp])

            assert tracer.has_hyper_galaxy is False

            tracer = al.Tracer.from_galaxies(galaxies=[gal_hyper, gal_hyper])

            assert tracer.has_hyper_galaxy is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_hyper, gal])

            assert tracer.has_hyper_galaxy is True

            tracer = al.Tracer.from_galaxies(galaxies=[gal_hyper, gal_lp])

            assert tracer.has_hyper_galaxy is True

        def test__upper_plane_index_with_light_profile(self):

            g0 = al.galaxy(redshift=0.5)
            g1 = al.galaxy(redshift=1.0)
            g2 = al.galaxy(redshift=2.0)
            g3 = al.galaxy(redshift=3.0)

            g0_lp = al.galaxy(redshift=0.5, light_profile=al.lp.LightProfile())
            g1_lp = al.galaxy(redshift=1.0, light_profile=al.lp.LightProfile())
            g2_lp = al.galaxy(redshift=2.0, light_profile=al.lp.LightProfile())
            g3_lp = al.galaxy(redshift=3.0, light_profile=al.lp.LightProfile())

            tracer = al.Tracer.from_galaxies(galaxies=[g0_lp])

            assert tracer.upper_plane_index_with_light_profile == 0

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g0_lp])

            assert tracer.upper_plane_index_with_light_profile == 0

            tracer = al.Tracer.from_galaxies(galaxies=[g1_lp])

            assert tracer.upper_plane_index_with_light_profile == 0

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1_lp])

            assert tracer.upper_plane_index_with_light_profile == 1

            tracer = al.Tracer.from_galaxies(galaxies=[g0_lp, g1_lp, g2_lp])

            assert tracer.upper_plane_index_with_light_profile == 2

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2_lp])

            assert tracer.upper_plane_index_with_light_profile == 2

            tracer = al.Tracer.from_galaxies(galaxies=[g0_lp, g1, g2, g3_lp])

            assert tracer.upper_plane_index_with_light_profile == 3

            tracer = al.Tracer.from_galaxies(galaxies=[g0_lp, g1, g2_lp, g3])

            assert tracer.upper_plane_index_with_light_profile == 2

        def test__hyper_model_image_of_galaxy_with_pixelization(self, sub_grid_7x7):

            gal = al.galaxy(redshift=0.5)
            gal_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[gal, gal])

            assert tracer.hyper_galaxy_image_of_planes_with_pixelizations == [None]

            tracer = al.Tracer.from_galaxies(galaxies=[gal_pix, gal_pix])

            assert tracer.hyper_galaxy_image_of_planes_with_pixelizations == [None]

            gal_pix = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
                hyper_galaxy_image=1,
            )

            tracer = al.Tracer.from_galaxies(galaxies=[gal_pix, gal])

            assert tracer.hyper_galaxy_image_of_planes_with_pixelizations == [1]

            gal0 = al.galaxy(redshift=0.25)
            gal1 = al.galaxy(redshift=0.75)
            gal2 = al.galaxy(redshift=1.5)

            gal_pix0 = al.galaxy(
                redshift=0.5,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
                hyper_galaxy_image=1,
            )

            gal_pix1 = al.galaxy(
                redshift=2.0,
                pixelization=al.pix.Pixelization(),
                regularization=al.reg.Constant(),
                hyper_galaxy_image=2,
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[gal0, gal1, gal2, gal_pix0, gal_pix1]
            )

            assert tracer.hyper_galaxy_image_of_planes_with_pixelizations == [
                None,
                1,
                None,
                None,
                2,
            ]

    class TestPixelizations:
        def test__no_galaxy_has_regularization__returns_list_of_ones(
            self, sub_grid_7x7
        ):
            galaxy_no_pix = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_no_pix])

            assert tracer.pixelizations_of_planes == [None]

        def test__source_galaxy_has_regularization__returns_list_with_none_and_regularization(
            self, sub_grid_7x7
        ):
            galaxy_pix = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(value=1),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_pix])

            assert tracer.pixelizations_of_planes[0] is None
            assert tracer.pixelizations_of_planes[1].value == 1

        def test__both_galaxies_have_pixelization__returns_both_pixelizations(
            self, sub_grid_7x7
        ):
            galaxy_pix_0 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inv.MockPixelization(value=1),
                regularization=mock_inv.MockRegularization(matrix_shape=(3, 3)),
            )

            galaxy_pix_1 = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(value=2),
                regularization=mock_inv.MockRegularization(matrix_shape=(4, 4)),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_pix_0, galaxy_pix_1])

            assert tracer.pixelizations_of_planes[0].value == 1
            assert tracer.pixelizations_of_planes[1].value == 2

    class TestRegularizations:
        def test__no_galaxy_has_regularization__returns_empty_list(self, sub_grid_7x7):
            galaxy_no_reg = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_reg, galaxy_no_reg])

            assert tracer.regularizations_of_planes == [None]

        def test__source_galaxy_has_regularization__returns_regularizations(
            self, sub_grid_7x7
        ):
            galaxy_reg = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(value=1),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_reg = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_reg, galaxy_reg])

            assert tracer.regularizations_of_planes[0] is None
            assert tracer.regularizations_of_planes[1].shape == (1, 1)

        def test__both_galaxies_have_regularization__returns_both_regularizations(
            self, sub_grid_7x7
        ):
            galaxy_reg_0 = al.galaxy(
                redshift=0.5,
                pixelization=mock_inv.MockPixelization(value=1),
                regularization=mock_inv.MockRegularization(matrix_shape=(3, 3)),
            )

            galaxy_reg_1 = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(value=2),
                regularization=mock_inv.MockRegularization(matrix_shape=(4, 4)),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_reg_0, galaxy_reg_1])

            assert tracer.regularizations_of_planes[0].shape == (3, 3)
            assert tracer.regularizations_of_planes[1].shape == (4, 4)

    class TestGalaxyLists:
        def test__galaxy_list__comes_in_plane_redshift_order(self, sub_grid_7x7):
            g0 = al.galaxy(redshift=0.5)
            g1 = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            assert tracer.galaxies == [g0, g1]

            g2 = al.galaxy(redshift=1.0)
            g3 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2, g3])

            assert tracer.galaxies == [g0, g1, g2, g3]

            g4 = al.galaxy(redshift=0.75)
            g5 = al.galaxy(redshift=1.5)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2, g3, g4, g5])

            assert tracer.galaxies == [g0, g1, g4, g2, g3, g5]

        # def test__galaxy_in_planes_lists__comes_in_lists_of_planes_in_redshift_order(self, sub_grid_7x7):
        #     g0 = al.galaxy(redshift=0.5)
        #     g1 = al.galaxy(redshift=0.5)
        #
        #     tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])
        #
        #     assert tracer.galaxies_in_planes == [[g0, g1]]
        #
        #     g2 = al.galaxy(redshift=1.0)
        #     g3 = al.galaxy(redshift=1.0)
        #
        #     tracer = al.Tracer.from_galaxies(galaxies=[g0, g1], galaxies=[g2, g3],
        #                                                  )
        #
        #     assert tracer.galaxies_in_planes == [[g0, g1], [g2, g3]]
        #
        #     g4 = al.galaxy(redshift=0.75)
        #     g5 = al.galaxy(redshift=1.5)
        #
        #     tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2, g3, g4, g5],
        #                                            )
        #
        #     assert tracer.galaxies_in_planes == [[g0, g1], [g4], [g2, g3], [g5]]


class TestAbstractTracerCosmology(object):
    def test__2_planes__z01_and_z1(self):
        g0 = al.galaxy(redshift=0.1)
        g1 = al.galaxy(redshift=1.0)

        tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

        assert tracer.cosmology == cosmo.Planck15

        assert tracer.image_plane.arcsec_per_kpc == pytest.approx(0.525060, 1e-5)
        assert tracer.image_plane.kpc_per_arcsec == pytest.approx(1.904544, 1e-5)
        assert tracer.image_plane.angular_diameter_distance_to_earth_in_units(
            unit_length="kpc"
        ) == pytest.approx(392840, 1e-5)

        assert tracer.source_plane.arcsec_per_kpc == pytest.approx(0.1214785, 1e-5)
        assert tracer.source_plane.kpc_per_arcsec == pytest.approx(8.231907, 1e-5)
        assert tracer.source_plane.angular_diameter_distance_to_earth_in_units(
            unit_length="kpc"
        ) == pytest.approx(1697952, 1e-5)

        assert tracer.angular_diameter_distance_from_image_to_source_plane_in_units(
            unit_length="kpc"
        ) == pytest.approx(1481890.4, 1e-5)

        assert tracer.critical_surface_density_between_planes_in_units(
            i=0, j=1, unit_length="kpc", unit_mass="solMass"
        ) == pytest.approx(4.85e9, 1e-2)

        tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

        assert tracer.critical_surface_density_between_planes_in_units(
            i=0, j=1, unit_length="arcsec", unit_mass="solMass"
        ) == pytest.approx(17593241668, 1e-2)

    def test__3_planes__z01_z1__and_z2(self):

        g0 = al.galaxy(redshift=0.1)
        g1 = al.galaxy(redshift=1.0)
        g2 = al.galaxy(redshift=2.0)

        tracer = al.Tracer.from_galaxies(
            galaxies=[g0, g1, g2], cosmology=cosmo.Planck15
        )

        assert tracer.arcsec_per_kpc_proper_of_plane(i=0) == pytest.approx(
            0.525060, 1e-5
        )
        assert tracer.kpc_per_arcsec_proper_of_plane(i=0) == pytest.approx(
            1.904544, 1e-5
        )

        assert tracer.angular_diameter_distance_of_plane_to_earth_in_units(
            i=0, unit_length="kpc"
        ) == pytest.approx(392840, 1e-5)
        assert (
            tracer.angular_diameter_distance_between_planes_in_units(
                i=0, j=0, unit_length="kpc"
            )
            == 0.0
        )
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=0, j=1, unit_length="kpc"
        ) == pytest.approx(1481890.4, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=0, j=2, unit_length="kpc"
        ) == pytest.approx(1626471, 1e-5)

        assert tracer.arcsec_per_kpc_proper_of_plane(i=1) == pytest.approx(
            0.1214785, 1e-5
        )
        assert tracer.kpc_per_arcsec_proper_of_plane(i=1) == pytest.approx(
            8.231907, 1e-5
        )

        assert tracer.angular_diameter_distance_of_plane_to_earth_in_units(
            i=1, unit_length="kpc"
        ) == pytest.approx(1697952, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=1, j=0, unit_length="kpc"
        ) == pytest.approx(-2694346, 1e-5)
        assert (
            tracer.angular_diameter_distance_between_planes_in_units(
                i=1, j=1, unit_length="kpc"
            )
            == 0.0
        )
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=1, j=2, unit_length="kpc"
        ) == pytest.approx(638544, 1e-5)

        assert tracer.arcsec_per_kpc_proper_of_plane(i=2) == pytest.approx(
            0.116500, 1e-5
        )
        assert tracer.kpc_per_arcsec_proper_of_plane(i=2) == pytest.approx(
            8.58368, 1e-5
        )

        assert tracer.angular_diameter_distance_of_plane_to_earth_in_units(
            i=2, unit_length="kpc"
        ) == pytest.approx(1770512, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=2, j=0, unit_length="kpc"
        ) == pytest.approx(-4435831, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=2, j=1, unit_length="kpc"
        ) == pytest.approx(-957816)
        assert (
            tracer.angular_diameter_distance_between_planes_in_units(
                i=2, j=2, unit_length="kpc"
            )
            == 0.0
        )

        assert tracer.critical_surface_density_between_planes_in_units(
            i=0, j=1, unit_length="kpc", unit_mass="solMass"
        ) == pytest.approx(4.85e9, 1e-2)
        assert tracer.critical_surface_density_between_planes_in_units(
            i=0, j=1, unit_length="arcsec", unit_mass="solMass"
        ) == pytest.approx(17593241668, 1e-2)

        assert tracer.scaling_factor_between_planes(i=0, j=1) == pytest.approx(
            0.9500, 1e-4
        )
        assert tracer.scaling_factor_between_planes(i=0, j=2) == pytest.approx(
            1.0, 1e-4
        )
        assert tracer.scaling_factor_between_planes(i=1, j=2) == pytest.approx(
            1.0, 1e-4
        )

    def test__4_planes__z01_z1_z2_and_z3(self):

        g0 = al.galaxy(redshift=0.1)
        g1 = al.galaxy(redshift=1.0)
        g2 = al.galaxy(redshift=2.0)
        g3 = al.galaxy(redshift=3.0)

        tracer = al.Tracer.from_galaxies(
            galaxies=[g0, g1, g2, g3], cosmology=cosmo.Planck15
        )

        assert tracer.arcsec_per_kpc_proper_of_plane(i=0) == pytest.approx(
            0.525060, 1e-5
        )
        assert tracer.kpc_per_arcsec_proper_of_plane(i=0) == pytest.approx(
            1.904544, 1e-5
        )

        assert tracer.angular_diameter_distance_of_plane_to_earth_in_units(
            i=0, unit_length="kpc"
        ) == pytest.approx(392840, 1e-5)
        assert (
            tracer.angular_diameter_distance_between_planes_in_units(
                i=0, j=0, unit_length="kpc"
            )
            == 0.0
        )
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=0, j=1, unit_length="kpc"
        ) == pytest.approx(1481890.4, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=0, j=2, unit_length="kpc"
        ) == pytest.approx(1626471, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=0, j=3, unit_length="kpc"
        ) == pytest.approx(1519417, 1e-5)

        assert tracer.arcsec_per_kpc_proper_of_plane(i=1) == pytest.approx(
            0.1214785, 1e-5
        )
        assert tracer.kpc_per_arcsec_proper_of_plane(i=1) == pytest.approx(
            8.231907, 1e-5
        )

        assert tracer.angular_diameter_distance_of_plane_to_earth_in_units(
            i=1, unit_length="kpc"
        ) == pytest.approx(1697952, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=1, j=0, unit_length="kpc"
        ) == pytest.approx(-2694346, 1e-5)
        assert (
            tracer.angular_diameter_distance_between_planes_in_units(
                i=1, j=1, unit_length="kpc"
            )
            == 0.0
        )
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=1, j=2, unit_length="kpc"
        ) == pytest.approx(638544, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=1, j=3, unit_length="kpc"
        ) == pytest.approx(778472, 1e-5)

        assert tracer.arcsec_per_kpc_proper_of_plane(i=2) == pytest.approx(
            0.116500, 1e-5
        )
        assert tracer.kpc_per_arcsec_proper_of_plane(i=2) == pytest.approx(
            8.58368, 1e-5
        )

        assert tracer.angular_diameter_distance_of_plane_to_earth_in_units(
            i=2, unit_length="kpc"
        ) == pytest.approx(1770512, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=2, j=0, unit_length="kpc"
        ) == pytest.approx(-4435831, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=2, j=1, unit_length="kpc"
        ) == pytest.approx(-957816)
        assert (
            tracer.angular_diameter_distance_between_planes_in_units(
                i=2, j=2, unit_length="kpc"
            )
            == 0.0
        )
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=2, j=3, unit_length="kpc"
        ) == pytest.approx(299564)

        assert tracer.arcsec_per_kpc_proper_of_plane(i=3) == pytest.approx(
            0.12674, 1e-5
        )
        assert tracer.kpc_per_arcsec_proper_of_plane(i=3) == pytest.approx(
            7.89009, 1e-5
        )

        assert tracer.angular_diameter_distance_of_plane_to_earth_in_units(
            i=3, unit_length="kpc"
        ) == pytest.approx(1627448, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=3, j=0, unit_length="kpc"
        ) == pytest.approx(-5525155, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=3, j=1, unit_length="kpc"
        ) == pytest.approx(-1556945, 1e-5)
        assert tracer.angular_diameter_distance_between_planes_in_units(
            i=3, j=2, unit_length="kpc"
        ) == pytest.approx(-399419, 1e-5)
        assert (
            tracer.angular_diameter_distance_between_planes_in_units(
                i=3, j=3, unit_length="kpc"
            )
            == 0.0
        )

        assert tracer.critical_surface_density_between_planes_in_units(
            i=0, j=1, unit_length="kpc", unit_mass="solMass"
        ) == pytest.approx(4.85e9, 1e-2)
        assert tracer.critical_surface_density_between_planes_in_units(
            i=0, j=1, unit_length="arcsec", unit_mass="solMass"
        ) == pytest.approx(17593241668, 1e-2)

        assert tracer.scaling_factor_between_planes(i=0, j=1) == pytest.approx(
            0.9348, 1e-4
        )
        assert tracer.scaling_factor_between_planes(i=0, j=2) == pytest.approx(
            0.984, 1e-4
        )
        assert tracer.scaling_factor_between_planes(i=0, j=3) == pytest.approx(
            1.0, 1e-4
        )
        assert tracer.scaling_factor_between_planes(i=1, j=2) == pytest.approx(
            0.754, 1e-4
        )
        assert tracer.scaling_factor_between_planes(i=1, j=3) == pytest.approx(
            1.0, 1e-4
        )
        assert tracer.scaling_factor_between_planes(i=2, j=3) == pytest.approx(
            1.0, 1e-4
        )

    def test__6_galaxies__tracer_planes_are_correct(self):

        g0 = al.galaxy(redshift=2.0)
        g1 = al.galaxy(redshift=2.0)
        g2 = al.galaxy(redshift=0.1)
        g3 = al.galaxy(redshift=3.0)
        g4 = al.galaxy(redshift=1.0)
        g5 = al.galaxy(redshift=3.0)

        tracer = al.Tracer.from_galaxies(
            galaxies=[g0, g1, g2, g3, g4, g5], cosmology=cosmo.Planck15
        )

        assert tracer.planes[0].galaxies == [g2]
        assert tracer.planes[1].galaxies == [g4]
        assert tracer.planes[2].galaxies == [g0, g1]
        assert tracer.planes[3].galaxies == [g3, g5]


class TestAbstractTracerLensing(object):
    class TestTracedGridsFromGrid:
        def test__x2_planes__no_galaxy__image_and_source_planes_setup__same_coordinates(
            self, sub_grid_7x7
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=1.0)]
            )

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            assert traced_grids_of_planes[0][0] == pytest.approx(
                np.array([1.25, -1.25]), 1e-3
            )
            assert traced_grids_of_planes[0][1] == pytest.approx(
                np.array([1.25, -0.75]), 1e-3
            )
            assert traced_grids_of_planes[0][2] == pytest.approx(
                np.array([0.75, -1.25]), 1e-3
            )
            assert traced_grids_of_planes[0][3] == pytest.approx(
                np.array([0.75, -0.75]), 1e-3
            )

            assert traced_grids_of_planes[1][0] == pytest.approx(
                np.array([1.25, -1.25]), 1e-3
            )
            assert traced_grids_of_planes[1][1] == pytest.approx(
                np.array([1.25, -0.75]), 1e-3
            )
            assert traced_grids_of_planes[1][2] == pytest.approx(
                np.array([0.75, -1.25]), 1e-3
            )
            assert traced_grids_of_planes[1][3] == pytest.approx(
                np.array([0.75, -0.75]), 1e-3
            )

        def test__x2_planes__sis_lens__traced_grid_includes_deflections__on_planes_setup(
            self, sub_grid_7x7_simple, gal_x1_mp
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[gal_x1_mp, al.galaxy(redshift=1.0)]
            )

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7_simple
            )

            assert traced_grids_of_planes[0][0] == pytest.approx(
                np.array([1.0, 1.0]), 1e-3
            )
            assert traced_grids_of_planes[0][1] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )
            assert traced_grids_of_planes[0][2] == pytest.approx(
                np.array([1.0, 1.0]), 1e-3
            )
            assert traced_grids_of_planes[0][3] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )

            assert traced_grids_of_planes[1][0] == pytest.approx(
                np.array([1.0 - 0.707, 1.0 - 0.707]), 1e-3
            )
            assert traced_grids_of_planes[1][1] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )
            assert traced_grids_of_planes[1][2] == pytest.approx(
                np.array([1.0 - 0.707, 1.0 - 0.707]), 1e-3
            )
            assert traced_grids_of_planes[1][3] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )

        def test__same_as_above_but_2_sis_lenses__deflections_double(
            self, sub_grid_7x7_simple, gal_x1_mp
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[gal_x1_mp, gal_x1_mp, al.galaxy(redshift=1.0)]
            )

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7_simple
            )

            assert traced_grids_of_planes[0][0] == pytest.approx(
                np.array([1.0, 1.0]), 1e-3
            )
            assert traced_grids_of_planes[0][1] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )
            assert traced_grids_of_planes[0][2] == pytest.approx(
                np.array([1.0, 1.0]), 1e-3
            )
            assert traced_grids_of_planes[0][3] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )

            assert traced_grids_of_planes[1][0] == pytest.approx(
                np.array([1.0 - 2.0 * 0.707, 1.0 - 2.0 * 0.707]), 1e-3
            )
            assert traced_grids_of_planes[1][1] == pytest.approx(
                np.array([-1.0, 0.0]), 1e-3
            )
            assert traced_grids_of_planes[1][2] == pytest.approx(
                np.array([1.0 - 2.0 * 0.707, 1.0 - 2.0 * 0.707]), 1e-3
            )

            assert traced_grids_of_planes[1][3] == pytest.approx(
                np.array([-1.0, 0.0]), 1e-3
            )

        def test__4_planes__grids_are_correct__sis_mass_profile(
            self, sub_grid_7x7_simple
        ):

            g0 = al.galaxy(
                redshift=2.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=2.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g2 = al.galaxy(
                redshift=0.1,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g3 = al.galaxy(
                redshift=3.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g4 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g5 = al.galaxy(
                redshift=3.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, g2, g3, g4, g5], cosmology=cosmo.Planck15
            )

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7_simple
            )

            # The scaling factors are as follows and were computed independently from the test_autoarray.
            beta_01 = 0.9348
            beta_02 = 0.9839601
            # Beta_03 = 1.0
            beta_12 = 0.7539734
            # Beta_13 = 1.0
            # Beta_23 = 1.0

            val = np.sqrt(2) / 2.0

            assert traced_grids_of_planes[0][0] == pytest.approx(
                np.array([1.0, 1.0]), 1e-4
            )
            assert traced_grids_of_planes[0][1] == pytest.approx(
                np.array([1.0, 0.0]), 1e-4
            )

            assert traced_grids_of_planes[1][0] == pytest.approx(
                np.array([(1.0 - beta_01 * val), (1.0 - beta_01 * val)]), 1e-4
            )
            assert traced_grids_of_planes[1][1] == pytest.approx(
                np.array([(1.0 - beta_01 * 1.0), 0.0]), 1e-4
            )

            defl11 = g0.deflections_from_grid(
                grid=al.grid.manual_2d(
                    [[[(1.0 - beta_01 * val), (1.0 - beta_01 * val)]]]
                )
            )
            defl12 = g0.deflections_from_grid(
                grid=al.grid.manual_2d([[[(1.0 - beta_01 * 1.0), 0.0]]])
            )

            assert traced_grids_of_planes[2][0] == pytest.approx(
                np.array(
                    [
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 0]),
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 1]),
                    ]
                ),
                1e-4,
            )
            assert traced_grids_of_planes[2][1] == pytest.approx(
                np.array([(1.0 - beta_02 * 1.0 - beta_12 * defl12[0, 0]), 0.0]), 1e-4
            )

            assert traced_grids_of_planes[3][1] == pytest.approx(
                np.array([1.0, 0.0]), 1e-4
            )

        def test__x2_planes__sis_lens__upper_plane_limit_removes_final_plane(
            self, sub_grid_7x7_simple, gal_x1_mp
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[gal_x1_mp, al.galaxy(redshift=1.0)]
            )

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7_simple, plane_index_limit=0
            )

            assert traced_grids_of_planes[0][0] == pytest.approx(
                np.array([1.0, 1.0]), 1e-3
            )
            assert traced_grids_of_planes[0][1] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )
            assert traced_grids_of_planes[0][2] == pytest.approx(
                np.array([1.0, 1.0]), 1e-3
            )
            assert traced_grids_of_planes[0][3] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )

            assert len(traced_grids_of_planes) == 1

        def test__4_planes__grids_are_correct__upper_plane_limit_removes_final_planes(
            self, sub_grid_7x7_simple
        ):

            g0 = al.galaxy(
                redshift=2.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=2.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g2 = al.galaxy(
                redshift=0.1,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g3 = al.galaxy(
                redshift=3.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g4 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g5 = al.galaxy(
                redshift=3.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, g2, g3, g4, g5], cosmology=cosmo.Planck15
            )

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7_simple, plane_index_limit=1
            )

            # The scaling factors are as follows and were computed independently from the test_autoarray.
            beta_01 = 0.9348
            beta_02 = 0.9839601
            # Beta_03 = 1.0
            beta_12 = 0.7539734
            # Beta_13 = 1.0
            # Beta_23 = 1.0

            val = np.sqrt(2) / 2.0

            assert traced_grids_of_planes[0][0] == pytest.approx(
                np.array([1.0, 1.0]), 1e-4
            )
            assert traced_grids_of_planes[0][1] == pytest.approx(
                np.array([1.0, 0.0]), 1e-4
            )

            assert traced_grids_of_planes[1][0] == pytest.approx(
                np.array([(1.0 - beta_01 * val), (1.0 - beta_01 * val)]), 1e-4
            )
            assert traced_grids_of_planes[1][1] == pytest.approx(
                np.array([(1.0 - beta_01 * 1.0), 0.0]), 1e-4
            )

            assert len(traced_grids_of_planes) == 2

        # def test__grid_attributes_passed(self, sub_grid_7x7):
        #     tracer = al.Tracer.from_galaxies(
        #         galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=0.5)],
        #
        #     )
        #
        #     assert (
        #         tracer.image_plane.grid.mask
        #         == sub_grid_7x7.unlensed_unsubbed_1d.mask
        #     ).all()
        #     assert (
        #         tracer.image_plane.grid.mask == sub_grid_7x7.mask
        #     ).all()
        #     assert (
        #         tracer.source_plane.grid.mask
        #         == sub_grid_7x7.unlensed_unsubbed_1d.mask
        #     ).all()
        #     assert (
        #         tracer.source_plane.grid.mask == sub_grid_7x7.mask
        #     ).all()

    class TestProfileImages:
        def test__x1_plane__single_plane_tracer(self, sub_grid_7x7):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )
            g2 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=3.0)
            )

            image_plane = al.plane(galaxies=[g0, g1, g2])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            image_plane_profile_image = image_plane.profile_image_from_grid(
                grid=sub_grid_7x7
            )

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert tracer_profile_image.shape_2d == (7, 7)
            assert (tracer_profile_image == image_plane_profile_image).all()

        def test__x2_planes__galaxy_light__no_mass__image_sum_of_image_and_source_plane(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            image_plane = al.plane(galaxies=[g0])
            source_plane = al.plane(galaxies=[g1])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            image = image_plane.profile_image_from_grid(
                grid=sub_grid_7x7
            ) + source_plane.profile_image_from_grid(grid=sub_grid_7x7)

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert tracer_profile_image.shape_2d == (7, 7)
            assert image == pytest.approx(tracer_profile_image, 1.0e-4)

        def test__x2_planes__galaxy_light_mass_sis__source_plane_image_includes_deflections(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            image_plane = al.plane(galaxies=[g0])

            source_plane_grid = image_plane.traced_grid_from_grid(grid=sub_grid_7x7)

            source_plane = al.plane(galaxies=[g1])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            image = image_plane.profile_image_from_grid(
                grid=sub_grid_7x7
            ) + source_plane.profile_image_from_grid(grid=source_plane_grid)

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert image == pytest.approx(tracer_profile_image, 1.0e-4)

        def test__x2_planes__image__compare_to_galaxy_images(self, sub_grid_7x7):
            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )
            g2 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=3.0)
            )

            g0_image = g0.profile_image_from_grid(grid=sub_grid_7x7)

            g1_image = g1.profile_image_from_grid(grid=sub_grid_7x7)

            g2_image = g2.profile_image_from_grid(grid=sub_grid_7x7)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert tracer_profile_image == pytest.approx(
                g0_image + g1_image + g2_image, 1.0e-4
            )

        def test__x2_planes__returns_image_of_each_plane(self, sub_grid_7x7):
            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            g1 = al.galaxy(
                redshift=1.0,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            image_plane = al.plane(galaxies=[g0])

            source_plane_grid = image_plane.traced_grid_from_grid(grid=sub_grid_7x7)

            source_plane = al.plane(galaxies=[g1])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            plane_profile_image = image_plane.profile_image_from_grid(
                grid=sub_grid_7x7
            ) + source_plane.profile_image_from_grid(grid=source_plane_grid)

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert tracer_profile_image == pytest.approx(plane_profile_image, 1.0e-4)

        def test__x3_planes___light_no_mass_in_each_plane__image_of_each_plane_is_galaxy_image(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.1, light_profile=al.lp.EllipticalSersic(intensity=0.1)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.2)
            )
            g2 = al.galaxy(
                redshift=2.0, light_profile=al.lp.EllipticalSersic(intensity=0.3)
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, g2], cosmology=cosmo.Planck15
            )

            plane_0 = al.plane(galaxies=[g0])
            plane_1 = al.plane(galaxies=[g1])
            plane_2 = al.plane(galaxies=[g2])

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            image = (
                plane_0.profile_image_from_grid(grid=sub_grid_7x7)
                + plane_1.profile_image_from_grid(grid=traced_grids_of_planes[1])
                + plane_2.profile_image_from_grid(grid=traced_grids_of_planes[2])
            )

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert image.shape_2d == (7, 7)
            assert image == pytest.approx(tracer_profile_image, 1.0e-4)

        def test__x3_planes__galaxy_light_mass_sis__source_plane_image_includes_deflections(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.1, light_profile=al.lp.EllipticalSersic(intensity=0.1)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.2)
            )
            g2 = al.galaxy(
                redshift=2.0, light_profile=al.lp.EllipticalSersic(intensity=0.3)
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, g2], cosmology=cosmo.Planck15
            )

            plane_0 = tracer.planes[0]
            plane_1 = tracer.planes[1]
            plane_2 = tracer.planes[2]

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            image = (
                plane_0.profile_image_from_grid(grid=sub_grid_7x7)
                + plane_1.profile_image_from_grid(grid=traced_grids_of_planes[1])
                + plane_2.profile_image_from_grid(grid=traced_grids_of_planes[2])
            )

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert image.shape_2d == (7, 7)
            assert image == pytest.approx(tracer_profile_image, 1.0e-4)

        def test__x3_planes__same_as_above_more_galaxies(self, sub_grid_7x7):
            g0 = al.galaxy(
                redshift=0.1, light_profile=al.lp.EllipticalSersic(intensity=0.1)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.2)
            )
            g2 = al.galaxy(
                redshift=2.0, light_profile=al.lp.EllipticalSersic(intensity=0.3)
            )
            g3 = al.galaxy(
                redshift=0.1, light_profile=al.lp.EllipticalSersic(intensity=0.4)
            )
            g4 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.5)
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, g2, g3, g4], cosmology=cosmo.Planck15
            )

            plane_0 = al.plane(galaxies=[g0, g3])
            plane_1 = al.plane(galaxies=[g1, g4])
            plane_2 = al.plane(galaxies=[g2])

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            image = (
                plane_0.profile_image_from_grid(grid=sub_grid_7x7)
                + plane_1.profile_image_from_grid(grid=traced_grids_of_planes[1])
                + plane_2.profile_image_from_grid(grid=traced_grids_of_planes[2])
            )

            tracer_profile_image = tracer.profile_image_from_grid(grid=sub_grid_7x7)

            assert image.shape_2d == (7, 7)
            assert image == pytest.approx(tracer_profile_image, 1.0e-4)

        def test__profile_images_of_planes__planes_without_light_profiles_are_all_zeros(
            self, sub_grid_7x7
        ):

            g0 = al.galaxy(
                redshift=0.1, light_profile=al.lp.EllipticalSersic(intensity=0.1)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.2)
            )
            g2 = al.galaxy(redshift=2.0)

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, g2], cosmology=cosmo.Planck15
            )

            plane_0 = al.plane(galaxies=[g0])
            plane_1 = al.plane(galaxies=[g1])

            plane_0_image = plane_0.profile_image_from_grid(grid=sub_grid_7x7)

            plane_1_image = plane_1.profile_image_from_grid(grid=sub_grid_7x7)

            tracer_profile_image_of_planes = tracer.profile_images_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            assert len(tracer_profile_image_of_planes) == 3

            assert tracer_profile_image_of_planes[0].shape_2d == (7, 7)
            assert tracer_profile_image_of_planes[0] == pytest.approx(
                plane_0_image, 1.0e-4
            )

            assert tracer_profile_image_of_planes[1].shape_2d == (7, 7)
            assert tracer_profile_image_of_planes[1] == pytest.approx(
                plane_1_image, 1.0e-4
            )

            assert tracer_profile_image_of_planes[2].shape_2d == (7, 7)
            assert (
                tracer_profile_image_of_planes[2].in_2d_binned == np.zeros((7, 7))
            ).all()

        def test__x1_plane__padded_image__compare_to_galaxy_images_using_padded_grid_stack(
            self, sub_grid_7x7
        ):
            padded_grid = sub_grid_7x7.padded_grid_from_kernel_shape(
                kernel_shape=(3, 3)
            )

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )
            g2 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=3.0)
            )

            padded_g0_image = g0.profile_image_from_grid(grid=padded_grid)

            padded_g1_image = g1.profile_image_from_grid(grid=padded_grid)

            padded_g2_image = g2.profile_image_from_grid(grid=padded_grid)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            padded_tracer_profile_image = tracer.padded_profile_image_from_grid_and_psf_shape(
                grid=sub_grid_7x7, psf_shape=(3, 3)
            )

            assert padded_tracer_profile_image.shape_2d == (9, 9)
            assert padded_tracer_profile_image == pytest.approx(
                padded_g0_image + padded_g1_image + padded_g2_image, 1.0e-4
            )

        def test__x3_planes__padded_2d_image_from_plane__mapped_correctly(
            self, sub_grid_7x7
        ):
            padded_grid = sub_grid_7x7.padded_grid_from_kernel_shape(
                kernel_shape=(3, 3)
            )

            g0 = al.galaxy(
                redshift=0.1, light_profile=al.lp.EllipticalSersic(intensity=0.1)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.2)
            )
            g2 = al.galaxy(
                redshift=2.0, light_profile=al.lp.EllipticalSersic(intensity=0.3)
            )

            padded_g0_image = g0.profile_image_from_grid(grid=padded_grid)

            padded_g1_image = g1.profile_image_from_grid(grid=padded_grid)

            padded_g2_image = g2.profile_image_from_grid(grid=padded_grid)

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, g2], cosmology=cosmo.Planck15
            )

            padded_tracer_profile_image = tracer.padded_profile_image_from_grid_and_psf_shape(
                grid=sub_grid_7x7, psf_shape=(3, 3)
            )

            assert padded_tracer_profile_image.shape_2d == (9, 9)
            assert padded_tracer_profile_image == pytest.approx(
                padded_g0_image + padded_g1_image + padded_g2_image, 1.0e-4
            )

        def test__galaxy_image_dict_from_grid(self, sub_grid_7x7):

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
                light_profile=al.lp.EllipticalSersic(intensity=2.0),
            )

            g2 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=3.0)
            )

            g3 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=5.0)
            )

            g0_image = g0.profile_image_from_grid(grid=sub_grid_7x7)
            g1_image = g1.profile_image_from_grid(grid=sub_grid_7x7)
            g2_image = g2.profile_image_from_grid(grid=sub_grid_7x7)

            g1_deflections = g1.deflections_from_grid(grid=sub_grid_7x7)

            source_grid_7x7 = sub_grid_7x7 - g1_deflections

            g3_image = g3.profile_image_from_grid(grid=source_grid_7x7)

            tracer = al.Tracer.from_galaxies(
                galaxies=[g3, g1, g0, g2], cosmology=cosmo.Planck15
            )

            image_1d_dict = tracer.galaxy_profile_image_dict_from_grid(
                grid=sub_grid_7x7
            )

            assert (image_1d_dict[g0].in_1d == g0_image).all()
            assert (image_1d_dict[g1].in_1d == g1_image).all()
            assert (image_1d_dict[g2].in_1d == g2_image).all()
            assert (image_1d_dict[g3].in_1d == g3_image).all()

            image_dict = tracer.galaxy_profile_image_dict_from_grid(grid=sub_grid_7x7)

            assert (image_dict[g0].in_2d == g0_image.in_2d).all()
            assert (image_dict[g1].in_2d == g1_image.in_2d).all()
            assert (image_dict[g2].in_2d == g2_image.in_2d).all()
            assert (image_dict[g3].in_2d == g3_image.in_2d).all()

    class TestConvergence:
        def test__galaxy_mass_sis__no_source_plane_convergence(self, sub_grid_7x7):

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(redshift=0.5)

            image_plane = al.plane(galaxies=[g0])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            image_plane_convergence = image_plane.convergence_from_grid(
                grid=sub_grid_7x7
            )

            tracer_convergence = tracer.convergence_from_grid(grid=sub_grid_7x7)

            assert image_plane_convergence.shape_2d == (7, 7)
            assert (image_plane_convergence == tracer_convergence).all()

        def test__galaxy_entered_3_times__both_planes__different_convergence_for_each(
            self, sub_grid_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )
            g2 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=3.0),
            )

            g0_convergence = g0.convergence_from_grid(grid=sub_grid_7x7)

            g1_convergence = g1.convergence_from_grid(grid=sub_grid_7x7)

            g2_convergence = g2.convergence_from_grid(grid=sub_grid_7x7)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            image_plane_convergence = tracer.image_plane.convergence_from_grid(
                grid=sub_grid_7x7
            )

            source_plane_convergence = tracer.source_plane.convergence_from_grid(
                grid=sub_grid_7x7
            )

            tracer_convergence = tracer.convergence_from_grid(grid=sub_grid_7x7)

            assert image_plane_convergence == pytest.approx(
                g0_convergence + g1_convergence, 1.0e-4
            )
            assert (source_plane_convergence == g2_convergence).all()
            assert tracer_convergence == pytest.approx(
                g0_convergence + g1_convergence + g2_convergence, 1.0e-4
            )

        def test__no_galaxy_has_mass_profile__convergence_returned_as_zeros(
            self, sub_grid_7x7
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=0.5)]
            )

            assert (
                tracer.convergence_from_grid(grid=sub_grid_7x7).in_2d_binned
                == np.zeros(shape=(7, 7))
            ).all()

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.1), al.galaxy(redshift=0.2)]
            )

            assert (
                tracer.convergence_from_grid(grid=sub_grid_7x7).in_2d_binned
                == np.zeros(shape=(7, 7))
            ).all()

    class TestPotential:
        def test__galaxy_mass_sis__no_source_plane_potential(self, sub_grid_7x7):

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(redshift=0.5)

            image_plane = al.plane(galaxies=[g0])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            image_plane_potential = image_plane.potential_from_grid(grid=sub_grid_7x7)

            tracer_potential = tracer.potential_from_grid(grid=sub_grid_7x7)

            assert image_plane_potential.shape_2d == (7, 7)
            assert (image_plane_potential == tracer_potential).all()

        def test__galaxy_entered_3_times__both_planes__different_potential_for_each(
            self, sub_grid_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )
            g2 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=3.0),
            )

            g0_potential = g0.potential_from_grid(grid=sub_grid_7x7)

            g1_potential = g1.potential_from_grid(grid=sub_grid_7x7)

            g2_potential = g2.potential_from_grid(grid=sub_grid_7x7)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            image_plane_potential = tracer.image_plane.potential_from_grid(
                grid=sub_grid_7x7
            )

            source_plane_potential = tracer.source_plane.potential_from_grid(
                grid=sub_grid_7x7
            )

            tracer_potential = tracer.potential_from_grid(grid=sub_grid_7x7)

            assert image_plane_potential == pytest.approx(
                g0_potential + g1_potential, 1.0e-4
            )
            assert (source_plane_potential == g2_potential).all()
            assert tracer_potential == pytest.approx(
                g0_potential + g1_potential + g2_potential, 1.0e-4
            )

        def test__no_galaxy_has_mass_profile__potential_returned_as_zeros(
            self, sub_grid_7x7
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=0.5)]
            )

            assert (
                tracer.potential_from_grid(grid=sub_grid_7x7).in_2d_binned
                == np.zeros(shape=(7, 7))
            ).all()

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.1), al.galaxy(redshift=0.2)]
            )

            assert (
                tracer.potential_from_grid(grid=sub_grid_7x7).in_2d_binned
                == np.zeros(shape=(7, 7))
            ).all()

    class TestDeflections:
        def test__galaxy_mass_sis__source_plane_no_mass__deflections_is_ignored(
            self, sub_grid_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(redshift=0.5)

            image_plane = al.plane(galaxies=[g0])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            image_plane_deflections = image_plane.deflections_from_grid(
                grid=sub_grid_7x7
            )

            tracer_deflections = tracer.deflections_from_grid(grid=sub_grid_7x7)

            assert tracer_deflections.shape_2d == (7, 7)
            assert (image_plane_deflections == tracer_deflections).all()

        def test__galaxy_entered_3_times__different_deflections_for_each(
            self, sub_grid_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )
            g2 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=3.0),
            )

            g0_deflections = g0.deflections_from_grid(grid=sub_grid_7x7)

            g1_deflections = g1.deflections_from_grid(grid=sub_grid_7x7)

            g2_deflections = g2.deflections_from_grid(grid=sub_grid_7x7)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            image_plane_deflections = tracer.image_plane.deflections_from_grid(
                grid=sub_grid_7x7
            )

            source_plane_deflections = tracer.source_plane.deflections_from_grid(
                grid=sub_grid_7x7
            )

            tracer_deflections = tracer.deflections_from_grid(grid=sub_grid_7x7)

            assert image_plane_deflections == pytest.approx(
                g0_deflections + g1_deflections, 1.0e-4
            )
            assert source_plane_deflections == pytest.approx(g2_deflections, 1.0e-4)
            assert tracer_deflections == pytest.approx(
                g0_deflections + g1_deflections + g2_deflections, 1.0e-4
            )

        def test__no_galaxy_has_mass_profile__deflections_returned_as_zeros(
            self, sub_grid_7x7
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=0.5)]
            )

            tracer_deflections = tracer.deflections_from_grid(grid=sub_grid_7x7)

            assert (
                tracer_deflections.in_2d_binned[:, :, 0] == np.zeros(shape=(7, 7))
            ).all()
            assert (
                tracer_deflections.in_2d_binned[:, :, 1] == np.zeros(shape=(7, 7))
            ).all()

    class TestDeflectionAnglesviaPotential(object):
        def test__compare_tracer_deflections_via_potential_and_calculation(self):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            g1 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            deflections_via_calculation = tracer.deflections_from_grid(grid=grid)

            deflections_via_potential = tracer.deflections_via_potential_from_grid(
                grid=grid
            )

            mean_error = np.mean(
                deflections_via_potential - deflections_via_calculation
            )

            assert mean_error < 1e-4

        def test__deflections_via_potential_same_as_its_planes___use_multiple_planes(
                self
        ):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.1,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            plane_0 = al.plane(galaxies=[g0])
            plane_1 = al.plane(galaxies=[g1])

            g0_deflections = plane_0.deflections_via_potential_from_grid(grid=grid)
            g1_deflections = plane_1.deflections_via_potential_from_grid(grid=grid)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            deflections = tracer.deflections_via_potential_from_grid(grid=grid)

            assert deflections == pytest.approx(g0_deflections + g1_deflections, 1.0e-4)

    class TestJacobian(object):
        def test__jacobian_components__two_component_galaxy_plane(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            plane_0 = al.plane(galaxies=[g0])
            plane_1 = al.plane(galaxies=[g1])

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            jacobian = tracer.jacobian_from_grid(grid=grid)

            A_12 = jacobian[0][1]
            A_21 = jacobian[1][0]

            mean_error = np.mean(A_12 - A_21)

            assert mean_error < 1e-4

            jacobian = tracer.jacobian_from_grid(grid=grid)

            A_12 = jacobian[0][1]
            A_21 = jacobian[1][0]

            mean_error = np.mean(A_12 - A_21)

            assert mean_error < 1e-4

    class TestConvergenceviaJacobian(object):
        def test__compare_plane_convergence_via_jacobian_and_calculation(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            convergence_via_calculation = tracer.convergence_from_grid(grid=grid)

            convergence_via_jacobian = tracer.convergence_via_jacobian_from_grid(
                grid=grid
            )

            mean_error = np.mean(convergence_via_jacobian - convergence_via_calculation)

            assert mean_error < 1e-1

        def test__convergence_sub_grid_binning_two_component_galaxy_plane(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            convergence = tracer.convergence_via_jacobian_from_grid(grid=grid)

            pixel_first_binned = convergence.in_1d_binned[0]
            pixel_first_binned_manual = (
                                                convergence[0] + convergence[1] + convergence[2] + convergence[3]
                                        ) / 4

            assert pixel_first_binned == pytest.approx(pixel_first_binned_manual, 1e-4)

            last_pixel_binned = convergence.in_1d_binned[99]

            last_pixel_binned_manual = (
                                               convergence[399]
                                               + convergence[398]
                                               + convergence[397]
                                               + convergence[396]
                                       ) / 4

            assert last_pixel_binned == pytest.approx(last_pixel_binned_manual, 1e-4)

            convergence_via_calculation = tracer.convergence_from_grid(grid=grid)

            convergence_via_jacobian = tracer.convergence_via_jacobian_from_grid(
                grid=grid
            )

            mean_error = np.mean(convergence_via_jacobian - convergence_via_calculation)

            assert convergence_via_jacobian.in_1d_binned.shape == (400,)
            assert mean_error < 1e-1

        def test__plane_convergence_via_jacobian_same_as_multiple_galaxies(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g2 = al.galaxy(redshift=1.0)

            plane_0 = al.plane(galaxies=[g0])
            plane_1 = al.plane(galaxies=[g1])

            plane_0_convergence = plane_0.convergence_via_jacobian_from_grid(grid=grid)
            plane_1_convergence = plane_1.convergence_via_jacobian_from_grid(grid=grid)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            convergence = tracer.convergence_via_jacobian_from_grid(grid=grid)

            assert convergence == pytest.approx(plane_0_convergence + plane_1_convergence, 1.0e-8)

    class TestShearviaJacobian(object):
        def test__shear_sub_grid_binning_two_component_galaxy_plane(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            shear = tracer.shear_via_jacobian_from_grid(grid=grid)

            first_pixel_binned = shear.in_1d_binned[0]
            first_pixel_binned_manual = (shear[0] + shear[1] + shear[2] + shear[3]) / 4

            assert first_pixel_binned == pytest.approx(first_pixel_binned_manual, 1e-4)

            last_pixel_binned = shear.in_1d_binned[99]

            last_pixel_binned_manual = (
                                               shear[399] + shear[398] + shear[397] + shear[396]
                                       ) / 4

            assert last_pixel_binned == pytest.approx(last_pixel_binned_manual, 1e-4)

        def test__plane_shear_via_jacobian_same_as_multiple_galaxies(self):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.05, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=2.0),
            )

            g2 = al.galaxy(redshift=1.0)

            plane_0 = al.plane(galaxies=[g0])
            plane_1 = al.plane(galaxies=[g1])

            plane_0_shear = plane_0.shear_via_jacobian_from_grid(grid=grid)
            plane_1_shear = plane_1.shear_via_jacobian_from_grid(grid=grid)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            shear = tracer.shear_via_jacobian_from_grid(grid=grid)

            assert shear == pytest.approx(plane_0_shear + plane_1_shear, 1.0e-8)

    class TestMagnification(object):
        def test__compare_magnification_from_eigen_values_and_from_determinant__two_component_galaxy_plane(
                self
        ):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            g2 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            magnification_via_determinant = tracer.magnification_from_grid(grid=grid)

            tangential_eigen_value = tracer.tangential_eigen_value_from_grid(grid=grid)

            radal_eigen_value = tracer.radial_eigen_value_from_grid(grid=grid)

            magnification_via_eigen_values = 1 / (
                    tangential_eigen_value * radal_eigen_value
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_eigen_values
            )

            assert mean_error < 1e-4

            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=2)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            magnification_via_determinant = tracer.magnification_from_grid(grid=grid)

            tangential_eigen_value = tracer.tangential_eigen_value_from_grid(grid=grid)

            radal_eigen_value = tracer.radial_eigen_value_from_grid(grid=grid)

            magnification_via_eigen_values = 1 / (
                    tangential_eigen_value * radal_eigen_value
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_eigen_values
            )

            assert mean_error < 1e-4

        def test__compare_magnification_from_determinant_and_from_convergence_and_shear__two_component_galaxy(
                self
        ):
            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            g2 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            magnification_via_determinant = tracer.magnification_from_grid(grid=grid)

            convergence = tracer.convergence_via_jacobian_from_grid(grid=grid)

            shear = tracer.shear_via_jacobian_from_grid(grid=grid)

            magnification_via_convergence_and_shear = 1 / (
                    (1 - convergence) ** 2 - shear ** 2
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_convergence_and_shear
            )

            assert mean_error < 1e-4

            grid = al.grid.uniform(shape_2d=(10, 10), pixel_scales=0.05, sub_size=2)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            magnification_via_determinant = tracer.magnification_from_grid(grid=grid)

            convergence = tracer.convergence_via_jacobian_from_grid(grid=grid)

            shear = tracer.shear_via_jacobian_from_grid(grid=grid)

            magnification_via_convergence_and_shear = 1 / (
                    (1 - convergence) ** 2 - shear ** 2
            )

            mean_error = np.mean(
                magnification_via_determinant - magnification_via_convergence_and_shear
            )

            assert mean_error < 1e-4

    class TestCriticalCurvesandCaustics(object):
        def test__compare_tangential_critical_curves_from_magnification_and_lamda_t__reg_grid_two_component_galaxy(
                self
        ):
            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.1, 0.1), einstein_radius=2.0
                ),
            )

            g2 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            critical_curve_tangential_from_magnification = critical_curve_via_magnification_from_tracer_and_grid(
                tracer=tracer, grid=grid
            )[
                0
            ]

            critical_curve_tangential_from_lambda_t = tracer.critical_curves_from_grid(
                grid=grid
            )[0]

            assert critical_curve_tangential_from_lambda_t == pytest.approx(
                critical_curve_tangential_from_magnification, 1e-4
            )

            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=2)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            critical_curve_tangential_from_magnification = critical_curve_via_magnification_from_tracer_and_grid(
                tracer=tracer, grid=grid
            )[
                0
            ]

            critical_curve_tangential_from_lambda_t = tracer.critical_curves_from_grid(
                grid=grid
            )[0]

            assert critical_curve_tangential_from_lambda_t == pytest.approx(
                critical_curve_tangential_from_magnification, 1e-4
            )

        def test__compare_radial_critical_curves_from_magnification_and_lamda_t__reg_grid_two_component_galaxy(
                self
        ):
            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.1, 0.1), einstein_radius=2.0
                ),
            )

            g2 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            critical_curve_radial_from_magnification = critical_curve_via_magnification_from_tracer_and_grid(
                tracer=tracer, grid=grid
            )[
                1
            ]

            critical_curve_radial_from_lambda_t = tracer.critical_curves_from_grid(
                grid=grid
            )[1]

            assert sum(critical_curve_radial_from_lambda_t) == pytest.approx(
                sum(critical_curve_radial_from_magnification), 1e-2
            )

            grid = al.grid.uniform(shape_2d=(100, 100), pixel_scales=0.05, sub_size=2)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            critical_curve_radial_from_magnification = critical_curve_via_magnification_from_tracer_and_grid(
                tracer=tracer, grid=grid
            )[
                1
            ]

            critical_curve_radial_from_lambda_t = tracer.critical_curves_from_grid(
                grid=grid
            )[1]

            assert sum(critical_curve_radial_from_lambda_t) == pytest.approx(
                sum(critical_curve_radial_from_magnification), 1e-2
            )

        def test__compare_tangential_caustic_from_magnification_and_lambda_t__two_component_galaxy(
                self
        ):
            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.25, sub_size=1)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.1, 0.1), einstein_radius=2.0
                ),
            )

            g2 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            caustic_tangential_from_magnification = caustics_via_magnification_from_tracer_and_grid(
                tracer=tracer, grid=grid
            )[
                0
            ]

            caustic_tangential_from_lambda_t = tracer.caustics_from_grid(grid=grid)[0]

            assert caustic_tangential_from_lambda_t == pytest.approx(
                caustic_tangential_from_magnification, 5e-1
            )

            grid = al.grid.uniform(shape_2d=(20, 20), pixel_scales=0.5, sub_size=2)

            caustic_tangential_from_magnification = caustics_via_magnification_from_tracer_and_grid(
                tracer=tracer, grid=grid
            )[
                0
            ]

            caustic_tangential_from_lambda_t = tracer.caustics_from_grid(grid=grid)[0]

            assert caustic_tangential_from_lambda_t == pytest.approx(
                caustic_tangential_from_magnification, 5e-1
            )

        def test__compare_radial_caustic_from_magnification_and_lambda_t__two_component_galaxy(
                self
        ):
            grid = al.grid.uniform(shape_2d=(60, 60), pixel_scales=0.5, sub_size=2)

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.EllipticalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.4, axis_ratio=0.7, phi=40.0
                ),
            )

            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(1.0, 1.0), einstein_radius=2.0
                ),
            )

            g2 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            caustic_radial_from_magnification = caustics_via_magnification_from_tracer_and_grid(
                tracer=tracer, grid=grid
            )[
                1
            ]

            caustic_radial_from_lambda_t = tracer.caustics_from_grid(grid=grid)[1]

            assert sum(caustic_radial_from_lambda_t) == pytest.approx(
                sum(caustic_radial_from_magnification), 1e-2
            )

    class TestGridAtRedshift:
        def test__lens_z05_source_z01_redshifts__match_planes_redshifts__gives_same_grids(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )
            g1 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=0.5
            )

            assert (grid_at_redshift == sub_grid_7x7).all()

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=1.0
            )

            source_plane_grid = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )[1]

            assert (grid_at_redshift == source_plane_grid).all()

        def test__same_as_above_but_for_multi_tracing(self, sub_grid_7x7):
            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )
            g1 = al.galaxy(
                redshift=0.75,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=2.0
                ),
            )
            g2 = al.galaxy(
                redshift=1.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=3.0
                ),
            )
            g3 = al.galaxy(
                redshift=1.0,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=4.0
                ),
            )
            g4 = al.galaxy(redshift=2.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2, g3, g4])

            traced_grids_of_planes = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=0.5
            )

            assert grid_at_redshift == pytest.approx(traced_grids_of_planes[0], 1.0e-4)

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=0.75
            )

            assert grid_at_redshift == pytest.approx(traced_grids_of_planes[1], 1.0e-4)

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=1.0
            )

            assert grid_at_redshift == pytest.approx(traced_grids_of_planes[2], 1.0e-4)

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=1.5
            )

            assert grid_at_redshift == pytest.approx(traced_grids_of_planes[3], 1.0e-4)

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=2.0
            )

            assert grid_at_redshift == pytest.approx(traced_grids_of_planes[4], 1.0e-4)

        def test__input_redshift_between_two_planes__two_planes_between_earth_and_input_redshift(
            self, sub_grid_7x7
        ):

            sub_grid_7x7[0] = np.array([[1.0, -1.0]])
            sub_grid_7x7[1] = np.array([[1.0, 0.0]])

            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )
            g1 = al.galaxy(
                redshift=0.75,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=2.0
                ),
            )
            g2 = al.galaxy(redshift=2.0)

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2])

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7, redshift=1.9
            )

            assert grid_at_redshift[0][0] == pytest.approx(-1.06587, 1.0e-1)
            assert grid_at_redshift[0][1] == pytest.approx(1.06587, 1.0e-1)
            assert grid_at_redshift[1][0] == pytest.approx(-1.921583, 1.0e-1)
            assert grid_at_redshift[1][1] == pytest.approx(0.0, 1.0e-1)

        def test__input_redshift_before_first_plane__returns_image_plane(
            self, sub_grid_7x7
        ):
            g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=1.0
                ),
            )
            g1 = al.galaxy(
                redshift=0.75,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=2.0
                ),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            grid_at_redshift = tracer.grid_at_redshift_from_grid_and_redshift(
                grid=sub_grid_7x7.geometry.unmasked_grid, redshift=0.3
            )

            assert (grid_at_redshift == sub_grid_7x7.geometry.unmasked_grid).all()

    class TestEinsteinRadiusAndMass:
        def test__x2_galaxies__values_are_sum_of_each_galaxy(self, sub_grid_7x7):

            g0 = al.galaxy(
                redshift=1.0, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0, mass=al.mp.SphericalIsothermal(einstein_radius=2.0)
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, al.galaxy(redshift=2.0)], cosmology=cosmo.Planck15
            )

            g0_einstein_radius = g0.einstein_radius_in_units(unit_length="arcsec")
            g1_einstein_radius = g1.einstein_radius_in_units(unit_length="arcsec")

            assert (
                tracer.einstein_radius_of_plane_in_units(i=0, unit_length="arcsec")
                == g0_einstein_radius + g1_einstein_radius
            )
            assert (
                tracer.einstein_radius_of_plane_in_units(i=1, unit_length="arcsec")
                is None
            )

            # g0_mass = g0.einstein_mass_in_units(unit_mass='angular')
            # g1_mass = g1.einstein_mass_in_units(unit_mass='angular')
            # assert tracer.einstein_mass_of_plane_in_units(i=0, unit_mass='angular') == g0_mass + g1_mass
            # assert tracer.einstein_mass_of_plane_in_units(i=1, unit_mass='angular') is None

            g0_einstein_radius = g0.einstein_radius_in_units(unit_length="kpc")
            g1_einstein_radius = g1.einstein_radius_in_units(unit_length="kpc")
            assert (
                tracer.einstein_radius_of_plane_in_units(i=0, unit_length="kpc")
                == g0_einstein_radius + g1_einstein_radius
            )
            assert (
                tracer.einstein_radius_of_plane_in_units(i=1, unit_length="kpc") is None
            )

            g0_mass = g0.einstein_mass_in_units(
                unit_mass="solMass", redshift_source=2.0
            )
            g1_mass = g1.einstein_mass_in_units(
                unit_mass="solMass", redshift_source=2.0
            )
            assert (
                tracer.einstein_mass_between_planes_in_units(
                    i=0, j=1, unit_mass="solMass"
                )
                == g0_mass + g1_mass
            )
            assert (
                tracer.einstein_mass_between_planes_in_units(
                    i=1, j=1, unit_mass="solMass"
                )
                is None
            )

        def test__same_as_above__include_shear__does_not_impact_calculations(
            self, sub_grid_7x7
        ):

            g0 = al.galaxy(
                redshift=1.0, mass=al.mp.SphericalIsothermal(einstein_radius=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0,
                mass=al.mp.SphericalIsothermal(einstein_radius=2.0),
                shear=al.mp.ExternalShear(),
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g0, g1, al.galaxy(redshift=2.0)], cosmology=cosmo.Planck15
            )

            g0_einstein_radius = g0.einstein_radius_in_units(unit_length="arcsec")
            g1_einstein_radius = g1.einstein_radius_in_units(unit_length="arcsec")

            assert (
                tracer.einstein_radius_of_plane_in_units(i=0, unit_length="arcsec")
                == g0_einstein_radius + g1_einstein_radius
            )

            assert (
                tracer.einstein_radius_of_plane_in_units(i=1, unit_length="arcsec")
                is None
            )

            # g0_mass = g0.einstein_mass_in_units(unit_mass='angular')
            # g1_mass = g1.einstein_mass_in_units(unit_mass='angular')
            # assert tracer.einstein_mass_of_plane_in_units(i=0, unit_mass='angular') == g0_mass + g1_mass
            # assert tracer.einstein_mass_of_plane_in_units(i=1, unit_mass='angular') is None

            g0_einstein_radius = g0.einstein_radius_in_units(unit_length="kpc")
            g1_einstein_radius = g1.einstein_radius_in_units(unit_length="kpc")
            assert (
                tracer.einstein_radius_of_plane_in_units(i=0, unit_length="kpc")
                == g0_einstein_radius + g1_einstein_radius
            )

            assert (
                tracer.einstein_radius_of_plane_in_units(i=1, unit_length="kpc") is None
            )

            g0_mass = g0.einstein_mass_in_units(
                unit_mass="solMass", redshift_source=2.0
            )
            g1_mass = g1.einstein_mass_in_units(
                unit_mass="solMass", redshift_source=2.0
            )
            assert (
                tracer.einstein_mass_between_planes_in_units(
                    i=0, j=1, unit_mass="solMass"
                )
                == g0_mass + g1_mass
            )
            assert (
                tracer.einstein_mass_between_planes_in_units(
                    i=1, j=1, unit_mass="solMass"
                )
                is None
            )


class TestAbstractTracerData(object):
    class TestBlurredProfileImages:
        def test__blurred_image_from_grid_and_psf(
            self, sub_grid_7x7, blurring_grid_7x7, psf_3x3
        ):

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            plane_0 = al.plane(redshift=0.5, galaxies=[g0])
            plane_1 = al.plane(redshift=1.0, galaxies=[g1])

            blurred_image_0 = plane_0.blurred_profile_image_from_grid_and_psf(
                grid=sub_grid_7x7, psf=psf_3x3, blurring_grid=blurring_grid_7x7
            )

            source_grid_7x7 = plane_0.traced_grid_from_grid(grid=sub_grid_7x7)
            source_blurring_grid_7x7 = plane_0.traced_grid_from_grid(
                grid=blurring_grid_7x7
            )

            blurred_image_1 = plane_1.blurred_profile_image_from_grid_and_psf(
                grid=source_grid_7x7,
                psf=psf_3x3,
                blurring_grid=source_blurring_grid_7x7,
            )

            tracer = al.Tracer(planes=[plane_0, plane_1], cosmology=cosmo.Planck15)

            blurred_image = tracer.blurred_profile_image_from_grid_and_psf(
                grid=sub_grid_7x7, psf=psf_3x3, blurring_grid=blurring_grid_7x7
            )

            assert blurred_image.in_1d == pytest.approx(
                blurred_image_0.in_1d + blurred_image_1.in_1d, 1.0e-4
            )

            assert blurred_image.in_2d == pytest.approx(
                blurred_image_0.in_2d + blurred_image_1.in_2d, 1.0e-4
            )

        def test__blurred_images_of_planes_from_grid_and_psf(
            self, sub_grid_7x7, blurring_grid_7x7, psf_3x3
        ):

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            plane_0 = al.plane(redshift=0.5, galaxies=[g0])
            plane_1 = al.plane(redshift=1.0, galaxies=[g1])

            blurred_image_0 = plane_0.blurred_profile_image_from_grid_and_psf(
                grid=sub_grid_7x7, psf=psf_3x3, blurring_grid=blurring_grid_7x7
            )

            source_grid_7x7 = plane_0.traced_grid_from_grid(grid=sub_grid_7x7)
            source_blurring_grid_7x7 = plane_0.traced_grid_from_grid(
                grid=blurring_grid_7x7
            )

            blurred_image_1 = plane_1.blurred_profile_image_from_grid_and_psf(
                grid=source_grid_7x7,
                psf=psf_3x3,
                blurring_grid=source_blurring_grid_7x7,
            )

            tracer = al.Tracer(planes=[plane_0, plane_1], cosmology=cosmo.Planck15)

            blurred_images = tracer.blurred_profile_images_of_planes_from_grid_and_psf(
                grid=sub_grid_7x7, psf=psf_3x3, blurring_grid=blurring_grid_7x7
            )

            assert (blurred_images[0].in_1d == blurred_image_0.in_1d).all()
            assert (blurred_images[1].in_1d == blurred_image_1.in_1d).all()

            assert (blurred_images[0].in_2d == blurred_image_0.in_2d).all()
            assert (blurred_images[1].in_2d == blurred_image_1.in_2d).all()

        def test__blurred_image_from_grid_and_convolver(
            self, sub_grid_7x7, blurring_grid_7x7, convolver_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            plane_0 = al.plane(redshift=0.5, galaxies=[g0])
            plane_1 = al.plane(redshift=1.0, galaxies=[g1])

            blurred_image_0 = plane_0.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            source_grid_7x7 = plane_0.traced_grid_from_grid(grid=sub_grid_7x7)
            source_blurring_grid_7x7 = plane_0.traced_grid_from_grid(
                grid=blurring_grid_7x7
            )

            blurred_image_1 = plane_1.blurred_profile_image_from_grid_and_convolver(
                grid=source_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=source_blurring_grid_7x7,
            )

            tracer = al.Tracer(planes=[plane_0, plane_1], cosmology=cosmo.Planck15)

            blurred_image = tracer.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            assert blurred_image.in_1d == pytest.approx(
                blurred_image_0.in_1d + blurred_image_1.in_1d, 1.0e-4
            )

            assert blurred_image.in_2d == pytest.approx(
                blurred_image_0.in_2d + blurred_image_1.in_2d, 1.0e-4
            )

        def test__blurred_images_of_planes_from_grid_and_convolver(
            self, sub_grid_7x7, blurring_grid_7x7, convolver_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            plane_0 = al.plane(redshift=0.5, galaxies=[g0])
            plane_1 = al.plane(redshift=1.0, galaxies=[g1])

            blurred_image_0 = plane_0.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            source_grid_7x7 = plane_0.traced_grid_from_grid(grid=sub_grid_7x7)
            source_blurring_grid_7x7 = plane_0.traced_grid_from_grid(
                grid=blurring_grid_7x7
            )

            blurred_image_1 = plane_1.blurred_profile_image_from_grid_and_convolver(
                grid=source_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=source_blurring_grid_7x7,
            )

            tracer = al.Tracer(planes=[plane_0, plane_1], cosmology=cosmo.Planck15)

            blurred_images = tracer.blurred_profile_images_of_planes_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            assert (blurred_images[0].in_1d == blurred_image_0.in_1d).all()
            assert (blurred_images[1].in_1d == blurred_image_1.in_1d).all()

            assert (blurred_images[0].in_2d == blurred_image_0.in_2d).all()
            assert (blurred_images[1].in_2d == blurred_image_1.in_2d).all()

        def test__galaxy_blurred_image_dict_from_grid_and_convolver(
            self, sub_grid_7x7, blurring_grid_7x7, convolver_7x7
        ):

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
                light_profile=al.lp.EllipticalSersic(intensity=2.0),
            )

            g2 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=3.0)
            )

            g3 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=5.0)
            )

            g0_blurred_image = g0.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            g1_blurred_image = g1.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            g2_blurred_image = g2.blurred_profile_image_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            g1_deflections = g1.deflections_from_grid(grid=sub_grid_7x7)

            source_grid_7x7 = sub_grid_7x7 - g1_deflections

            g1_blurring_deflections = g1.deflections_from_grid(grid=blurring_grid_7x7)

            source_blurring_grid_7x7 = blurring_grid_7x7 - g1_blurring_deflections

            g3_blurred_image = g3.blurred_profile_image_from_grid_and_convolver(
                grid=source_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=source_blurring_grid_7x7,
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g3, g1, g0, g2], cosmology=cosmo.Planck15
            )

            blurred_image_dict = tracer.galaxy_blurred_profile_image_dict_from_grid_and_convolver(
                grid=sub_grid_7x7,
                convolver=convolver_7x7,
                blurring_grid=blurring_grid_7x7,
            )

            assert (blurred_image_dict[g0].in_1d == g0_blurred_image.in_1d).all()
            assert (blurred_image_dict[g1].in_1d == g1_blurred_image.in_1d).all()
            assert (blurred_image_dict[g2].in_1d == g2_blurred_image.in_1d).all()
            assert (blurred_image_dict[g3].in_1d == g3_blurred_image.in_1d).all()

    class TestUnmaskedBlurredProfileImages:
        def test__unmasked_images_of_tracer_planes_and_galaxies(self):

            psf = al.kernel.manual_2d(
                array=(np.array([[0.0, 3.0, 0.0], [0.0, 1.0, 2.0], [0.0, 0.0, 0.0]])),
                pixel_scales=1.0,
            )

            mask = al.mask.manual(
                mask_2d=np.array(
                    [[True, True, True], [True, False, True], [True, True, True]]
                ),
                pixel_scales=1.0,
                sub_size=1,
            )

            grid = al.masked.grid.from_mask(mask=mask)

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=0.1)
            )
            g1 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=0.2)
            )
            g2 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.3)
            )
            g3 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=0.4)
            )

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1, g2, g3])

            padded_grid = grid.padded_grid_from_kernel_shape(kernel_shape=psf.shape_2d)

            traced_padded_grids = tracer.traced_grids_of_planes_from_grid(
                grid=padded_grid
            )

            manual_blurred_image_0 = tracer.image_plane.profile_images_of_galaxies_from_grid(
                grid=traced_padded_grids[0]
            )[
                0
            ]
            manual_blurred_image_0 = psf.convolved_array_from_array(
                array=manual_blurred_image_0
            )

            manual_blurred_image_1 = tracer.image_plane.profile_images_of_galaxies_from_grid(
                grid=traced_padded_grids[0]
            )[
                1
            ]
            manual_blurred_image_1 = psf.convolved_array_from_array(
                array=manual_blurred_image_1
            )

            manual_blurred_image_2 = tracer.source_plane.profile_images_of_galaxies_from_grid(
                grid=traced_padded_grids[1]
            )[
                0
            ]
            manual_blurred_image_2 = psf.convolved_array_from_array(
                array=manual_blurred_image_2
            )

            manual_blurred_image_3 = tracer.source_plane.profile_images_of_galaxies_from_grid(
                grid=traced_padded_grids[1]
            )[
                1
            ]
            manual_blurred_image_3 = psf.convolved_array_from_array(
                array=manual_blurred_image_3
            )

            unmasked_blurred_image = tracer.unmasked_blurred_profile_image_from_grid_and_psf(
                grid=grid, psf=psf
            )

            assert unmasked_blurred_image.in_2d == pytest.approx(
                manual_blurred_image_0.in_2d_binned[1:4, 1:4]
                + manual_blurred_image_1.in_2d_binned[1:4, 1:4]
                + manual_blurred_image_2.in_2d_binned[1:4, 1:4]
                + manual_blurred_image_3.in_2d_binned[1:4, 1:4],
                1.0e-4,
            )

            unmasked_blurred_image_of_planes = tracer.unmasked_blurred_profile_image_of_planes_from_grid_and_psf(
                grid=grid, psf=psf
            )

            assert unmasked_blurred_image_of_planes[0].in_2d == pytest.approx(
                manual_blurred_image_0.in_2d_binned[1:4, 1:4]
                + manual_blurred_image_1.in_2d_binned[1:4, 1:4],
                1.0e-4,
            )
            assert unmasked_blurred_image_of_planes[1].in_2d == pytest.approx(
                manual_blurred_image_2.in_2d_binned[1:4, 1:4]
                + manual_blurred_image_3.in_2d_binned[1:4, 1:4],
                1.0e-4,
            )

            unmasked_blurred_image_of_planes_and_galaxies = tracer.unmasked_blurred_profile_image_of_planes_and_galaxies_from_grid_and_psf(
                grid=grid, psf=psf
            )

            assert (
                unmasked_blurred_image_of_planes_and_galaxies[0][0].in_2d
                == manual_blurred_image_0.in_2d_binned[1:4, 1:4]
            ).all()
            assert (
                unmasked_blurred_image_of_planes_and_galaxies[0][1].in_2d
                == manual_blurred_image_1.in_2d_binned[1:4, 1:4]
            ).all()
            assert (
                unmasked_blurred_image_of_planes_and_galaxies[1][0].in_2d
                == manual_blurred_image_2.in_2d_binned[1:4, 1:4]
            ).all()
            assert (
                unmasked_blurred_image_of_planes_and_galaxies[1][1].in_2d
                == manual_blurred_image_3.in_2d_binned[1:4, 1:4]
            ).all()

    class TestVisibilities:
        def test__visibilities_from_grid_and_transformer(
            self, sub_grid_7x7, transformer_7x7_7
        ):
            g0 = al.galaxy(
                redshift=0.5,
                light_profile=al.lp.EllipticalSersic(intensity=1.0),
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            g0_image_1d = g0.profile_image_from_grid(grid=sub_grid_7x7)

            deflections = g0.deflections_from_grid(grid=sub_grid_7x7)

            source_grid_7x7 = sub_grid_7x7 - deflections

            g1_image_1d = g1.profile_image_from_grid(grid=source_grid_7x7)

            visibilities = transformer_7x7_7.visibilities_from_image(
                image=g0_image_1d + g1_image_1d
            )

            tracer = al.Tracer.from_galaxies(galaxies=[g0, g1])

            tracer_visibilities = tracer.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert visibilities == pytest.approx(tracer_visibilities, 1.0e-4)

        def test__visibilities_of_planes_from_grid_and_transformer(
            self, sub_grid_7x7, transformer_7x7_7
        ):

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=2.0)
            )

            plane_0 = al.plane(redshift=0.5, galaxies=[g0])
            plane_1 = al.plane(redshift=0.5, galaxies=[g1])
            plane_2 = al.plane(redshift=1.0, galaxies=[al.galaxy(redshift=1.0)])

            visibilities_0 = plane_0.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            visibilities_1 = plane_1.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            tracer = al.Tracer(
                planes=[plane_0, plane_1, plane_2], cosmology=cosmo.Planck15
            )

            visibilities = tracer.profile_visibilities_of_planes_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert (visibilities[0] == visibilities_0).all()
            assert (visibilities[1] == visibilities_1).all()

        def test__galaxy_visibilities_dict_from_grid_and_transformer(
            self, sub_grid_7x7, transformer_7x7_7
        ):

            g0 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=1.0)
            )
            g1 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
                light_profile=al.lp.EllipticalSersic(intensity=2.0),
            )

            g2 = al.galaxy(
                redshift=0.5, light_profile=al.lp.EllipticalSersic(intensity=3.0)
            )

            g3 = al.galaxy(
                redshift=1.0, light_profile=al.lp.EllipticalSersic(intensity=5.0)
            )

            g0_visibilities = g0.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            g1_visibilities = g1.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            g2_visibilities = g2.profile_visibilities_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            g1_deflections = g1.deflections_from_grid(grid=sub_grid_7x7)

            source_grid_7x7 = sub_grid_7x7 - g1_deflections

            g3_visibilities = g3.profile_visibilities_from_grid_and_transformer(
                grid=source_grid_7x7, transformer=transformer_7x7_7
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[g3, g1, g0, g2], cosmology=cosmo.Planck15
            )

            visibilities_dict = tracer.galaxy_profile_visibilities_dict_from_grid_and_transformer(
                grid=sub_grid_7x7, transformer=transformer_7x7_7
            )

            assert (visibilities_dict[g0] == g0_visibilities).all()
            assert (visibilities_dict[g1] == g1_visibilities).all()
            assert (visibilities_dict[g2] == g2_visibilities).all()
            assert (visibilities_dict[g3] == g3_visibilities).all()

    class TestGridIrregularsOfPlanes:
        def test__x2_planes__traced_grid_setup_correctly(self, sub_grid_7x7):
            galaxy_pix = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(
                    value=1, grid=np.array([[1.0, 1.0]])
                ),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_pix])

            pixelization_grids = tracer.sparse_image_plane_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            assert pixelization_grids[0] == None
            assert (pixelization_grids[1] == np.array([[1.0, 1.0]])).all()

        def test__multi_plane__traced_grid_setup_correctly(self, sub_grid_7x7):

            galaxy_pix0 = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(
                    value=1, grid=np.array([[1.0, 1.0]])
                ),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )

            galaxy_pix1 = al.galaxy(
                redshift=2.0,
                pixelization=mock_inv.MockPixelization(
                    value=1, grid=np.array([[2.0, 2.0]])
                ),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )

            galaxy_no_pix0 = al.galaxy(redshift=0.25)
            galaxy_no_pix1 = al.galaxy(redshift=0.5)
            galaxy_no_pix2 = al.galaxy(redshift=1.5)

            tracer = al.Tracer.from_galaxies(
                galaxies=[
                    galaxy_pix0,
                    galaxy_pix1,
                    galaxy_no_pix0,
                    galaxy_no_pix1,
                    galaxy_no_pix2,
                ]
            )

            pixelization_grids = tracer.sparse_image_plane_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            assert pixelization_grids[0] == None
            assert pixelization_grids[1] == None
            assert (pixelization_grids[2] == np.array([[1.0, 1.0]])).all()
            assert pixelization_grids[3] == None
            assert (pixelization_grids[4] == np.array([[2.0, 2.0]])).all()

    class TestTracedGridIrregularsOfPlanes:
        def test__x2_planes__no_mass_profiles__traced_grid_setup_correctly(
            self, sub_grid_7x7
        ):

            galaxy_pix = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(
                    value=1, grid=al.grid.manual_2d([[[1.0, 0.0]]])
                ),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_pix])

            traced_pixelization_grids = tracer.traced_sparse_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            assert traced_pixelization_grids[0] == None
            assert (traced_pixelization_grids[1] == np.array([[1.0, 0.0]])).all()

        def test__x2_planes__include_mass_profile__traced_grid_setup_correctly(
            self, sub_grid_7x7
        ):

            galaxy_no_pix = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=0.5
                ),
            )

            galaxy_pix = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(
                    value=1, grid=al.grid.manual_2d([[[1.0, 0.0]]])
                ),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_pix])

            traced_pixelization_grids = tracer.traced_sparse_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            assert traced_pixelization_grids[0] == None
            assert traced_pixelization_grids[1] == pytest.approx(
                np.array([[1.0 - 0.5, 0.0]]), 1.0e-4
            )

        def test__multi_plane__traced_grid_setup_correctly(self, sub_grid_7x7):

            galaxy_pix0 = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(
                    value=1, grid=al.grid.manual_2d([[[1.0, 1.0]]])
                ),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )

            galaxy_pix1 = al.galaxy(
                redshift=2.0,
                pixelization=mock_inv.MockPixelization(
                    value=1, grid=al.grid.manual_2d([[[2.0, 2.0]]])
                ),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )

            galaxy_no_pix0 = al.galaxy(
                redshift=0.25,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=0.5
                ),
            )
            galaxy_no_pix1 = al.galaxy(redshift=0.5)
            galaxy_no_pix2 = al.galaxy(redshift=1.5)

            tracer = al.Tracer.from_galaxies(
                galaxies=[
                    galaxy_pix0,
                    galaxy_pix1,
                    galaxy_no_pix0,
                    galaxy_no_pix1,
                    galaxy_no_pix2,
                ]
            )

            traced_pixelization_grids = tracer.traced_sparse_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            traced_grid_pix0 = tracer.traced_grids_of_planes_from_grid(
                grid=al.grid.manual_2d([[[1.0, 1.0]]])
            )[2]
            traced_grid_pix1 = tracer.traced_grids_of_planes_from_grid(
                grid=al.grid.manual_2d([[[2.0, 2.0]]])
            )[4]

            assert traced_pixelization_grids[0] == None
            assert traced_pixelization_grids[1] == None
            assert (traced_pixelization_grids[2] == traced_grid_pix0).all()
            assert traced_pixelization_grids[3] == None
            assert (traced_pixelization_grids[4] == traced_grid_pix1).all()

        def test__x2_planes__no_mass_profiles__use_real_pixelization__doesnt_crash_due_to_auto_arrays(
            self, sub_grid_7x7
        ):

            galaxy_pix = al.galaxy(
                redshift=1.0,
                pixelization=al.pix.VoronoiMagnification(shape=(3, 3)),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_pix])

            traced_pixelization_grids = tracer.traced_sparse_grids_of_planes_from_grid(
                grid=sub_grid_7x7
            )

            assert traced_pixelization_grids[0] is None
            assert traced_pixelization_grids[1] is not None

    class TestMappersOfPlanes:
        def test__no_galaxy_has_pixelization__returns_list_of_nones(self, sub_grid_7x7):

            galaxy_no_pix = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_no_pix])

            mappers_of_planes = tracer.mappers_of_planes_from_grid(grid=sub_grid_7x7)
            assert mappers_of_planes == [None]

        def test__source_galaxy_has_pixelization__returns_mapper_in_list(
            self, sub_grid_7x7
        ):
            galaxy_pix = al.galaxy(
                redshift=1.0,
                pixelization=mock_inv.MockPixelization(value=1),
                regularization=mock_inv.MockRegularization(matrix_shape=(1, 1)),
            )
            galaxy_no_pix = al.galaxy(redshift=0.5)

            tracer = al.Tracer.from_galaxies(galaxies=[galaxy_no_pix, galaxy_pix])

            mapper_of_planes = tracer.mappers_of_planes_from_grid(grid=sub_grid_7x7)

            assert mapper_of_planes == [None, 1]

        def test__multiplane__correct_galaxy_planes_galaxies_have_pixelization__returns_both_mappers(
            self, sub_grid_7x7
        ):

            galaxy_no_pix0 = al.galaxy(
                redshift=0.25,
                mass_profile=al.mp.SphericalIsothermal(
                    centre=(0.0, 0.0), einstein_radius=0.5
                ),
            )
            galaxy_no_pix1 = al.galaxy(redshift=0.5)
            galaxy_no_pix2 = al.galaxy(redshift=1.5)

            galaxy_pix_0 = al.galaxy(
                redshift=0.75,
                pixelization=mock_inv.MockPixelization(value=1),
                regularization=mock_inv.MockRegularization(matrix_shape=(3, 3)),
            )
            galaxy_pix_1 = al.galaxy(
                redshift=2.0,
                pixelization=mock_inv.MockPixelization(value=2),
                regularization=mock_inv.MockRegularization(matrix_shape=(4, 4)),
            )

            tracer = al.Tracer.from_galaxies(
                galaxies=[
                    galaxy_no_pix0,
                    galaxy_no_pix1,
                    galaxy_no_pix2,
                    galaxy_pix_0,
                    galaxy_pix_1,
                ]
            )

            mappers_of_planes = tracer.mappers_of_planes_from_grid(grid=sub_grid_7x7)

            assert mappers_of_planes == [None, None, 1, None, 2]

    class TestInversion:
        def test__x1_inversion_in_tracer__performs_inversion_correctly(
            self, sub_grid_7x7, masked_imaging_7x7
        ):

            pix = al.pix.Rectangular(shape=(3, 3))
            reg = al.reg.Constant(coefficient=0.0)

            g0 = al.galaxy(redshift=0.5, pixelization=pix, regularization=reg)

            tracer = al.Tracer.from_galaxies(galaxies=[al.galaxy(redshift=0.5), g0])

            inversion = tracer.inversion_imaging_from_grid_and_data(
                grid=sub_grid_7x7,
                image=masked_imaging_7x7.image,
                noise_map=masked_imaging_7x7.noise_map,
                convolver=masked_imaging_7x7.convolver,
                inversion_uses_border=False,
            )

            assert inversion.mapped_reconstructed_image == pytest.approx(
                masked_imaging_7x7.image, 1.0e-2
            )

    class TestHyperNoiseMap:
        def test__hyper_noise_maps_of_planes(self, sub_grid_7x7):

            noise_map_1d = al.array.manual_2d([[5.0, 3.0, 1.0]])

            hyper_model_image = al.array.manual_2d([[2.0, 4.0, 10.0]])
            hyper_galaxy_image = al.array.manual_2d([[1.0, 5.0, 8.0]])

            hyper_galaxy_0 = al.HyperGalaxy(contribution_factor=5.0)
            hyper_galaxy_1 = al.HyperGalaxy(contribution_factor=10.0)

            galaxy_0 = al.galaxy(
                redshift=0.5,
                hyper_galaxy=hyper_galaxy_0,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
                hyper_minimum_value=0.0,
            )

            galaxy_1 = al.galaxy(
                redshift=1.0,
                hyper_galaxy=hyper_galaxy_1,
                hyper_model_image=hyper_model_image,
                hyper_galaxy_image=hyper_galaxy_image,
                hyper_minimum_value=0.0,
            )

            plane_0 = al.plane(redshift=0.5, galaxies=[galaxy_0])
            plane_1 = al.plane(redshift=0.5, galaxies=[galaxy_1])
            plane_2 = al.plane(redshift=1.0, galaxies=[al.galaxy(redshift=0.5)])

            hyper_noise_map_0 = plane_0.hyper_noise_map_from_noise_map(
                noise_map=noise_map_1d
            )
            hyper_noise_map_1 = plane_1.hyper_noise_map_from_noise_map(
                noise_map=noise_map_1d
            )

            tracer = al.Tracer(
                planes=[plane_0, plane_1, plane_2], cosmology=cosmo.Planck15
            )

            hyper_noise_maps = tracer.hyper_noise_maps_of_planes_from_noise_map(
                noise_map=noise_map_1d
            )

            assert (hyper_noise_maps[0].in_1d == hyper_noise_map_0).all()
            assert (hyper_noise_maps[1].in_1d == hyper_noise_map_1).all()
            assert hyper_noise_maps[2].in_1d == np.zeros(shape=(3, 1))

            hyper_noise_map = tracer.hyper_noise_map_from_noise_map(
                noise_map=noise_map_1d
            )

            assert (
                hyper_noise_map.in_1d == hyper_noise_map_0 + hyper_noise_map_1
            ).all()

            tracer = al.Tracer.from_galaxies(
                galaxies=[galaxy_0, galaxy_1], cosmology=cosmo.Planck15
            )

            hyper_noise_maps = tracer.hyper_noise_maps_of_planes_from_noise_map(
                noise_map=noise_map_1d
            )

            assert (hyper_noise_maps[0].in_1d == hyper_noise_map_0).all()
            assert (hyper_noise_maps[1].in_1d == hyper_noise_map_1).all()


class TestTracer(object):
    class TestTracedDeflectionsFromGrid:
        def test__x2_planes__no_galaxy__all_deflections_are_zeros(
            self, sub_grid_7x7_simple
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=1.0)]
            )

            traced_deflections_between_planes = tracer.deflections_between_planes_from_grid(
                grid=sub_grid_7x7_simple, plane_i=0, plane_j=0
            )

            assert traced_deflections_between_planes[0] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[1] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[2] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[3] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )

            traced_deflections_between_planes = tracer.deflections_between_planes_from_grid(
                grid=sub_grid_7x7_simple, plane_i=0, plane_j=1
            )

            assert traced_deflections_between_planes[0] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[1] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[2] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[3] == pytest.approx(
                np.array([0.0, 0.0]), 1e-3
            )

        def test__x2_planes__sis_lens__traced_deflection_are_correct(
            self, sub_grid_7x7_simple, gal_x1_mp
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[gal_x1_mp, al.galaxy(redshift=1.0)]
            )

            traced_deflections_between_planes = tracer.deflections_between_planes_from_grid(
                grid=sub_grid_7x7_simple, plane_i=0, plane_j=1
            )

            assert traced_deflections_between_planes[0] == pytest.approx(
                np.array([0.707, 0.707]), 1e-3
            )
            assert traced_deflections_between_planes[1] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[2] == pytest.approx(
                np.array([0.707, 0.707]), 1e-3
            )
            assert traced_deflections_between_planes[3] == pytest.approx(
                np.array([1.0, 0.0]), 1e-3
            )

        def test__same_as_above_but_x2_sis_lenses__deflections_double(
            self, sub_grid_7x7_simple, gal_x1_mp
        ):

            tracer = al.Tracer.from_galaxies(
                galaxies=[gal_x1_mp, gal_x1_mp, al.galaxy(redshift=1.0)]
            )

            traced_deflections_between_planes = tracer.deflections_between_planes_from_grid(
                grid=sub_grid_7x7_simple, plane_i=0, plane_j=1
            )

            assert traced_deflections_between_planes[0] == pytest.approx(
                np.array([2.0 * 0.707, 2.0 * 0.707]), 1e-3
            )
            assert traced_deflections_between_planes[1] == pytest.approx(
                np.array([2.0 * 1.0, 0.0]), 1e-3
            )
            assert traced_deflections_between_planes[2] == pytest.approx(
                np.array([2.0 * 0.707, 2.0 * 0.707]), 1e-3
            )
            assert traced_deflections_between_planes[3] == pytest.approx(
                np.array([2.0 * 1.0, 0.0]), 1e-3
            )

        # def test__multi_plane_x4_planes__traced_deflections_are_correct_including_cosmology_scaling__sis_mass_profile(
        #     self, sub_grid_7x7_simple
        # ):
        #
        #     g0 = al.galaxy(
        #         redshift=2.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        #     )
        #     g1 = al.galaxy(
        #         redshift=2.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        #     )
        #     g2 = al.galaxy(
        #         redshift=0.1, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        #     )
        #     g3 = al.galaxy(
        #         redshift=3.0,
        #     )
        #     g4 = al.galaxy(
        #         redshift=1.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        #     )
        #     g5 = al.galaxy(
        #         redshift=3.0,
        #     )
        #
        #     tracer = al.Tracer.from_galaxies(
        #         galaxies=[g0, g1, g2, g3, g4, g5],
        #         cosmology=cosmo.Planck15,
        #     )
        #
        #     deflections_between_planes = tracer.deflections_between_planes_from_grid(
        #         grid=sub_grid_7x7_simple, plane_i=0, plane_j=1)
        #
        #     # The scaling factors are as follows and were computed independently from the test_autoarray.
        #     beta_01 = 0.9348
        #     beta_02 = 0.9839601
        #     # Beta_03 = 1.0
        #     beta_12 = 0.7539734
        #     # Beta_13 = 1.0
        #     # Beta_23 = 1.0
        #
        #     val = np.sqrt(2) / 2.0
        #
        #     assert deflections_between_planes[0] == pytest.approx(
        #         np.arrays([val, val]), 1e-4
        #     )
        #     assert deflections_between_planes[1] == pytest.approx(
        #         np.arrays([1.0, 0.0]), 1e-4
        #     )
        #
        #     defl11 = g0.deflections_from_grid(
        #         grid=np.arrays([[(1.0 - beta_01 * val), (1.0 - beta_01 * val)]])
        #     )
        #     defl12 = g0.deflections_from_grid(
        #         grid=np.arrays([[(1.0 - beta_01 * 1.0), 0.0]])
        #     )

        # assert traced_deflections_of_planes[1][0] == pytest.approx(
        #     defl11[0], 1e-4
        # )
        # assert traced_deflections_of_planes[1][1] == pytest.approx(
        #     defl12[0], 1e-4
        # )

        # 2 Galaxies in this plane, so multiply by 2.0

        # defl21 = 2.0 * g0.deflections_from_grid(
        #     grid=np.arrays(
        #         [
        #             [
        #                 (1.0 - beta_02 * val - beta_12 * defl11[0, 0]),
        #                 (1.0 - beta_02 * val - beta_12 * defl11[0, 1]),
        #             ]
        #         ]
        #     )
        # )
        # defl22 = 2.0 * g0.deflections_from_grid(
        #     grid=np.arrays([[(1.0 - beta_02 * 1.0 - beta_12 * defl12[0, 0]), 0.0]])
        # )

        # assert deflections_between_planes[2][0] == pytest.approx(
        #     defl21[0], 1e-4
        # )
        # assert deflections_between_planes[2][1] == pytest.approx(
        #     defl22[0], 1e-4
        # )
        #
        # assert deflections_between_planes[3][0] == pytest.approx(
        #     np.arrays([0.0, 0.0]), 1e-3
        # )
        # assert deflections_between_planes[3][1] == pytest.approx(
        #     np.arrays([0.0, 0.0]), 1e-3
        # )

        # def test__grid_attributes_passed(self, sub_grid_7x7_simple):
        #     tracer = al.Tracer.from_galaxies(
        #         galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=0.5)],
        #     )
        #
        #     traced_deflections_of_planes = tracer.traced_deflections_of_planes_from_grid(
        #         grid=sub_grid_7x7_simple)
        #
        #     assert (
        #         traced_deflections_of_planes[0].mask == sub_grid_7x7_simple.sub.mask
        #     ).all()


class TestTacerFixedSlices(object):
    class TestCosmology:
        def test__4_planes_after_slicing(self, sub_grid_7x7):

            lens_g0 = al.galaxy(redshift=0.5)
            source_g0 = al.galaxy(redshift=2.0)
            los_g0 = al.galaxy(redshift=1.0)

            tracer = al.Tracer.sliced_tracer_from_lens_line_of_sight_and_source_galaxies(
                lens_galaxies=[lens_g0],
                line_of_sight_galaxies=[los_g0],
                source_galaxies=[source_g0],
                planes_between_lenses=[1, 1],
                cosmology=cosmo.Planck15,
            )

            assert (
                tracer.arcsec_per_kpc_proper_of_plane(i=0)
                == tracer.cosmology.arcsec_per_kpc_proper(z=0.25).value
            )
            assert (
                tracer.kpc_per_arcsec_proper_of_plane(i=0)
                == 1.0 / tracer.cosmology.arcsec_per_kpc_proper(z=0.25).value
            )

            assert (
                tracer.angular_diameter_distance_of_plane_to_earth_in_units(
                    i=0, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance(0.25).to("kpc").value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=0, j=0, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.25, 0.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=0, j=1, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.25, 0.5)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=0, j=2, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.25, 1.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=0, j=3, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.25, 2.0)
                .to("kpc")
                .value
            )

            assert (
                tracer.arcsec_per_kpc_proper_of_plane(i=1)
                == tracer.cosmology.arcsec_per_kpc_proper(z=0.5).value
            )
            assert (
                tracer.kpc_per_arcsec_proper_of_plane(i=1)
                == 1.0 / tracer.cosmology.arcsec_per_kpc_proper(z=0.5).value
            )

            assert (
                tracer.angular_diameter_distance_of_plane_to_earth_in_units(
                    i=1, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance(0.5).to("kpc").value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=1, j=0, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.5, 0.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=1, j=1, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.5, 0.5)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=1, j=2, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.5, 1.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=1, j=3, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(0.5, 2.0)
                .to("kpc")
                .value
            )

            assert (
                tracer.arcsec_per_kpc_proper_of_plane(i=2)
                == tracer.cosmology.arcsec_per_kpc_proper(z=1.25).value
            )
            assert (
                tracer.kpc_per_arcsec_proper_of_plane(i=2)
                == 1.0 / tracer.cosmology.arcsec_per_kpc_proper(z=1.25).value
            )

            assert (
                tracer.angular_diameter_distance_of_plane_to_earth_in_units(
                    i=2, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance(1.25).to("kpc").value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=2, j=0, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(1.25, 0.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=2, j=1, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(1.25, 0.5)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=2, j=2, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(1.25, 1.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=2, j=3, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(1.25, 2.0)
                .to("kpc")
                .value
            )

            assert (
                tracer.arcsec_per_kpc_proper_of_plane(i=3)
                == tracer.cosmology.arcsec_per_kpc_proper(z=2.0).value
            )
            assert (
                tracer.kpc_per_arcsec_proper_of_plane(i=3)
                == 1.0 / tracer.cosmology.arcsec_per_kpc_proper(z=2.0).value
            )

            assert (
                tracer.angular_diameter_distance_of_plane_to_earth_in_units(
                    i=3, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance(2.0).to("kpc").value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=3, j=0, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(2.0, 0.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=3, j=1, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(2.0, 0.5)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=3, j=2, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(2.0, 1.25)
                .to("kpc")
                .value
            )
            assert (
                tracer.angular_diameter_distance_between_planes_in_units(
                    i=3, j=3, unit_length="kpc"
                )
                == tracer.cosmology.angular_diameter_distance_z1z2(2.0, 2.0)
                .to("kpc")
                .value
            )

    class TestPlaneSetup:
        def test__6_galaxies__tracer_planes_are_correct(self, sub_grid_7x7):
            lens_g0 = al.galaxy(redshift=0.5)
            source_g0 = al.galaxy(redshift=2.0)
            los_g0 = al.galaxy(redshift=0.1)
            los_g1 = al.galaxy(redshift=0.2)
            los_g2 = al.galaxy(redshift=0.4)
            los_g3 = al.galaxy(redshift=0.6)

            tracer = al.Tracer.sliced_tracer_from_lens_line_of_sight_and_source_galaxies(
                lens_galaxies=[lens_g0],
                line_of_sight_galaxies=[los_g0, los_g1, los_g2, los_g3],
                source_galaxies=[source_g0],
                planes_between_lenses=[1, 1],
                cosmology=cosmo.Planck15,
            )

            # Plane redshifts are [0.25, 0.5, 1.25, 2.0]

            assert tracer.planes[0].galaxies == [los_g0, los_g1]
            assert tracer.planes[1].galaxies == [lens_g0, los_g2, los_g3]
            assert tracer.planes[2].galaxies == []
            assert tracer.planes[3].galaxies == [source_g0]

    class TestPlaneGrids:
        def test__4_planes__data_grid_and_deflections_stacks_are_correct__sis_mass_profile(
            self, sub_grid_7x7_simple
        ):

            lens_g0 = al.galaxy(
                redshift=0.5,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            source_g0 = al.galaxy(
                redshift=2.0,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            los_g0 = al.galaxy(
                redshift=0.1,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            los_g1 = al.galaxy(
                redshift=0.2,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            los_g2 = al.galaxy(
                redshift=0.4,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )
            los_g3 = al.galaxy(
                redshift=0.6,
                mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0),
            )

            tracer = al.Tracer.sliced_tracer_from_lens_line_of_sight_and_source_galaxies(
                lens_galaxies=[lens_g0],
                line_of_sight_galaxies=[los_g0, los_g1, los_g2, los_g3],
                source_galaxies=[source_g0],
                planes_between_lenses=[1, 1],
                cosmology=cosmo.Planck15,
            )

            traced_grids = tracer.traced_grids_of_planes_from_grid(
                grid=sub_grid_7x7_simple
            )

            # This test_autoarray is essentially the same as the TracerMulti test_autoarray, we just slightly change how many galaxies go
            # in each plane and therefore change the factor in front of val for different planes.

            # The scaling factors are as follows and were computed indepedently from the test_autoarray.
            beta_01 = 0.57874474423
            beta_02 = 0.91814281
            # Beta_03 = 1.0
            beta_12 = 0.8056827034
            # Beta_13 = 1.0
            # Beta_23 = 1.0

            val = np.sqrt(2) / 2.0

            assert traced_grids[0][0] == pytest.approx(np.array([1.0, 1.0]), 1e-4)
            assert traced_grids[0][1] == pytest.approx(np.array([1.0, 0.0]), 1e-4)

            assert traced_grids[1][0] == pytest.approx(
                np.array([(1.0 - beta_01 * 2.0 * val), (1.0 - beta_01 * 2.0 * val)]),
                1e-4,
            )
            assert traced_grids[1][1] == pytest.approx(
                np.array([(1.0 - beta_01 * 2.0), 0.0]), 1e-4
            )

            #  Galaxies in this plane, so multiply by 3

            defl11 = 3.0 * lens_g0.deflections_from_grid(
                grid=al.grid.manual_2d(
                    [[[(1.0 - beta_01 * 2.0 * val), (1.0 - beta_01 * 2.0 * val)]]]
                )
            )
            defl12 = 3.0 * lens_g0.deflections_from_grid(
                grid=al.grid.manual_2d([[[(1.0 - beta_01 * 2.0 * 1.0), 0.0]]])
            )

            assert traced_grids[2][0] == pytest.approx(
                np.array(
                    [
                        (1.0 - beta_02 * 2.0 * val - beta_12 * defl11[0, 0]),
                        (1.0 - beta_02 * 2.0 * val - beta_12 * defl11[0, 1]),
                    ]
                ),
                1e-4,
            )
            assert traced_grids[2][1] == pytest.approx(
                np.array([(1.0 - beta_02 * 2.0 - beta_12 * defl12[0, 0]), 0.0]), 1e-4
            )

            assert traced_grids[3][0] == pytest.approx(
                np.array([-2.5355, -2.5355]), 1e-4
            )
            assert traced_grids[3][1] == pytest.approx(np.array([2.0, 0.0]), 1e-4)


class TestTracerPositions(object):
    def test__x2_positions__no_galaxy__image_and_source_planes_setup__same_positions(
        self
    ):
        tracer = al.Tracer.from_galaxies(
            galaxies=[al.galaxy(redshift=0.5), al.galaxy(redshift=1.0)]
        )

        traced_positions_of_planes = tracer.traced_positions_of_planes_from_positions(
            positions=[al.grid_irregular.manual_1d(grid=[[1.0, 1.0], [-1.0, -1.0]])]
        )

        assert traced_positions_of_planes[0][0] == pytest.approx(
            np.array([[1.0, 1.0], [-1.0, -1.0]]), 1e-3
        )

        assert traced_positions_of_planes[1][0] == pytest.approx(
            np.array([[1.0, 1.0], [-1.0, -1.0]]), 1e-3
        )

    def test__x2_positions__sis_lens__positions_with_source_plane_deflected(
        self, gal_x1_mp
    ):
        tracer = al.Tracer.from_galaxies(galaxies=[gal_x1_mp, al.galaxy(redshift=1.0)])

        traced_positions_of_planes = tracer.traced_positions_of_planes_from_positions(
            positions=[al.grid_irregular.manual_1d([[1.0, 1.0], [-1.0, -1.0]])]
        )

        assert traced_positions_of_planes[0][0] == pytest.approx(
            np.array([[1.0, 1.0], [-1.0, -1.0]]), 1e-3
        )

        assert traced_positions_of_planes[1][0] == pytest.approx(
            np.array([[1.0 - 0.707, 1.0 - 0.707], [-1.0 + 0.707, -1.0 + 0.707]]), 1e-3
        )

    def test__same_as_above_but_2_sis_lenses__deflections_double(self, gal_x1_mp):
        tracer = al.Tracer.from_galaxies(
            galaxies=[gal_x1_mp, gal_x1_mp, al.galaxy(redshift=1.0)]
        )

        traced_positions_of_planes = tracer.traced_positions_of_planes_from_positions(
            positions=[al.grid_irregular.manual_1d([[1.0, 1.0], [-1.0, -1.0]])]
        )

        assert traced_positions_of_planes[0][0] == pytest.approx(
            np.array([[1.0, 1.0], [-1.0, -1.0]]), 1e-3
        )
        assert traced_positions_of_planes[1][0] == pytest.approx(
            np.array([[1.0 - 1.414, 1.0 - 1.414], [-1.0 + 1.414, -1.0 + 1.414]]), 1e-3
        )

    def test__multiple_sets_of_positions_in_different_arrays(self, gal_x1_mp):
        tracer = al.Tracer.from_galaxies(galaxies=[gal_x1_mp, al.galaxy(redshift=1.0)])

        traced_positions_of_planes = tracer.traced_positions_of_planes_from_positions(
            positions=[
                al.grid_irregular.manual_1d([[1.0, 1.0], [-1.0, -1.0]]),
                al.grid_irregular.manual_1d([[0.5, 0.5]]),
            ]
        )

        assert traced_positions_of_planes[0][0] == pytest.approx(
            np.array([[1.0, 1.0], [-1.0, -1.0]]), 1e-3
        )

        assert traced_positions_of_planes[1][0] == pytest.approx(
            np.array([[1.0 - 0.707, 1.0 - 0.707], [-1.0 + 0.707, -1.0 + 0.707]]), 1e-3
        )

        assert traced_positions_of_planes[0][1] == pytest.approx(
            np.array([[0.5, 0.5]]), 1e-3
        )

        assert traced_positions_of_planes[1][1] == pytest.approx(
            np.array([[0.5 - 0.707, 0.5 - 0.707]]), 1e-3
        )

    def test__4_planes__coordinate_grid_stack_and_deflections_are_correct__sis_mass_profile(
        self
    ):
        import math

        g0 = al.galaxy(
            redshift=2.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g1 = al.galaxy(
            redshift=2.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g2 = al.galaxy(
            redshift=0.1, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g3 = al.galaxy(
            redshift=3.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g4 = al.galaxy(
            redshift=1.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g5 = al.galaxy(
            redshift=3.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )

        tracer = al.Tracer.from_galaxies(
            galaxies=[g0, g1, g2, g3, g4, g5], cosmology=cosmo.Planck15
        )

        traced_positions_of_planes = tracer.traced_positions_of_planes_from_positions(
            positions=[al.grid_irregular.manual_1d([[1.0, 1.0]])]
        )

        # From unit test_autoarray below:
        # Beta_01 = 0.9348
        beta_02 = 0.9839601
        # Beta_03 = 1.0
        beta_12 = 0.7539734
        # Beta_13 = 1.0
        # Beta_23 = 1.0

        val = math.sqrt(2) / 2.0

        assert traced_positions_of_planes[0][0] == pytest.approx(
            np.array([[1.0, 1.0]]), 1e-4
        )

        assert traced_positions_of_planes[1][0] == pytest.approx(
            np.array([[(1.0 - 0.9348 * val), (1.0 - 0.9348 * val)]]), 1e-4
        )

        defl11 = g0.deflections_from_grid(
            grid=al.grid.manual_2d([[[(1.0 - 0.9348 * val), (1.0 - 0.9348 * val)]]])
        )

        assert traced_positions_of_planes[2][0] == pytest.approx(
            np.array(
                [
                    [
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 0]),
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 1]),
                    ]
                ]
            ),
            1e-4,
        )

        assert traced_positions_of_planes[3][0] == pytest.approx(
            np.array([[1.0, 1.0]]), 1e-4
        )

    def test__same_as_above_but_multiple_sets_of_positions(self):
        import math

        g0 = al.galaxy(
            redshift=2.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g1 = al.galaxy(
            redshift=2.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g2 = al.galaxy(
            redshift=0.1, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g3 = al.galaxy(
            redshift=3.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g4 = al.galaxy(
            redshift=1.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )
        g5 = al.galaxy(
            redshift=3.0, mass_profile=al.mp.SphericalIsothermal(einstein_radius=1.0)
        )

        tracer = al.Tracer.from_galaxies(
            galaxies=[g0, g1, g2, g3, g4, g5], cosmology=cosmo.Planck15
        )

        traced_positions_of_planes = tracer.traced_positions_of_planes_from_positions(
            positions=[
                al.grid_irregular.manual_1d([[1.0, 1.0]]),
                al.grid_irregular.manual_1d([[1.0, 1.0]]),
            ]
        )

        # From unit test_autoarray below:
        # Beta_01 = 0.9348
        beta_02 = 0.9839601
        # Beta_03 = 1.0
        beta_12 = 0.7539734
        # Beta_13 = 1.0
        # Beta_23 = 1.0

        val = math.sqrt(2) / 2.0

        assert traced_positions_of_planes[0][0] == pytest.approx(
            np.array([[1.0, 1.0]]), 1e-4
        )

        assert traced_positions_of_planes[1][0] == pytest.approx(
            np.array([[(1.0 - 0.9348 * val), (1.0 - 0.9348 * val)]]), 1e-4
        )

        defl11 = g0.deflections_from_grid(
            grid=al.grid.manual_2d([[[(1.0 - 0.9348 * val), (1.0 - 0.9348 * val)]]])
        )

        assert traced_positions_of_planes[2][0] == pytest.approx(
            np.array(
                [
                    [
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 0]),
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 1]),
                    ]
                ]
            ),
            1e-4,
        )

        assert traced_positions_of_planes[3][0] == pytest.approx(
            np.array([[1.0, 1.0]]), 1e-4
        )

        assert traced_positions_of_planes[0][1] == pytest.approx(
            np.array([[1.0, 1.0]]), 1e-4
        )

        assert traced_positions_of_planes[1][1] == pytest.approx(
            np.array([[(1.0 - 0.9348 * val), (1.0 - 0.9348 * val)]]), 1e-4
        )

        defl11 = g0.deflections_from_grid(
            grid=al.grid.manual_2d([[[(1.0 - 0.9348 * val), (1.0 - 0.9348 * val)]]])
        )

        assert traced_positions_of_planes[2][1] == pytest.approx(
            np.array(
                [
                    [
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 0]),
                        (1.0 - beta_02 * val - beta_12 * defl11[0, 1]),
                    ]
                ]
            ),
            1e-4,
        )

        assert traced_positions_of_planes[3][1] == pytest.approx(
            np.array([[1.0, 1.0]]), 1e-4
        )