from autolens.aggregator import aggregator as agg

import numpy as np
from autogalaxy.plot.plotter import lensing_plotter, lensing_include
from autogalaxy.plot.plots import plane_plots, inversion_plots
from autolens.plot.plots import fit_imaging_plots
from autoarray.plot.plotter import plotter
import os
from os import path
import shutil


def agg_max_log_likelihood_from_aggregator(aggregator):

    samples = list(filter(None, aggregator.values("samples")))
    log_likelihoods = [max(samps.log_likelihoods) for samps in samples]
    index = np.argmax(log_likelihoods)
    search_max = list(filter(None, aggregator.values("search")))[index]

    directory = str(search_max.paths.name)
    directory = directory.replace(r"/", path.sep)

    return aggregator.filter(aggregator.directory.contains(directory))


def copy_pickle_files_to_agg_max(agg_max_log_likelihood):

    search_max_log_likelihood = list(agg_max_log_likelihood.values("search"))
    pickle_path_max_log_likelihood = search_max_log_likelihood[0].paths.pickle_path

    pickle_path_max_log_likelihood = str(pickle_path_max_log_likelihood).replace(
        r"/", path.sep
    )

    pickle_path_grid_search = pickle_path_max_log_likelihood

    pickle_path_grid_search = path.split(pickle_path_grid_search)[0]
    pickle_path_grid_search = path.split(pickle_path_grid_search)[0]
    pickle_path_grid_search = path.split(pickle_path_grid_search)[0]

    # TODO : needed for linux?

    #   pickle_path_grid_search = path.split(pickle_path_grid_search)[0]
    #   pickle_path_grid_search = path.split(pickle_path_grid_search)[0]

    pickle_path_grid_search = path.join(pickle_path_grid_search, "pickles")

    src_files = os.listdir(pickle_path_grid_search)

    for file_name in src_files:
        full_file_name = path.join(pickle_path_grid_search, file_name)
        if path.isfile(full_file_name):
            shutil.copy(full_file_name, pickle_path_max_log_likelihood)


def detection_array_from(
    agg_before, agg_detect, use_log_evidences=True, use_stochastic_log_evidences=False
):

    fit_imaging_before = list(
        agg.fit_imaging_generator_from_aggregator(aggregator=agg_before)
    )[0]

    if use_log_evidences and not use_stochastic_log_evidences:
        figure_of_merit_before = list(agg_before.values("samples"))[0].log_evidence
    elif use_stochastic_log_evidences:
        figure_of_merit_before = np.median(
            list(agg_before.values("stochastic_log_evidences"))[0]
        )
    else:
        figure_of_merit_before = fit_imaging_before.figure_of_merit

    return (
        agg.grid_search_result_as_array(
            aggregator=agg_detect,
            use_log_evidences=use_log_evidences,
            use_stochastic_log_evidences=use_stochastic_log_evidences,
        )
        - figure_of_merit_before,
    )[0]


def mass_array_from(agg_detect):
    return agg.grid_search_subhalo_masses_as_array(aggregator=agg_detect)


@lensing_include.set_include
@lensing_plotter.set_plotter_for_subplot
@plotter.set_subplot_filename
def subplot_detection_agg(
    agg_before,
    agg_detect,
    use_log_evidences=True,
    use_stochastic_log_evidences=False,
    include=None,
    plotter=None,
):

    fit_imaging_before = list(
        agg.fit_imaging_generator_from_aggregator(aggregator=agg_before)
    )[0]

    agg_max_log_likelihood = agg_max_log_likelihood_from_aggregator(
        aggregator=agg_detect
    )

    copy_pickle_files_to_agg_max(agg_max_log_likelihood=agg_max_log_likelihood)

    fit_imaging_detect = list(
        agg.fit_imaging_generator_from_aggregator(aggregator=agg_max_log_likelihood)
    )[0]

    detection_array = detection_array_from(
        agg_before=agg_before,
        agg_detect=agg_detect,
        use_log_evidences=use_log_evidences,
        use_stochastic_log_evidences=use_stochastic_log_evidences,
    )

    mass_array = mass_array_from(agg_detect=agg_detect)

    subplot_detection_fits(
        fit_imaging_before=fit_imaging_before,
        fit_imaging_detect=fit_imaging_detect,
        include=include,
        plotter=plotter,
    )

    subplot_detection_imaging(
        fit_imaging_detect=fit_imaging_detect,
        detection_array=detection_array,
        mass_array=mass_array,
        include=include,
        plotter=plotter,
    )


