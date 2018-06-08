from colorama import Fore
from oeda.log import *
from oeda.rtxlib.execution import experimentFunction
from oeda.analysis.analysis_execution import start_factorial_tests
from oeda.databases import db
from oeda.rtxlib.executionstrategy.StepStrategy import start_step_strategy
from oeda.analysis.analysis_execution import get_tuples, delete_combination_notation, \
                                             iterate_anova_tables, get_significant_interactions

def start_three_phase_strategy(wf):
    """ executes ANOVA, bayesian opt, and Ttest """
    info("> ExecStrategy   | 3Phase", Fore.CYAN)

    info("> Starting experimentFunction for ANOVA")
    start_step_strategy(wf)

    info("> Starting ANOVA")
    # as we have only one data type, e.g. overhead
    considered_data_type_name = wf.considered_data_types[0]["name"]
    wf.analysis["data_type"] = considered_data_type_name
    successful, aov_table, aov_table_sqr = start_factorial_tests(wf)

    if successful:
        stage_ids, samples, knobs = get_tuples(wf.id, considered_data_type_name)
        anova_result = db().get_analysis(experiment_id=wf.id, stage_ids=stage_ids, analysis_name='two-way-anova')
        print "##########"
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(anova_result)
        print "##########"
        # now we want to select the most important factors out of anova result

        significant_interactions = []
        alpha = wf.analysis["anovaAlpha"]
        anova_results = anova_result["anova_result"]

        for interaction_key in anova_results.keys():
            pvalue = anova_results[interaction_key]['PR(>F)']
            if pvalue < alpha:
                significant_interactions.append((interaction_key, pvalue))

        sorted_significant_interactions = sorted((value, key) for (key,value) in significant_interactions.items())
        print "!!!!!!!!!"
        pp.pprint(sorted_significant_interactions)
        print "!!!!!!!!!"

        aov_table = aov_table.sort_values(by='PR(>F)', ascending=True)
        aov_table = aov_table[aov_table["PR(>F)"] < wf.analysis["anovaAlpha"]]
        # aov_table = aov_table[aov_table["omega_sq"] > min_effect_size]

        print "********"
        print aov_table
        print "********"




    else:
        error("> ANOVA failed")

    info(">")

def get_key(wf):
    for chVarName in wf._oeda_experiment["changeableVariables"]:
        variable = wf._oeda_experiment["changeableVariables"][chVarName]
        if variable["is_selected"]:
            return chVarName
