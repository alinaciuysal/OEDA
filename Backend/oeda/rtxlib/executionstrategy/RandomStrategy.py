from oeda.log import *
from oeda.rtxlib.execution import experimentFunction
from skopt import gp_minimize

def random_execution(wf, optimum_values, variables):
    """ this is the function we call and that returns a value for optimization """
    knob_object = recreate_knob_from_optimizer_values(variables, optimum_values)
    # create a new experiment to run in execution
    exp = dict()
    exp["ignore_first_n_samples"] = wf.primary_data_provider["ignore_first_n_samples"]
    exp["sample_size"] = wf.execution_strategy["sample_size"]
    exp["knobs"] = knob_object
    wf.setup_stage(wf, exp["knobs"])
    execution_result = experimentFunction(wf, exp)
    info(">                | execution_result: " + str(execution_result))
    return execution_result


def start_random_strategy(wf):
    """ executes experiments by randomly picking values from the provided interval(s) """
    info("> ExecStrategy   | Random", Fore.CYAN)
    wf.totalExperiments = wf.execution_strategy["optimizer_iterations"]
    optimizer_iterations_in_design = wf.execution_strategy["optimizer_iterations_in_design"]

    # we look at the ranges the user has specified in the knobs
    knobs = wf.execution_strategy["knobs"]
    # we create a list of variable names and a list of knob (from,to)

    variables = []
    range_tuples = []
    # we fill the arrays and use the index to map from gauss-optimizer-value to variable
    for key in knobs:
        variables += [key]
        # range_tuples += [ [knobs[key][0], knobs[key][1] ] ]
        range_tuples += [(knobs[key][0], knobs[key][1])]

    info("> RandomStrategy   | wf.totalExperiments" + str(wf.totalExperiments), Fore.CYAN)
    info("> RandomStrategy   | knobs" + str(knobs), Fore.CYAN)
    info("> RandomStrategy   | range_tuples" + str(range_tuples), Fore.CYAN)

    optimizer_result = gp_minimize(lambda opti_values: random_execution(wf, opti_values, variables),
                                   range_tuples, n_calls=wf.totalExperiments, n_random_starts=optimizer_iterations_in_design)

    # optimizer is done, print results
    info(">")
    info("> OptimalResult  | Knobs:  " + str(recreate_knob_from_optimizer_values(variables, optimizer_result.x)))
    info(">                | Result: " + str(optimizer_result.fun))


def recreate_knob_from_optimizer_values(variables, optimum_values):
    """ recreates knob values from a variable """
    knob_object = {}
    # create the knobObject based on the position of the opti_values and variables in their array
    for idx, val in enumerate(variables):
        knob_object[val] = optimum_values[idx]
    return knob_object