@lensing_include.set_include
@lensing_plotter.set_plotter_for_subplot
@plotter.set_subplot_filename
def subplot_detection_fits(
    fit_imaging_before, fit_imaging_detect, include=None, plotter=None
):
    """
    A subplot comparing the normalized residuals, chi-squared map and source reconstructions of the model-fits
    before the subhalo added to the model (top row) and the subhalo fit which gives the largest increase in
    Bayesian evidence on the subhalo detection grid search.

    Parameters
    ----------
    fit_imaging_before : FitImaging
        The fit of a `Tracer` not including a subhalo in the model to a `MaskedImaging` dataset (e.g. the
        model-image, residual_map, chi_squared_map).
    fit_imaging_detect : FitImaging
        The fit of a `Tracer` with the subhalo detection grid's highest evidence model including a subhalo to a
        `MaskedImaging` dataset (e.g. the  model-image, residual_map, chi_squared_map).
    include : Include
        Customizes what appears on the plots (e.g. critical curves, profile centres, origin, etc.).
    plotter : Plotter
        Object for plotting PyAutoLens data-stuctures as subplots via Matplotlib.
    """
    number_subplots = 6

    plotter.open_subplot_figure(number_subplots=number_subplots)

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=1)

    plotter_detect = plotter.plotter_with_new_labels(
        title_label="Normailzed Residuals (No Subhalo)"
    )

    fit_imaging_plots.normalized_residual_map(
        fit=fit_imaging_before, include=include, plotter=plotter_detect
    )

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=2)

    plotter_detect = plotter.plotter_with_new_labels(
        title_label="Chi-Squared Map (No Subhalo)"
    )

    fit_imaging_plots.chi_squared_map(
        fit=fit_imaging_before, include=include, plotter=plotter_detect
    )

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=3)

    plotter_detect = plotter.plotter_with_new_labels(
        title_label="Source Reconstruction (No Subhalo)"
    )

    source_model_on_subplot(
        fit=fit_imaging_before,
        plane_index=1,
        number_subplots=6,
        subplot_index=3,
        include=include,
        plotter=plotter_detect,
    )

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=4)

    plotter_detect = plotter.plotter_with_new_labels(
        title_label="Normailzed Residuals (With Subhalo)"
    )

    fit_imaging_plots.normalized_residual_map(
        fit=fit_imaging_detect, include=include, plotter=plotter_detect
    )

    plotter_detect = plotter.plotter_with_new_labels(
        title_label="Chi-Squared Map (With Subhalo)"
    )

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=5)

    fit_imaging_plots.chi_squared_map(
        fit=fit_imaging_detect, include=include, plotter=plotter_detect
    )

    plotter_detect = plotter.plotter_with_new_labels(
        title_label="Source Reconstruction (With Subhalo)"
    )

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=6)

    source_model_on_subplot(
        fit=fit_imaging_detect,
        plane_index=1,
        number_subplots=6,
        subplot_index=6,
        include=include,
        plotter=plotter_detect,
    )

    plotter.output.subplot_to_figure()

    plotter.figure.close()


@lensing_include.set_include
@lensing_plotter.set_plotter_for_subplot
@plotter.set_subplot_filename
def subplot_detection_imaging(
    fit_imaging_detect, detection_array, mass_array, include=None, plotter=None
):

    number_subplots = 4

    plotter.open_subplot_figure(number_subplots=number_subplots)

    plotter_detect = plotter.plotter_with_new_labels(title_label="Image")

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=1)

    fit_imaging_plots.image(
        fit=fit_imaging_detect, include=include, plotter=plotter_detect
    )

    plotter_detect = plotter.plotter_with_new_labels(title_label="Signal-To-Noise Map")

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=2)

    fit_imaging_plots.signal_to_noise_map(
        fit=fit_imaging_detect, include=include, plotter=plotter_detect
    )

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=3)

    plotter_detect = plotter.plotter_with_new_labels(
        title_label="Increase in Log Evidence"
    )

    plotter.plot_array(
        array=detection_array,
        extent_manual=fit_imaging_detect.image.extent,
        include=include,
        plotter=plotter_detect,
    )

    plotter.setup_subplot(number_subplots=number_subplots, subplot_index=4)

    plotter_detect = plotter.plotter_with_new_labels(title_label="Subhalo Mass")

    plotter.plot_array(
        array=mass_array,
        extent_manual=fit_imaging_detect.image.extent,
        include=include,
        plotter=plotter_detect,
    )

    plotter.output.subplot_to_figure()

    plotter.figure.close()


def source_model_on_subplot(
    fit, plane_index, number_subplots, subplot_index, include, plotter
):

    if not fit.tracer.planes[plane_index].has_pixelization:

        plotter.setup_subplot(
            number_subplots=number_subplots, subplot_index=subplot_index
        )

        traced_grids = fit.tracer.traced_grids_of_planes_from_grid(grid=fit.grid)

        plane_plots.plane_image(
            plane=fit.tracer.planes[plane_index],
            grid=traced_grids[plane_index],
            positions=include.positions_of_plane_from_fit_and_plane_index(
                fit=fit, plane_index=plane_index
            ),
            caustics=include.caustics_from_obj(obj=fit.tracer),
            include=include,
            plotter=plotter,
        )

    elif fit.tracer.planes[plane_index].has_pixelization:

        ratio = float(
            (
                fit.inversion.mapper.grid.scaled_maxima[1]
                - fit.inversion.mapper.grid.scaled_minima[1]
            )
            / (
                fit.inversion.mapper.grid.scaled_maxima[0]
                - fit.inversion.mapper.grid.scaled_minima[0]
            )
        )

        aspect_inv = plotter.figure.aspect_for_subplot_from_ratio(ratio=ratio)

        plotter.setup_subplot(
            number_subplots=number_subplots,
            subplot_index=subplot_index,
            aspect=float(aspect_inv),
        )

        inversion_plots.reconstruction(
            inversion=fit.inversion,
            source_positions=include.positions_of_plane_from_fit_and_plane_index(
                fit=fit, plane_index=plane_index
            ),
            caustics=include.caustics_from_obj(obj=fit.tracer),
            include=include,
            plotter=plotter,
        )
