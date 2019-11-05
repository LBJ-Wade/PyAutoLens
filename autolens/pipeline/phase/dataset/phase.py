from astropy import cosmology as cosmo

import autofit as af
import autoarray as aa
from autolens.pipeline.phase import abstract
from autolens.pipeline.phase import extensions
from autolens.pipeline.phase.dataset.result import Result


def default_mask_function(shape_2d, pixel_scales):
    return aa.mask.circular(
        shape_2d=shape_2d, pixel_scales=pixel_scales, sub_size=1, radius_arcsec=3.0
    )


def isinstance_or_prior(obj, cls):
    if isinstance(obj, cls):
        return True
    if isinstance(obj, af.PriorModel) and obj.cls == cls:
        return True
    return False


class PhaseDataset(abstract.AbstractPhase):
    galaxies = af.PhaseProperty("galaxies")

    Result = Result

    def __init__(
        self,
        phase_name,
        phase_tag,
        phase_folders=tuple(),
        galaxies=None,
        optimizer_class=af.MultiNest,
        cosmology=cosmo.Planck15,
    ):
        """

        A phase in an lens pipeline. Uses the set non_linear optimizer to try to fit models and hyper_galaxies
        passed to it.

        Parameters
        ----------
        optimizer_class: class
            The class of a non_linear optimizer
        """

        super(PhaseDataset, self).__init__(
            phase_name=phase_name,
            phase_tag=phase_tag,
            phase_folders=phase_folders,
            optimizer_class=optimizer_class,
        )
        self.galaxies = galaxies or []
        self.cosmology = cosmology

        self.is_hyper_phase = False

    def run(self, dataset, results=None, mask=None, positions=None):
        """
        Run this phase.

        Parameters
        ----------
        positions
        mask: Mask
            The default masks passed in by the pipeline
        results: autofit.tools.pipeline.ResultsCollection
            An object describing the results of the last phase or None if no phase has been executed
        dataset: scaled_array.ScaledSquarePixelArray
            An masked_imaging that has been masked

        Returns
        -------
        result: AbstractPhase.Result
            A result object comprising the best fit model and other hyper_galaxies.
        """
        self.variable = self.variable.populate(results)

        analysis = self.make_analysis(
            dataset=dataset, results=results, mask=mask, positions=positions
        )

        self.customize_priors(results)
        self.assert_and_save_pickle()

        result = self.run_analysis(analysis)

        return self.make_result(result=result, analysis=analysis)

    def make_analysis(self, dataset, results=None, mask=None, positions=None):
        """
        Create an lens object. Also calls the prior passing and masked_imaging modifying functions to allow child
        classes to change the behaviour of the phase.

        Parameters
        ----------
        positions
        mask: Mask
            The default masks passed in by the pipeline
        dataset: im.Imaging
            An masked_imaging that has been masked
        results: autofit.tools.pipeline.ResultsCollection
            The result from the previous phase

        Returns
        -------
        lens : Analysis
            An lens object that the non-linear optimizer calls to determine the fit of a set of values
        """
        raise NotImplementedError()

    def extend_with_inversion_phase(self):
        return extensions.InversionPhase(phase=self)