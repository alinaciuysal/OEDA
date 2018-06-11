from oeda.databases import db
from oeda.log import *
from oeda.analysis.two_sample_tests import Ttest, TtestPower, TtestSampleSizeEstimation
from oeda.analysis.one_sample_tests import DAgostinoPearson, AndersonDarling, KolmogorovSmirnov, ShapiroWilk
from oeda.analysis.n_sample_tests import Bartlett, FlignerKilleen, KruskalWallis, Levene, OneWayAnova
from oeda.analysis.factorial_tests import FactorialAnova
from oeda.rtxlib.executionstrategy.SelfOptimizerStrategy import start_self_optimizer_strategy
from oeda.rtxlib.executionstrategy.MlrStrategy import start_mlr_mbo_strategy

from collections import OrderedDict
from oeda.utilities.Structures import DefaultOrderedDict
from math import sqrt
from copy import deepcopy
from operator import itemgetter

import numpy as np

outer_key = "payload" # this is by default, see: data_point_type properties in experiment_db_config.json


def run_analysis(wf):
    """ we run the correct analysis """
    if wf.analysis["type"] == "two_sample_tests":
        start_two_sample_tests(wf)

    elif wf.analysis["type"] == "factorial_tests":
        start_factorial_tests(wf)

    elif wf.analysis["type"] == "one_sample_tests":
        start_one_sample_tests(wf)

    elif wf.analysis["type"] == "n_sample_tests":
        start_n_sample_tests(wf)

    info("> Finished analysis")


# there are always 2 samples for the t-test
def start_two_sample_tests(wf):
    id = wf.id
    alpha = wf.analysis["alpha"]
    key = wf.analysis["data_type"]
    mean_diff = 0.1 # as in crowdnav-elastic-ttest-sample-size/definition.py # TODO: get it from user

    stage_ids, samples, knobs = get_tuples(id, key)

    test1 = Ttest(stage_ids=stage_ids, y_key=key, alpha=alpha)
    result = test1.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test1.name, result=result)

    x1 = samples[0]
    x2 = samples[1]
    pooled_std = sqrt((np.var(x1) + np.var(x2)) / 2)
    effect_size = mean_diff / pooled_std
    test2 = TtestPower(stage_ids=stage_ids, y_key=key, effect_size=effect_size)
    result2 = test2.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test2.name, result=result2)

    test3 = TtestSampleSizeEstimation(stage_ids=stage_ids, y_key=key, effect_size=None, mean_diff=mean_diff)
    result3 = test3.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test3.name, result=result3)
    return


