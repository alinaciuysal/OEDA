from oeda.databases import setup_experiment_database, setup_user_database, db
from collections import defaultdict
from oeda.analysis.factorial_tests import FactorialAnova

# there are >= 2 samples for anova
def start_anova(id):
    key = "overhead"
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
    outer_key = "payload"
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
    # iterate first table
    for row in aov_table.itertuples():
        for col_name in list(aov_table):
            if col_name == "PR(>F)" and hasattr(row, "_4"): # PR(>F) is translated to _4 TODO: why?
                dd[row.Index][col_name] = getattr(row, "_4")
            elif hasattr(row, col_name):
                dd[row.Index][col_name] = getattr(row, col_name)
    # iterate second table
    for row in aov_table_sqr.itertuples():
        for col_name in list(aov_table_sqr):
            if hasattr(row, col_name):
                dd[row.Index][col_name] = getattr(row, col_name)
    return dd

def get_influence_parameters(anova_result, nrOfParameters):
    print(anova_result)
    print(type(anova_result))
    return anova_result

if __name__ == '__main__':
    # setup_user_database()
    setup_experiment_database("elasticsearch", "localhost", 9200)
    id = "a780bba9-a2c7-20a5-7be9-ede26d9c9b64"
    stage_ids = ["6dc62e9c-3625-85ca-657e-3b06cc269828#1", "6dc62e9c-3625-85ca-657e-3b06cc269828#2", "6dc62e9c-3625-85ca-657e-3b06cc269828#3", "6dc62e9c-3625-85ca-657e-3b06cc269828#4"]
    retrieved = db().get_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name="two-way-anova")
    nrOfParameters = 2 # to be retrieved from experiment definition
    get_influence_parameters(retrieved["anova_result"], nrOfParameters)