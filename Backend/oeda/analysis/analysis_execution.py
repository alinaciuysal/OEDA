from oeda.databases import db
from oeda.log import *
from oeda.analysis.two_sample_tests import Ttest, TtestPower, TtestSampleSizeEstimation
from oeda.analysis.one_sample_tests import DAgostinoPearson, AndersonDarling, KolmogorovSmirnov, ShapiroWilk
from oeda.analysis.n_sample_tests import Bartlett, FlignerKilleen, KruskalWallis, Levene, OneWayAnova
from oeda.analysis.factorial_tests import FactorialAnova

from collections import defaultdict
from math import sqrt
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
def start_factorial_tests(wf):
    id = wf.id
    key = wf.analysis["data_type"]

    # key = "overhead"
    if key is not None:
        stage_ids, samples, knobs = get_tuples(id, key)
        test = FactorialAnova(stage_ids=stage_ids, y_key=key, knob_keys=None, stages_count=len(stage_ids))
        aov_table, aov_table_sqr = test.run(data=samples, knobs=knobs)
        # type(dd) is defaultdict with unique keys
        dd = iterate_anova_tables(aov_table=aov_table, aov_table_sqr=aov_table_sqr)

        # keys e.g. C(exploration_percentage), C(route_random_sigma), Residual
        # resultDict e.g. {'PR(>F)': 0.0949496951695454, 'F': 2.8232330924997346 ...
        anova_result = dict()
        for key, resultDict in dd.items():
            anova_result[key] = resultDict
            for inner_key, value in resultDict.items():
                if str(value) == 'nan':
                    value = None
                anova_result[key][inner_key] = value
        db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, anova_result=anova_result)
        return True
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
# rows are keys of the result obj
# values are inner keys of those keys
def iterate_anova_tables(aov_table, aov_table_sqr):
    dd = defaultdict(dict)
    print(aov_table)
    # iterate first table
    for row in aov_table.itertuples():
        for col_name in list(aov_table):
            if col_name == "PR(>F)" and hasattr(row, "_4"): # PR(>F) is translated to _4 TODO: why?
                dd[row.Index][col_name] = getattr(row, "_4")
            elif hasattr(row, col_name):
                dd[row.Index][col_name] = getattr(row, col_name)

    print(aov_table_sqr)
    # iterate second table
    for row in aov_table_sqr.itertuples():
        for col_name in list(aov_table_sqr):
            if hasattr(row, col_name):
                dd[row.Index][col_name] = getattr(row, col_name)
    return dd