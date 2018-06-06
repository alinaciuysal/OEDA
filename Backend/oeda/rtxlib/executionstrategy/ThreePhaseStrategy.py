from colorama import Fore
from oeda.log import *
from oeda.rtxlib.execution import experimentFunction
from oeda.analysis.analysis_execution import start_factorial_tests
from oeda.databases import db
from oeda.rtxlib.executionstrategy.StepStrategy import start_step_strategy
from oeda.analysis.analysis_execution import get_tuples

def start_three_phase_strategy(wf):
    """ executes ANOVA, bayesian opt, and Ttest """
    info("> ExecStrategy   | 3Phase", Fore.CYAN)

    info("> Starting experimentFunction for ANOVA")
    start_step_strategy(wf)

    info("> Starting ANOVA")
    key = get_key(wf)
    wf.analysis["data_type"] = key
    successful = start_factorial_tests(wf)

    if successful:
        stage_ids, samples, knobs = get_tuples(wf.id, key)
        anova_result = db().get_analysis(experiment_id=wf.id, stage_ids=stage_ids, test_name='two-way-anova')
        print(anova_result)
        # now we want to select the most important factors out of anova result
    else:
        error("> ANOVA failed")

    info(">")


def recreate_knob_from_optimizer_values(variables, opti_values):
    """ recreates knob values from a variable """
    knob_object = {}
    # create the knobObject based on the position of the opti_values and variables in their array
    for idx, val in enumerate(variables):
        knob_object[val] = opti_values[idx]
    return knob_object


def self_optimizer_execution(wf, opti_values, variables):
    """ this is the function we call and that returns a value for optimization """
    knob_object = recreate_knob_from_optimizer_values(variables, opti_values)
    # create a new experiment to run in execution
    exp = dict()
    exp["ignore_first_n_samples"] = wf.primary_data_provider["ignore_first_n_samples"]
    exp["sample_size"] = wf.execution_strategy["sample_size"]
    exp["knobs"] = knob_object
    wf.setup_stage(wf, exp["knobs"])
    return experimentFunction(wf, exp)


def get_key(wf):
    for chVar in wf.experiment["changeableVariables"]:
        if chVar["is_default"]:
            return chVar["name"]
