import autofit as af
import autolens as al
from test import runner

test_type = "phase_features"
test_name = "bin_up_factor"
data_type = "lens_light_dev_vaucouleurs"
data_resolution = "LSST"


def make_pipeline(name, phase_folders, optimizer_class=af.MultiNest):

    phase1 = al.PhaseImaging(
        phase_name="phase_1",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=al.GalaxyModel(redshift=0.5, sersic=al.light_profiles.EllipticalSersic)
        ),
        bin_up_factor=2,
        optimizer_class=optimizer_class,
    )

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 40
    phase1.optimizer.sampling_efficiency = 0.8

    return al.PipelineImaging(name, phase1)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
