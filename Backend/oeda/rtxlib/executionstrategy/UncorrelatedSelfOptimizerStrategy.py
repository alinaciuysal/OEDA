from colorama import Fore
from oeda.rtxlib.executionstrategy.SelfOptimizerStrategy import self_optimizer_execution, recreate_knob_from_optimizer_values

from skopt import gp_minimize
from oeda.log import *
from oeda.rtxlib.execution import experimentFunction


def start_uncorrelated_self_optimizer_strategy(wf):
    """ executes a self optimizing strategy """

    acquisition_method = wf.execution_strategy["acquisition_method"]
    info("> ExecStrategy   | UncorrelatedSelfOptimizer", Fore.CYAN)
    info("> Optimizer      | " + acquisition_method, Fore.CYAN)

    knobs = wf.execution_strategy["knobs"]
    info("> Knobs      | " + str(knobs), Fore.CYAN)
    wf.totalExperiments = len(knobs) * wf.execution_strategy["optimizer_iterations"]
    total_result = dict()
    # we fill the arrays and use the index to map from gauss-optimizer-value to variable
    for key in knobs:
        min_value = min(float(knobs[key][0]), float(knobs[key][1]))
        max_value = max(float(knobs[key][0]), float(knobs[key][1]))
        optimal_knob_value = optimizeOneVariable(wf, wf.execution_strategy["optimizer_iterations"], key,
                                                 (min_value, max_value))
        info("> optimal_knob_value      | " + str(optimal_knob_value), Fore.CYAN)

        if type(optimal_knob_value) is list:
            optimal_knob_value = optimal_knob_value[0]

        total_result[key] = optimal_knob_value
        wf.change_provider["instance"].applyChange(total_result)
    info(">")
    info("> FinalResult    | Best Values: " + str(total_result))


#  we also use code from the SelfOptimizerStrategy as it is the same here

def optimizeOneVariable(wf, optimizer_iterations, key, range):
    variables = [key]
    range_tuples = [range]
    optimizer_iterations_in_design = wf.execution_strategy["optimizer_iterations_in_design"]
    optimizer_result = gp_minimize(lambda opti_values: self_optimizer_execution(wf, opti_values, variables),
                                   range_tuples, n_calls=optimizer_iterations, n_random_starts=optimizer_iterations_in_design)
    info(">")
    info("> OptimalResult  | Knobs:  " + str(recreate_knob_from_optimizer_values(variables, optimizer_result.x)))
    info(">                | Result: " + str(optimizer_result.fun))
    return optimizer_result.x
