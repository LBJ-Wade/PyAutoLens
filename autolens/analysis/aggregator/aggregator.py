import autofit as af
import autolens as al

from autofit import exc

from autofit.database.model.fit import Fit
from autogalaxy.analysis.aggregator.aggregator import (
    imaging_via_database_from,
    interferometer_via_database_from,
)

from functools import partial
import numpy as np
from os import path
import json

from typing import Optional, List
from itertools import chain

def tracer_gen_from(aggregator : af.Aggregator):
    """
    Returns a generator of `Tracer` objects from an input aggregator, which generates a list of the maximum log
    likelihood `Tracer` objects for the results loaded in the aggregator.

    This is performed by mapping the `tracer_max_log_likelihood_via_database_from` with the aggregator, which sets up
    each tracer using only generators ensuring that manipulating the planes of large sets of results is done in a
    memory efficient way.

    Parameters
    ----------
    aggregator
        A PyAutoFit aggregator object containing the results of PyAutoLens model-fits.
    """
    return aggregator.map(func=tracer_max_log_likelihood_via_database_from)


def tracer_pdf_gen_from(aggregator : af.Aggregator, total_samples : int):
    """
    Returns a generator of multiple `Tracer` objects from an input aggregator, which for every result generates a list
    of `Tracer` objects whose parameter values are drawn randomly from the PDF. This enables straight forward error
    estimation.

    This is performed by mapping the `tracer_randomly_drawn_from_pdf_via_database_from` with the aggregator, which
    sets up each tracer using only generators ensuring that manipulating the tracers of large sets of results is done in
    a memory efficient way.

    Parameters
    ----------
    aggregator : af.Aggregator
        A PyAutoFit aggregator object containing the results of PyAutoLens model-fits.
    """
    for i in range(total_samples):

        plane_gen = aggregator.map(func=tracer_randomly_drawn_from_pdf_via_database_from)

        if i > 0:
            generator = chain(generator, plane_gen)
        else:
            generator = plane_gen

    return generator


def tracer_max_log_likelihood_via_database_from(fit: Fit) -> "al.Tracer":
    """
    Returns a `Tracer` object from the database's `Fit` object, corresponding to the maximum log likelihood model.

    The plane's galaxies have their hyper-images added (if they were used in the fit).

    Parameters
    ----------
    fit
        A PyAutoFit database Fit object containing the generators of the results of PyAutoGalaxy model-fits.
    """

    galaxies = fit.instance.galaxies

    return tracer_from(fit=fit, galaxies=galaxies)


def tracer_randomly_drawn_from_pdf_via_database_from(fit: Fit) -> "al.Tracer":
    """
    Returns a `Tracer` object from the `Samples` object of the non-linear search. where the model is chosen randomly
    from the PDF.

    The plane's galaxies have their hyper-images added (if they were used in the fit).

    Parameters
    ----------
    fit
        A PyAutoFit database Fit object containing the generators of the results of PyAutoGalaxy model-fits.
    """

    samples = fit.value(name="samples")

    instance = samples.instance_drawn_randomly_from_pdf()

    return tracer_from(fit=fit, galaxies=instance.galaxies)


def tracer_from(fit: Fit, galaxies : List[al.Galaxy]) -> "al.Tracer":
    """
    Returns a `Tracer` object from an input PyAutoFit `Fit` object and an instance of galaxies from the model-fit.

    This function adds the `hyper_model_image` and `hyper_galaxy_image_path_dict` to the galaxies before constructing
    the `Tracer`, if they were used for the model fit.

    Parameters
    ----------
    fit
        A PyAutoFit database Fit object containing the generators of the results of PyAutoGalaxy model-fits.
    galaxies
        A list of galaxies corresponding to a sample in a non-linear search and model-fit.

    Returns
    -------
    tracer
        The tracer computed via an instance of galaxies.
    """
    
    hyper_model_image = fit.value(name="hyper_model_image")
    hyper_galaxy_image_path_dict = fit.value(name="hyper_galaxy_image_path_dict")

    galaxies_with_hyper = []

    if hyper_galaxy_image_path_dict is not None:

        for (galaxy_path, galaxy) in fit.instance.path_instance_tuples_for_class(
            al.Galaxy
        ):
            if galaxy_path in hyper_galaxy_image_path_dict:
                galaxy.hyper_model_image = hyper_model_image
                galaxy.hyper_galaxy_image = hyper_galaxy_image_path_dict[galaxy_path]

            galaxies_with_hyper.append(galaxy)

        return al.Tracer.from_galaxies(galaxies=galaxies_with_hyper)

    return al.Tracer.from_galaxies(galaxies=galaxies)