##########################
## One sample tests (Normality tests)
##########################
def start_one_sample_tests(wf):
    id = wf.id
    alpha = wf.analysis["alpha"]
    key = wf.analysis["data_type"]

    stage_ids, samples, knobs = get_tuples(id, key)
    test = AndersonDarling(id, key, alpha=alpha)
    # as we have only one sample, we need to pass data=samples[0]
    result = test.run(data=samples[0], knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    test = DAgostinoPearson(id, key, alpha=alpha)
    result = test.run(data=samples[0], knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    test = KolmogorovSmirnov(id, key, alpha=alpha)
    result = test.run(data=samples[0], knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    test = ShapiroWilk(id, key, alpha=alpha)
    result = test.run(data=samples[0], knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    return


#########################
# Different distributions tests
# pass necessary stage_ids to db().save_analysis() method
#########################
def start_n_sample_tests(wf):
    id = wf.id
    alpha = wf.analysis["alpha"]
    key = wf.analysis["data_type"]
    stage_ids, samples, knobs = get_tuples(id, key)

    test = OneWayAnova(stage_ids=stage_ids, y_key=key, alpha=alpha)
    result = test.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    test = KruskalWallis(stage_ids=stage_ids, y_key=key, alpha=alpha)
    result = test.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    test = Levene(stage_ids=stage_ids, y_key=key, alpha=alpha)
    result = test.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    test = Bartlett(stage_ids=stage_ids, y_key=key, alpha=alpha)
    result = test.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    test = FlignerKilleen(stage_ids=stage_ids, y_key=key, alpha=alpha)
    result = test.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)

    return


# there are >= 2 samples for factorial_tests
# ES saves the ordered dict in unordered format because of JSON serialization / deserialization
# see https://github.com/elastic/elasticsearch-py/issues/68 if you want to preserve order in ES
def start_factorial_tests(wf):
    id = wf.id
    key = wf.analysis["data_type"]

    # key = "overhead"
    if key is not None:
        stage_ids, samples, knobs = get_tuples(id, key)
        test = FactorialAnova(stage_ids=stage_ids, y_key=key, knob_keys=None, stages_count=len(stage_ids))
        aov_table, aov_table_sqr = test.run(data=samples, knobs=knobs)
        # before saving and merging tables, extract useful information
        aov_table = delete_combination_notation(aov_table)
        aov_table_sqr = delete_combination_notation(aov_table_sqr)

        # type(dd) is DefaultOrderedDict
        # keys = [exploration_percentage, route_random_sigma, exploration_percentage,route_random_sigma...]
        # resultDict e.g. {'PR(>F)': 0.0949496951695454, 'F': 2.8232330924997346 ...
        dod = iterate_anova_tables(aov_table=aov_table, aov_table_sqr=aov_table_sqr)
        try:
            # from now on, caller functions should fetch result from DB
            db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, anova_result=dod)
            return True
        except Exception as e:
            error(e.message)
            return False
    else:
        error("data type for anova is not properly provided")
        return False


def get_tuples(id, key):
    stage_ids = db().get_stages(id)[0]
    data, knobs = db().get_data_for_analysis(id)
    extract_inner_values(key=key, stage_ids=stage_ids, data=data)
    # parse data & knobs (k-v pairs) to a proper array of values
    samples = [data[stage_id] for stage_id in stage_ids]
    knobs = [knobs[stage_id] for stage_id in stage_ids]
    return stage_ids, samples, knobs


def extract_inner_values(key, stage_ids, data):
    for stage_id in stage_ids:
        res = []
        # AnalysisTest.data is a dict of stage_ids and data_points
        for data_point in data[stage_id]:
            if key in data_point[outer_key]:
                res.append(data_point[outer_key][key])
        data[stage_id] = res


# type(table) is DataFrame
# rows are keys of the result obj param1; param2; param1, param2 etc.
# values are inner keys of those keys, type of values is dict
# set NaN or nan values to None to save to DB properly
# they are like (nan, <type 'float'>), so we compare them by str
def iterate_anova_tables(aov_table, aov_table_sqr):
    dd = DefaultOrderedDict(OrderedDict)
    # iterate first table
    for row in aov_table.itertuples():
        for col_name in list(aov_table):
            if col_name == "PR(>F)" and hasattr(row, "_4"): # PR(>F) is translated to _4 because of pandas?
                val = getattr(row, "_4")
                if str(val) == 'nan' or str(val) == 'NaN':
                    val = None
                dd[row.Index][col_name] = val
            elif hasattr(row, col_name):
                val = getattr(row, col_name)
                if str(val) == 'nan' or str(val) == 'NaN':
                    val = None
                dd[row.Index][col_name] = val

    # iterate second table
    for row in aov_table_sqr.itertuples():
        for col_name in list(aov_table_sqr):
            if hasattr(row, col_name):
                val = getattr(row, col_name)
                if str(val) == 'nan' or str(val) == 'NaN':
                    val = None
                dd[row.Index][col_name] = val

    return dd


# https://stackoverflow.com/questions/4406501/change-the-name-of-a-key-in-dictionary
# https://stackoverflow.com/questions/40855900/pandas-rename-index-values
def delete_combination_notation(table):
    for r in table.index:
        corrected = []
        keys = str(r).split(':')
        for k in keys:
            k = str(k).replace('C(', '').replace(')', '')
            corrected.append(k)
        if len(corrected) != 0:
            res = ""
            for idx, k in enumerate(corrected):
                res += k
                if idx != len(corrected) - 1:
                    res += ", "
            table = table.rename(index={r: res})
    return table


# https://stackoverflow.com/questions/16412563/python-sorting-dictionary-of-dictionaries
def get_significant_interactions(anova_result, alpha, nrOfParameters):
    # now we want to select the most important factors out of result
    significant_interactions = []
    for interaction_key in anova_result.keys():
        res = anova_result[interaction_key]
        # Residual will be filtered here because of None check
        if 'PR(>F)' in res:
            pvalue = res['PR(>F)']
            if pvalue < alpha and pvalue is not None:
                significant_interactions.append((interaction_key, res, pvalue))

    # sort w.r.t pvalue and also pass other values to caller fcn
    sorted_significant_interactions = sorted((pvalue, interaction_key, res) for (interaction_key, res, pvalue) in significant_interactions)
    if sorted_significant_interactions:
        dd = DefaultOrderedDict(OrderedDict)
        # Filtering phase
        idx = 0
        for (pvalue, interaction_key, res) in sorted_significant_interactions:
            if idx < nrOfParameters:
                # TODO: mark the selected ones in DB, for UI to use this properly, update_analysis method should be changed
                # for now, we'll re-iterate tuples and mark them in UI
                res["is_selected"] = True
                dd[interaction_key] = res
            idx += 1
        return dd
    return None


''' distributes number of iterations within optimization to respective significant interactions
    e.g. nrOfFoundInteractions = 10, and we have 3 influencing factors; then
        4 will be assigned to first (most) influencing factor, 3 will be assigned to second & third factor
    as we use DefaultOrderedDict, we preserve the insertion order of tuples and we get keys based on index of values
'''
def assign_iterations(experiment, significant_interactions, execution_strategy_type):
    nrOfFoundInteractions = len(significant_interactions.keys())
    optimizer_iterations = experiment["executionStrategy"]["optimizer_iterations"]

    values = []
    # https://stackoverflow.com/questions/10366327/dividing-a-integer-equally-in-x-parts
    for i in range(nrOfFoundInteractions):
        values.append(optimizer_iterations / nrOfFoundInteractions)    # integer division

    # divide up the remainder
    for i in range(optimizer_iterations % nrOfFoundInteractions):
        values[i] += 1
    # here, values = [4, 3, 3] for nrOfFoundInteractions = 3, optimizer_iterations = 10
    # keys = ['rrs', 'ep', 'rrs, exploration_percentage']
    info("> values " + str(values))
    for i in range(len(values)):
        key = significant_interactions.keys()[i]
        # TODO: set UI so that smaller value cannot be retrieved,

        # if you have more values in keys, then you need to set opt_iter_in_design accordingly
        # the restriction of n_calls <= 4 * nrOfParams is coming from gp_minimize
        if values[i] < len(str(key).split(', ')) * 4:
            values[i] = len(str(key).split(', ')) * 4
        significant_interactions[key]["optimizer_iterations"] = values[i]
        significant_interactions[key]["optimizer_iterations_in_design"] = len(str(key).split(', ')) * 4
    info("> Significant Interactions " + str(significant_interactions))
    return significant_interactions


def start_bogp(wf, sorted_significant_interactions):
    execution_strategy_type = wf.execution_strategy["type"]
    assigned_iterations = assign_iterations(wf._oeda_experiment, sorted_significant_interactions, execution_strategy_type)
    newExecutionStrategy = deepcopy(wf._oeda_experiment["executionStrategy"])
    # print(newExecutionStrategy)
    knobs = newExecutionStrategy["knobs"]
    # k, v example: "route_random_sigma, exploration_percentage": {"optimizer_iterations": 3,"PR(>F)": 0.13678788369818956, "optimizer_iterations_in_design": 8 ...}
    # after changing knobs parameter of experiment.executionStrategy, perform experimentation for each interaction (v)
    optimal_tuples = []
    for k, v in sorted_significant_interactions.items():
        print("k: ", k, " v: ", v)
        # here chVars are {u'route_random_sigma': [0, 0.4], u'exploration_percentage': [0, 0.4, 0.6]}
        # print(experiment["changeableVariables"])
        # if there is only one x value in key, then fetch min & max values from chVars
        new_knob = {}
        params = str(k).split(', ')
        if len(params) == 1:
            min_value = knobs[k][0]
            max_value = knobs[k][-1]
            new_knob[str(k)] = [min_value, max_value]
        else:
            for parameter in params:
                all_values = knobs[parameter] # e.g. [0, 0.2, 0.4]
                new_knob[parameter] = [all_values[0], all_values[-1]]

        # prepare everything needed for experimentation
        # fetch optimizer_iterations and optimizer_iterations_in_design from assigned_iterations
        newExecutionStrategy["knobs"] = new_knob
        newExecutionStrategy["optimizer_iterations"] = assigned_iterations[k]["optimizer_iterations"]
        newExecutionStrategy["optimizer_iterations_in_design"] = assigned_iterations[k]["optimizer_iterations_in_design"]

        # set new values in wf
        wf.execution_strategy = newExecutionStrategy

        # perform desired optimization process
        # after each experimentation, we will get best value & knob related with that value
        # to find optimum out of all experimentations, we use optimal_tuples array to keep track & sort at the end
        # TODO: 3) insert result to db (create an abstraction of phase1-2-3 etc.) to create experiment_id
        if wf.execution_strategy["type"] == 'self_optimizer':
            optimal_knob, optimal_value = start_self_optimizer_strategy(wf)
            optimal_tuples.append((optimal_knob, optimal_value))
            info("> Optimal knob at the end of Bayesian process (scikit): " + str(optimal_knob) + ", " + str(optimal_value))
        elif wf.execution_strategy["type"] == 'mlr_mbo':
            optimal_knob, optimal_value = start_mlr_mbo_strategy(wf)
            optimal_tuples.append((optimal_knob, optimal_value))
            info("> Optimal knob at the end of Bayesian process (mlr-mbo): " + str(optimal_knob) + ", " + str(optimal_value))
        # TODO: to save result to db, we need a new experiment_id, o/w previous ones will be overwritten
    info("> All knobs & values " + str(optimal_tuples))
    # find the best tuple (knob & result)
    sorted_tuples = sorted(optimal_tuples, key=lambda x: x[1])
    info("> Sorted knobs & values " + str(sorted_tuples))
    # e.g. {'route_random_sigma': 0.3, 'exploration_percentage': 0.5}, 0.4444444
    return sorted_tuples[0][0], sorted_tuples[0][1]
