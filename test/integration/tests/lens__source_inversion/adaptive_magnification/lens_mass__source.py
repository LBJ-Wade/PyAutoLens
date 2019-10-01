import autofit as af
import autolens as al
from test import runner

test_type = "lens__source_inversion"
test_name = "lens_mass__source_adaptive_magnification"
data_type = "lens_mass__source_smooth"
data_resolution = "LSST"


def make_pipeline(name, phase_folders, optimizer_class=af.MultiNest):
    class SourcePix(al.PhaseImaging):
        def customize_priors(self, results):

            self.galaxies.lens.mass.mask_centre.centre_0 = 0.0
            self.galaxies.lens.mass.mask_centre.centre_1 = 0.0
            self.galaxies.lens.mass.einstein_radius = 1.6

    phase1 = SourcePix(
        phase_name="phase_1",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5, mass=al.mass_profiles.EllipticalIsothermal
            ),
            source=al.GalaxyModel(
                redshift=1.0,
                pixelization=al.pixelizations.VoronoiMagnification,
                regularization=al.regularization.Constant,
            ),
        ),
        optimizer_class=optimizer_class,
    )

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 60
    phase1.optimizer.sampling_efficiency = 0.8

    phase1 = phase1.extend_with_inversion_phase()

    class SourcePix(al.PhaseImaging):
        def customize_priors(self, results):

            self.galaxies.source = results.last.inversion.constant.galaxies.source

    phase2 = SourcePix(
        phase_name="phase_2",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5, mass=phase1.result.variable.galaxies.lens.mass
            ),
            source=al.GalaxyModel(
                redshift=1.0,
                pixelization=al.pixelizations.VoronoiMagnification,
                regularization=al.regularization.Constant,
            ),
        ),
        optimizer_class=optimizer_class,
    )

    phase2.optimizer.const_efficiency_mode = True
    phase2.optimizer.n_live_points = 60
    phase2.optimizer.sampling_efficiency = 0.8

    phase2 = phase2.extend_with_inversion_phase()

    return al.PipelineImaging(name, phase1, phase2)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
