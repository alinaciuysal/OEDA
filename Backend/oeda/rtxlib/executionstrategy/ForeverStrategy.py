from colorama import Fore

from oeda.log import *
from oeda.rtxlib.execution import experimentFunction


def start_forever_strategy(wf):
    """ executes forever - changes must come from definition file """
    info("> ExecStrategy   | Forever ", Fore.CYAN)
    wf.totalExperiments = -1
    while True:
        experimentFunction(wf, {
            "knobs": {"forever": True},
            "ignore_first_n_samples": wf.primary_data_provider["ignore_first_n_samples"],
            "sample_size": wf.execution_strategy["sample_size"],
        })
