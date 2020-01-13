import autolens as al
from autolens.pipeline import visualizer as vis
import os
import pytest
from os import path
from autofit import conf

directory = path.dirname(path.realpath(__file__))

@pytest.fixture(name="visualizer_plotter_path")
def make_visualizer_plotter_setup():
    return "{}/../../test_files/plotting/visualizer/".format(
        os.path.dirname(os.path.realpath(__file__))
    )


@pytest.fixture(autouse=True)
def set_config_path():
    conf.instance = conf.Config(
        path.join(directory, "../test_files/plotters"), path.join(directory, "output")
    )


class TestPhaseSetVisualizer:


    def test__visualizes_ray_tracing_using_configs(
       self,  masked_imaging_7x7, tracer_x2_plane_7x7, visualizer_plotter_path, plot_patch
    ):
        visualizer = vis.PhaseDatasetVisualizer(
            masked_dataset=masked_imaging_7x7, image_path=visualizer_plotter_path)

        visualizer.visualize_ray_tracing(tracer=tracer_x2_plane_7x7, during_analysis=True)


        assert visualizer_plotter_path + "subplots/subplot_tracer.png" in plot_patch.paths
        assert (
            visualizer_plotter_path + "ray_tracing/profile_image.png" in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "ray_tracing/source_plane.png" in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "ray_tracing/convergence.png"
            in plot_patch.paths
        )
        assert visualizer_plotter_path + "ray_tracing/potential.png" not in plot_patch.paths
        assert (
            visualizer_plotter_path + "ray_tracing/deflections_y.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "ray_tracing/deflections_x.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "ray_tracing/magnification.png"
            in plot_patch.paths
        )



class TestPhaseImagingVisualizer:

    def test__visualizes_imaging_using_configs(
        self, masked_imaging_7x7, visualizer_plotter_path, plot_patch
    ):

        visualizer = vis.PhaseImagingVisualizer(
            masked_dataset=masked_imaging_7x7,
            image_path=visualizer_plotter_path)

        visualizer.visualize_imaging()

        assert visualizer_plotter_path + "subplots/subplot_imaging.png" in plot_patch.paths
        assert visualizer_plotter_path + "imaging/image.png" in plot_patch.paths
        assert visualizer_plotter_path + "imaging/noise_map.png" not in plot_patch.paths
        assert visualizer_plotter_path + "imaging/psf.png" in plot_patch.paths
        assert (
            visualizer_plotter_path + "imaging/signal_to_noise_map.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "imaging/absolute_signal_to_noise_map.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "imaging/potential_chi_squared_map.png"
            in plot_patch.paths
        )


    def test__source_and_lens__visualizes_fit_using_configs(
        self, masked_imaging_7x7, masked_imaging_fit_x2_plane_7x7, visualizer_plotter_path, plot_patch
    ):

        visualizer = vis.PhaseImagingVisualizer(
            masked_dataset=masked_imaging_7x7, image_path=visualizer_plotter_path)

        visualizer.visualize_fit(fit=masked_imaging_fit_x2_plane_7x7, during_analysis=True)

        assert visualizer_plotter_path + "subplots/subplot_fit_imaging.png" in plot_patch.paths
        assert visualizer_plotter_path + "fit_imaging/image.png" in plot_patch.paths
        assert visualizer_plotter_path + "fit_imaging/noise_map.png" not in plot_patch.paths
        assert (
            visualizer_plotter_path + "fit_imaging/signal_to_noise_map.png" not in plot_patch.paths
        )
        assert visualizer_plotter_path + "fit_imaging/model_image.png" in plot_patch.paths
        assert visualizer_plotter_path + "fit_imaging/residual_map.png" not in plot_patch.paths
        assert (
            visualizer_plotter_path + "fit_imaging/normalized_residual_map.png" in plot_patch.paths
        )
        assert visualizer_plotter_path + "fit_imaging/chi_squared_map.png" in plot_patch.paths
        assert (
            visualizer_plotter_path + "fit_imaging/subtracted_image_of_plane_0.png"
            in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "fit_imaging/subtracted_image_of_plane_1.png"
            in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "fit_imaging/model_image_of_plane_0.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "fit_imaging/model_image_of_plane_1.png"
            not in plot_patch.paths
        )
        assert visualizer_plotter_path + "fit_imaging/plane_image_of_plane_0.png" in plot_patch.paths
        assert visualizer_plotter_path + "fit_imaging/plane_image_of_plane_1.png" in plot_patch.paths

    def test__visualizes_hyper_images_using_config(
        self, masked_imaging_7x7, hyper_model_image_7x7, hyper_galaxy_image_path_dict_7x7, visualizer_plotter_path, plot_patch,
    ):

        visualizer = vis.PhaseImagingVisualizer(
            masked_dataset=masked_imaging_7x7, image_path=visualizer_plotter_path)

        class MockLastResults(object):

            def __init__(self, hyper_model_image, hyper_galaxy_image_path_dict):

                self.hyper_model_image = hyper_model_image
                self.hyper_galaxy_image_path_dict = hyper_galaxy_image_path_dict

        last_results = MockLastResults(hyper_model_image=hyper_model_image_7x7, hyper_galaxy_image_path_dict=hyper_galaxy_image_path_dict_7x7)

        visualizer.visualize_hyper_images(last_results=last_results)

        assert visualizer_plotter_path + "hyper/hyper_model_image.png" in plot_patch.paths
        assert visualizer_plotter_path + "hyper/subplot_hyper_galaxy_images.png" in plot_patch.paths

