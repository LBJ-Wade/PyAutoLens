from autolens.fit.plotters import masked_imaging_fit_plotters
from test import simulation_util

imaging = simulation_util.load_test_imaging(
    data_type="lens_sis__source_smooth__offset_centre", data_resolution="LSST"
)


def fit_with_offset_centre(centre):

    mask = al.mask.elliptical(
        shape=imaging.shape,
        pixel_scales=imaging.pixel_scales,
        major_axis_radius_arcsec=3.0,
        axis_ratio=1.0,
        phi=0.0,
        centre=centre,
    )

    # The lines of code below do everything we're used to, that is, setup an image and its al.ogrid, mask it, trace it
    # via a tracer, setup the rectangular mapper, etc.
    lens_galaxy = al.galaxy(
        redshift=0.5,
        mass=al.mp.EllipticalIsothermal(
            centre=(1.0, 1.0), einstein_radius=1.6, axis_ratio=0.7, phi=45.0
        ),
    )
    source_galaxy = al.galaxy(
        redshift=1.0,
        pixelization=al.pix.VoronoiMagnification(shape=(20, 20)),
        regularization=al.reg.Constant(coefficient=1.0),
    )

    masked_imaging = al.LensData(imaging=imaging, mask=mask)

    pixelization_grid = source_galaxy.pixelization.traced_sparse_grids_of_planes_from_grid(
        grid=masked_imaging.grid
    )

    grid_stack_with_pixelization_grid = masked_imaging.grid.new_grid_stack_with_grids_added(
        pixelization=pixelization_grid
    )

    tracer = al.Tracer.from_galaxies(
        galaxies=[lens_galaxy, source_galaxy],
        image_plane_grid=grid_stack_with_pixelization_grid,
    )
    fit = al.LensImageFit.from_masked_data_and_tracer(
        masked_imaging=masked_imaging, tracer=tracer
    )

    return fit


fit = fit_with_offset_centre(centre=(1.0, 1.0))

masked_imaging_fit_plotters.plot_fit_subplot(
    fit=fit,
    should_plot_mask_overlay=True,
    positions=[[[2.2, 2.2], [-0.2, -0.2], [-0.2, 2.2], [2.2, -0.2]]],
    should_plot_image_plane_pix=True,
)

fit = fit_with_offset_centre(centre=(1.05, 1.05))


masked_imaging_fit_plotters.plot_fit_subplot(
    fit=fit,
    should_plot_mask_overlay=True,
    positions=[[[2.2, 2.2], [-0.2, -0.2], [-0.2, 2.2], [2.2, -0.2]]],
    should_plot_image_plane_pix=True,
)

fit = fit_with_offset_centre(centre=(1.1, 1.1))

masked_imaging_fit_plotters.plot_fit_subplot(
    fit=fit,
    should_plot_mask_overlay=True,
    positions=[[[2.2, 2.2], [-0.2, -0.2], [-0.2, 2.2], [2.2, -0.2]]],
    should_plot_image_plane_pix=True,
)

fit = fit_with_offset_centre(centre=(0.95, 0.95))

masked_imaging_fit_plotters.plot_fit_subplot(
    fit=fit,
    should_plot_mask_overlay=True,
    positions=[[[2.2, 2.2], [-0.2, -0.2], [-0.2, 2.2], [2.2, -0.2]]],
    should_plot_image_plane_pix=True,
)

fit = fit_with_offset_centre(centre=(5.9, 5.9))

masked_imaging_fit_plotters.plot_fit_subplot(
    fit=fit,
    should_plot_mask_overlay=True,
    positions=[[[2.2, 2.2], [-0.2, -0.2], [-0.2, 2.2], [2.2, -0.2]]],
    should_plot_image_plane_pix=True,
)