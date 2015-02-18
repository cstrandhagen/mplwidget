import numpy as np
import scipy.misc
from lmfit.model import Model
from lmfit.models import update_param_vals, index_of


__author__ = 'uffinger'


def guess_from_peak(model, y, x):
    "estimate amp, cen, sigma for a peak, create params"
    if x is None:
        return 1.0, 0.0, 1.0
    maxy, miny = max(y), min(y)
    imaxy = index_of(y, maxy)
    mu = x[imaxy]
    amp = (maxy - miny)*2.0

    pars = model.make_params(mu=mu, amp=amp)
    return pars

COMMON_DOC = """

Parameters
----------
independent_vars: list of strings to be set as variable names
missing: None, 'drop', or 'raise'
    None: Do not check for null or missing values.
    'drop': Drop null or missing observations in data.
        Use pandas.isnull if pandas is available; otherwise,
        silently fall back to numpy.isnan.
    'raise': Raise a (more helpful) exception when data contains null
        or missing values.
prefix: string to prepend to paramter names, needed to add two Models that
    have parameter names in common. None by default.
"""


class PoissonModel(Model):
    __doc__ = "x -> amp * exp(-mu) * mu ** x / scipy.misc.factorial(x)" + COMMON_DOC

    def __init__(self, *args, **kwargs):
        def poisson(x, amp, mu):
            return amp * np.exp(-mu) * mu ** x / scipy.misc.factorial(x)
        super(PoissonModel, self).__init__(poisson, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        pars = guess_from_peak(self, data, x)
        return update_param_vals(pars, self.prefix, **kwargs)
