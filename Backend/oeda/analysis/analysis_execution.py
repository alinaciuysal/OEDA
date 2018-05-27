from oeda.databases import db
from oeda.log import *
from oeda.analysis.two_sample_tests import Ttest, TtestPower, TtestSampleSizeEstimation
from oeda.analysis.factorial_tests import FactorialAnova
from collections import defaultdict

outer_key = "payload" # this is default, see: data_point_type properties in experiment_db_config.json

def run_analysis(wf):
    """ we run the correct analysis """
    if wf.analysis["type"] == "t_test":
        start_t_test(wf)

    elif wf.analysis["type"] == "anova":
        start_anova(wf)

    info("> Finished analysis")

# there are always 2 samples for the t-test
def start_t_test(wf):
    id = wf.id
    alpha = wf.analysis["alpha"]
    key = wf.analysis["data_type"]
    # key = "overhead"
    # alpha = 0.05
    stage_ids, samples, knobs = get_tuples(id, key)
    test = Ttest(stage_ids=stage_ids, y_key="overhead", alpha=alpha)
    result = test.run(data=samples, knobs=knobs)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, result=result)
    return


# there are >= 2 samples for anova
def start_anova(wf):
    id = wf.id
    key = wf.analysis["data_type"]
    # key = "overhead"
    stage_ids, samples, knobs = get_tuples(id, key)
    test = FactorialAnova(stage_ids=stage_ids, y_key=key, knob_keys=None, stages_count=len(stage_ids))
    aov_table, aov_table_sqr = test.run(data=samples, knobs=knobs)
    # type(dd) is defaultdict with unique keys
    dd = iterate_anova_tables(aov_table=aov_table, aov_table_sqr=aov_table_sqr)
    print(dd.items())
    anova_result = {}
    for k, v in dd.items():
        anova_result[k] = v
    print("res", anova_result)
    # TODO: Problem in ES while parsing anova_result
    # db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, anova_result=anova_result)
    # retrieved = db().get_analysis(id, stage_ids, test.name)
    # print("retrieved", retrieved)
    return


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