def fit_imaging_gen_from(
    aggregator: af.Aggregator,
    settings_imaging: Optional[al.SettingsImaging] = None,
    settings_pixelization: Optional[al.SettingsPixelization] = None,
    settings_inversion: Optional[al.SettingsInversion] = None,
    use_preloaded_grid: bool = True,
):
    """
    Returns a generator of `FitImaging` objects from an input aggregator, which generates a list of the
    `FitImaging` objects for every set of results loaded in the aggregator.

    This is performed by mapping the `fit_imaging_from_agg_obj` with the aggregator, which sets up each fit using
    only generators ensuring that manipulating the fits of large sets of results is done in a memory efficient way.

    Parameters
    ----------
    aggregator : af.Aggregator
        A PyAutoFit aggregator object containing the results of PyAutoLens model-fits."""

    func = partial(
        fit_imaging_via_database_from,
        settings_imaging=settings_imaging,
        settings_pixelization=settings_pixelization,
        settings_inversion=settings_inversion,
        use_preloaded_grid=use_preloaded_grid,
    )

    return aggregator.map(func=func)


def fit_imaging_via_database_from(
    fit: Fit,
    settings_imaging: al.SettingsImaging = None,
    settings_pixelization: al.SettingsPixelization = None,
    settings_inversion: al.SettingsInversion = None,
    use_preloaded_grid: bool = True,
) -> "al.FitImaging":
    """
    Returns a `FitImaging` object from an aggregator's `SearchOutput` class, which we call an 'agg_obj' to describe
    that it acts as the aggregator object for one result in the `Aggregator`. This uses the aggregator's generator
    outputs such that the function can use the `Aggregator`'s map function to to create a `FitImaging` generator.

    The `FitImaging` is created.

    Parameters
    ----------
    fit : af.SearchOutput
        A PyAutoFit aggregator's SearchOutput object containing the generators of the results of PyAutoLens model-fits.
    """
    imaging = imaging_via_database_from(fit=fit, settings_imaging=settings_imaging)
    tracer = tracer_max_log_likelihood_via_database_from(fit=fit)

    settings_pixelization = settings_pixelization or fit.value(
        name="settings_pixelization"
    )
    settings_inversion = settings_inversion or fit.value(name="settings_inversion")

    preloads = al.Preloads()

    if use_preloaded_grid:

        sparse_grids_of_planes = fit.value(name="preload_sparse_grids_of_planes")

        if sparse_grids_of_planes is not None:

            preloads = al.Preloads(sparse_grids_of_planes=sparse_grids_of_planes)

    return al.FitImaging(
        imaging=imaging,
        tracer=tracer,
        settings_pixelization=settings_pixelization,
        settings_inversion=settings_inversion,
        preloads=preloads,
    )


def fit_interferometer_gen_from(
    aggregator: af.Aggregator,
    settings_interferometer: al.SettingsInterferometer = None,
    settings_pixelization: al.SettingsPixelization = None,
    settings_inversion: al.SettingsInversion = None,
    use_preloaded_grid: bool = True,
):
    """
    Returns a `FitInterferometer` object from an aggregator's `SearchOutput` class, which we call an 'agg_obj' to
    describe that it acts as the aggregator object for one result in the `Aggregator`. This uses the aggregator's
    generator outputs such that the function can use the `Aggregator`'s map function to to create a `FitInterferometer`
    generator.

    The `FitInterferometer` is created.

    Parameters
    ----------
    agg_obj : af.SearchOutput
        A PyAutoFit aggregator's SearchOutput object containing the generators of the results of PyAutoLens model-fits.
    """

    func = partial(
        fit_interferometer_via_database_from,
        settings_interferometer=settings_interferometer,
        settings_pixelization=settings_pixelization,
        settings_inversion=settings_inversion,
        use_preloaded_grid=use_preloaded_grid,
    )
    return aggregator.map(func=func)


def fit_interferometer_via_database_from(
    fit: Fit,
    real_space_mask: Optional[al.Mask2D] = None,
    settings_interferometer: al.SettingsInterferometer = None,
    settings_pixelization: al.SettingsPixelization = None,
    settings_inversion: al.SettingsInversion = None,
    use_preloaded_grid: bool = True,
) -> "al.FitInterferometer":
    """
    Returns a generator of `FitInterferometer` objects from an input aggregator, which generates a list of the
    `FitInterferometer` objects for every set of results loaded in the aggregator.

    This is performed by mapping the `fit_interferometer_from_agg_obj` with the aggregator, which sets up each fit
    using only generators ensuring that manipulating the fits of large sets of results is done in a memory efficient
    way.

    Parameters
    ----------
    aggregator : af.Aggregator
        A PyAutoFit aggregator object containing the results of PyAutoLens model-fits.
    """
    interferometer = interferometer_via_database_from(
        fit=fit,
        real_space_mask=real_space_mask,
        settings_interferometer=settings_interferometer,
    )
    tracer = tracer_max_log_likelihood_via_database_from(fit=fit)

    settings_pixelization = settings_pixelization or fit.value(
        name="settings_pixelization"
    )
    settings_inversion = settings_inversion or fit.value(name="settings_inversion")

    preloads = None

    if use_preloaded_grid:

        sparse_grids_of_planes = fit.value(name="preload_sparse_grids_of_planes")

        if sparse_grids_of_planes is not None:

            preloads = al.Preloads(sparse_grids_of_planes=sparse_grids_of_planes)

    return al.FitInterferometer(
        interferometer=interferometer,
        tracer=tracer,
        settings_pixelization=settings_pixelization,
        settings_inversion=settings_inversion,
        preloads=preloads,
    )


