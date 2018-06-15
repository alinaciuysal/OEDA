from colorama import Fore
from oeda.log import *
from oeda.analysis.analysis_execution import start_factorial_tests, start_two_sample_tests
from oeda.databases import db
from oeda.rtxlib.executionstrategy.StepStrategy import start_step_strategy
from oeda.rtxlib.executionstrategy.SequencialStrategy import start_sequential_strategy
from oeda.analysis.analysis_execution import get_tuples, get_significant_interactions, start_bogp
from oeda.rtxlib.executionstrategy import create_knob_from_default

import pprint
pp = pprint.PrettyPrinter(indent=4)

def start_three_phase_analysis(wf):
    """ executes ANOVA, bayesian opt, and Ttest """
    info("> Analysis   | 3-Phase", Fore.CYAN)
    info("> Starting experimentFunction for ANOVA, setting step_no to 1")
    wf.step_no = 1 # set step_no to 1 initially, as we did not perform any experiment stage_counter is still 0
    start_step_strategy(wf)
    info("> Starting ANOVA, step_no is still 1")
    # we have only one data type, e.g. overhead
    considered_data_type_name = wf.considered_data_types[0]["name"]
    wf.analysis["data_type"] = considered_data_type_name
    successful = start_factorial_tests(wf)
    if successful:
        all_res = db().get_analysis(experiment_id=wf.id, step_no=wf.step_no, analysis_name='two-way-anova')
        # now we want to select the most important factors out of anova result, following can also be integrated
        # aov_table = aov_table[aov_table["omega_sq"] > min_effect_size]
        sorted_significant_interactions = get_significant_interactions(all_res["anova_result"], wf.analysis["anovaAlpha"], wf.analysis["nrOfImportantFactors"])
        info("> Sorted significant interactions " + str(sorted_significant_interactions))
        # in this case, we can't find any significant interactions
        if sorted_significant_interactions is None:
            db().update_analysis(experiment_id=wf.id, step_no=wf.step_no, analysis_name='two-way-anova', field='eligible_for_next_step', value=False)
            db().update_experiment(experiment_id=wf.id, field='numberOfSteps', value=wf.step_no)
            info("> Cannot find significant interactions, aborting process")
        else:
            db().update_analysis(experiment_id=wf.id, step_no=wf.step_no, analysis_name='two-way-anova', field='eligible_for_next_step', value=True)
            info("> Starting Optimization process, setting step_no to 2, re-setting stage_counter, updating numberOfSteps in experiment")
            wf.step_no += 1
            wf.stage_counter = 1 # first step is done, reset stage counter to 1 and remove experimentCounter attribute
            delattr(wf, 'experimentCounter')
            db().update_experiment(experiment_id=wf.id, field='numberOfSteps', value=wf.step_no)

            best_knob, best_result = start_bogp(wf=wf, sorted_significant_interactions=sorted_significant_interactions)
            default_knob = create_knob_from_default(wf=wf)
            info("> Step no for T-test, " + str(wf.step_no))
            info("> Default knob for T-test, " + str(default_knob))
            info("> Best knob for T-test," + str(best_knob))

            info("> Starting T-test, step_no: " + str(wf.step_no) + " re-setting stage_counter")
            # perform experiments with default & best knobs in another step
            # also save this to experiment in ES
            # there is no need to increment step_no because at the last stage of bogp, it gets incremented
            # but we need to reset stage_counter and remove experimentCounter attribute, it will be assigned properly in experimentFunction(wf)
            wf.stage_counter = 1
            delattr(wf, 'experimentCounter')
            db().update_experiment(experiment_id=wf.id, field='numberOfSteps', value=wf.step_no)

            # prepare knobs accordingly
            wf.execution_strategy["knobs"] = [default_knob, best_knob]
            # set tTestSampleSize as executionStr sample_size
            wf.execution_strategy["sample_size"] = wf.analysis["tTestSampleSize"]

            start_sequential_strategy(wf=wf)
            # perform T-test
            t_test_result = start_two_sample_tests(wf=wf)
            info("> T-test result is saved to DB:" + str(t_test_result))
    else:
        error("> ANOVA failed")

    info(">")