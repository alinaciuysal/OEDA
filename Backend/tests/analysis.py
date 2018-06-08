from oeda.databases import setup_experiment_database, setup_user_database, db
from collections import defaultdict
from oeda.analysis.factorial_tests import FactorialAnova
from oeda.analysis.analysis_execution import delete_combination_notation, \
    iterate_anova_tables, get_significant_interactions, get_tuples, extract_inner_values

import pprint
pp = pprint.PrettyPrinter(indent=4)

# there are >= 2 samples for anova
def start_anova(id, key, alpha, nrOfParameters):
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


    retrieved = db().get_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name='two-way-anova')
    pp.pprint(retrieved)

    # following part will be integrated to ThreePhaseStr.
    # aov_table = delete_combination_notation(aov_table)
    # aov_table_sqr = delete_combination_notation(aov_table_sqr)

    # si = get_significant_interactions(dd, alpha, nrOfParameters)
    # pp.pprint(si)

    return

if __name__ == '__main__':
    nrOfParameters = 3 # to be retrieved from analysis definition
    alpha = 0.5 # to be retrieved from analysis definition
    setup_experiment_database("elasticsearch", "localhost", 9200)
    id = "a780bba9-a2c7-20a5-7be9-ede26d9c9b64"
    key = "overhead"
    start_anova(id, key, alpha, nrOfParameters)