def grid_search_result_as_array(
    aggregator: af.Aggregator,
    use_log_evidences: bool = True,
    use_stochastic_log_evidences: bool = False,
) -> np.ndarray:

    grid_search_result_gen = aggregator.values("grid_search_result")

    grid_search_results = list(filter(None, list(grid_search_result_gen)))

    if len(grid_search_results) == 0:
        raise exc.AggregatorException(
            "There is no grid search resultin the aggregator."
        )
    elif len(grid_search_results) > 1:
        raise exc.AggregatorException(
            "There is more than one grid search result in the aggregator - please filter the"
            "aggregator."
        )

    return grid_search_log_evidences_as_array_from_grid_search_result(
        grid_search_result=grid_search_results[0],
        use_log_evidences=use_log_evidences,
        use_stochastic_log_evidences=use_stochastic_log_evidences,
    )


def grid_search_subhalo_masses_as_array(aggregator: af.Aggregator) -> al.Array2D:

    grid_search_result_gen = aggregator.values("grid_search_result")

    grid_search_results = list(filter(None, list(grid_search_result_gen)))

    if len(grid_search_results) != 1:
        raise exc.AggregatorException(
            "There is more than one grid search result in the aggregator - please filter the"
            "aggregator."
        )

    return grid_search_subhalo_masses_as_array_from_grid_search_result(
        grid_search_result=grid_search_results[0]
    )


def grid_search_subhalo_centres_as_array(aggregator: af.Aggregator) -> al.Array2D:

    grid_search_result_gen = aggregator.values("grid_search_result")

    grid_search_results = list(filter(None, list(grid_search_result_gen)))

    if len(grid_search_results) != 1:
        raise exc.AggregatorException(
            "There is more than one grid search result in the aggregator - please filter the"
            "aggregator."
        )

    return grid_search_subhalo_masses_as_array_from_grid_search_result(
        grid_search_result=grid_search_results[0]
    )


def grid_search_log_evidences_as_array_from_grid_search_result(
    grid_search_result,
    use_log_evidences=True,
    use_stochastic_log_evidences: bool = False,
) -> al.Array2D:

    if grid_search_result.no_dimensions != 2:
        raise exc.AggregatorException(
            "The GridSearchResult is not dimensions 2, meaning a 2D array cannot be made."
        )

    if use_log_evidences and not use_stochastic_log_evidences:
        values = [
            value
            for values in grid_search_result.log_evidence_values
            for value in values
        ]
    elif use_stochastic_log_evidences:

        stochastic_log_evidences = []

        for result in grid_search_result.results:

            stochastic_log_evidences_json_file = path.join(
                result.search.paths.output_path, "stochastic_log_evidences.json"
            )

            try:
                with open(stochastic_log_evidences_json_file, "r") as f:
                    stochastic_log_evidences_array = np.asarray(json.load(f))
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"File not found at {result.search.paths.output_path}"
                )

            stochastic_log_evidences.append(np.median(stochastic_log_evidences_array))

        values = stochastic_log_evidences

    else:
        values = [
            value
            for values in grid_search_result.max_log_likelihood_values
            for value in values
        ]

    return al.Array2D.manual_yx_and_values(
        y=[centre[0] for centre in grid_search_result.physical_centres_lists],
        x=[centre[1] for centre in grid_search_result.physical_centres_lists],
        values=values,
        pixel_scales=grid_search_result.physical_step_sizes,
        shape_native=grid_search_result.shape,
    )


def grid_search_subhalo_masses_as_array_from_grid_search_result(
    grid_search_result,
) -> [float]:

    if grid_search_result.no_dimensions != 2:
        raise exc.AggregatorException(
            "The GridSearchResult is not dimensions 2, meaning a 2D array cannot be made."
        )

    masses = [
        res.samples.median_pdf_instance.galaxies.subhalo.mass.mass_at_200
        for results in grid_search_result.results_reshaped
        for res in results
    ]

    return al.Array2D.manual_yx_and_values(
        y=[centre[0] for centre in grid_search_result.physical_centres_lists],
        x=[centre[1] for centre in grid_search_result.physical_centres_lists],
        values=masses,
        pixel_scales=grid_search_result.physical_step_sizes,
        shape_native=grid_search_result.shape,
    )


def grid_search_subhalo_centres_as_array_from_grid_search_result(
    grid_search_result,
) -> [(float, float)]:

    if grid_search_result.no_dimensions != 2:
        raise exc.AggregatorException(
            "The GridSearchResult is not dimensions 2, meaning a 2D array cannot be made."
        )

    return [
        res.samples.median_pdf_instance.galaxies.subhalo.mass.centre
        for results in grid_search_result.results_reshaped
        for res in results
    ]