class TestPhaseInterferometerVisualizer:

    def test__visualizes_interferometer_using_configs(
        self, masked_interferometer_7, general_config, visualizer_plotter_path, plot_patch
    ):

        visualizer = vis.PhaseInterferometerVisualizer(
            masked_dataset=masked_interferometer_7,
            image_path=visualizer_plotter_path)

        visualizer.visualize_interferometer()

        assert visualizer_plotter_path + "subplots/subplot_interferometer.png" in plot_patch.paths
        assert (
            visualizer_plotter_path + "interferometer/visibilities.png"
            in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "interferometer/u_wavelengths.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "interferometer/v_wavelengths.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "interferometer/primary_beam.png"
            in plot_patch.paths
        )

    def test__source_and_lens__visualizes_fit_using_configs(
        self, masked_interferometer_7, masked_interferometer_fit_x2_plane_7x7, visualizer_plotter_path, plot_patch
    ):

        visualizer = vis.PhaseInterferometerVisualizer(
            masked_dataset=masked_interferometer_7, image_path=visualizer_plotter_path)

        visualizer.visualize_fit(fit=masked_interferometer_fit_x2_plane_7x7, during_analysis=True)

        assert visualizer_plotter_path + "subplots/subplot_fit_interferometer.png" in plot_patch.paths
        assert visualizer_plotter_path + "fit_interferometer/visibilities.png" in plot_patch.paths
        assert visualizer_plotter_path + "fit_interferometer/noise_map.png" not in plot_patch.paths
        assert (
            visualizer_plotter_path + "fit_interferometer/signal_to_noise_map.png" not in plot_patch.paths
        )
        assert visualizer_plotter_path + "fit_interferometer/model_visibilities.png" in plot_patch.paths
        assert (
            visualizer_plotter_path + "fit_interferometer/residual_map_vs_uv_distances_real.png"
            not in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "fit_interferometer/normalized_residual_map_vs_uv_distances_real.png"
            in plot_patch.paths
        )
        assert (
            visualizer_plotter_path + "fit_interferometer/chi_squared_map_vs_uv_distances_real.png"
            in plot_patch.paths
        )


class TestHyperGalaxyVisualizer:

    def test__hyper_fit__images_for_phase__source_and_lens__depedent_on_input(
        self, masked_imaging_fit_x2_plane_7x7, hyper_galaxy_image_0_7x7, visualizer_plotter_path, plot_patch
    ):

        visualizer = vis.HyperGalaxyVisualizer(
            image_path=visualizer_plotter_path)

        visualizer.visualize_hyper_galaxy(fit=masked_imaging_fit_x2_plane_7x7, hyper_fit=masked_imaging_fit_x2_plane_7x7, galaxy_image=hyper_galaxy_image_0_7x7,
                                          contribution_map_in=hyper_galaxy_image_0_7x7)

        assert (
            visualizer_plotter_path + "subplots/subplot_fit_hyper_galaxy.png" in plot_patch.paths
        )