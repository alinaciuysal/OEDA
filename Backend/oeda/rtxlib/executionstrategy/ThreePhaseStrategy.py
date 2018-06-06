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

def get_key(wf):
    for chVar in wf._oeda_experiment["changeableVariables"]:
        if chVar["is_default"]:
            return chVar["name"]
