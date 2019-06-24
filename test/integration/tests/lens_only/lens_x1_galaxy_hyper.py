import os

import autofit as af
import autofit as af
from autolens.model.galaxy import galaxy as g
from autolens.model.galaxy import galaxy_model as gm
from autolens.pipeline.phase import phase_imaging as ph
from autolens.pipeline import pipeline as pl
from autolens.model.profiles import light_profiles as lp
from test.integration import integration_util
from test.simulation import simulation_util

test_type = 'lens_only'
test_name = "lens_x1_galaxy_hyper"

test_path = '{}/../../'.format(os.path.dirname(os.path.realpath(__file__)))
output_path = test_path + 'output/'
config_path = test_path + 'config'
af.conf.instance = af.conf.Config(config_path=config_path, output_path=output_path)


def pipeline():

    integration_util.reset_paths(test_name=test_name, output_path=output_path)
    ccd_data = simulation_util.load_test_ccd_data(data_type='lens_only_bulge_and_disk', data_resolution='LSST')
    pipeline = make_pipeline(test_name=test_name)
    pipeline.run(data=ccd_data)

def make_pipeline(test_name):

    phase1 = ph.LensPlanePhase(
        phase_name='phase_1', phase_folders=[test_type, test_name],
        lens_galaxies=dict(lens=gm.GalaxyModel(redshift=0.5, light=lp.EllipticalSersic)),
        optimizer_class=nl.MultiNest)

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 40
    phase1.optimizer.sampling_efficiency = 0.8

    phase1h = ph.HyperGalaxyPhase(phase_name='phase_1_hyper', phase_folders=[test_type, test_name])

    phase1h.optimizer.const_efficiency_mode = True
    phase1h.optimizer.n_live_points = 40
    phase1h.optimizer.sampling_efficiency = 0.8

    class HyperLensPlanePhase(ph.LensPlanePhase):

        def pass_priors(self, results):

            self.lens_galaxies.lens.hyper_galaxy = results.from_phase('phase_1_hyper').\
                constant.lens_galaxies.lens.hyper_galaxy

            self.lens_galaxies.lens.light = results.from_phase('phase_1').\
                variable.lens_galaxies.lens.light

    phase2 = HyperLensPlanePhase(
        phase_name='phase_2', phase_folders=[test_type, test_name],
        lens_galaxies=dict(lens=gm.GalaxyModel(redshift=0.5, light=lp.EllipticalSersic, hyper_galaxy=g.HyperGalaxy)),
        optimizer_class=nl.MultiNest)

    phase2.optimizer.const_efficiency_mode = True
    phase2.optimizer.n_live_points = 40
    phase2.optimizer.sampling_efficiency = 0.8

    return pl.PipelineImaging(test_name, phase1, phase1h, phase2)


if __name__ == "__main__":
    pipeline()
