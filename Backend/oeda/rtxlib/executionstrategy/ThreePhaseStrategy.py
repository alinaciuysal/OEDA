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
    # as we have only one data type, e.g. overhead
    considered_data_type_name = wf.considered_data_types[0]["name"]
    wf.analysis["data_type"] = considered_data_type_name
    successful = start_factorial_tests(wf)

    if successful:
        stage_ids, samples, knobs = get_tuples(wf.id, considered_data_type_name)
        anova_result = db().get_analysis(experiment_id=wf.id, stage_ids=stage_ids, analysis_name='two-way-anova')
        print(anova_result)
        # now we want to select the most important factors out of anova result
    else:
        error("> ANOVA failed")

    info(">")

def get_key(wf):
    for chVarName in wf._oeda_experiment["changeableVariables"]:
        variable = wf._oeda_experiment["changeableVariables"][chVarName]
        if variable["is_selected"]:
            return chVarName
