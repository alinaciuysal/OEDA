from oeda.databases import setup_experiment_database, setup_user_database, db
from oeda.analysis.factorial_tests import FactorialAnova
from oeda.analysis.analysis_execution import delete_combination_notation, \
    iterate_anova_tables, get_significant_interactions, get_tuples, assign_iterations
import json
from copy import deepcopy


def save_anova(key, stage_ids, samples, knobs):
    test = FactorialAnova(stage_ids=stage_ids, y_key=key, knob_keys=None, stages_count=len(stage_ids))
    aov_table, aov_table_sqr = test.run(data=samples, knobs=knobs)

    aov_table = delete_combination_notation(aov_table)
    aov_table_sqr = delete_combination_notation(aov_table_sqr)

    # type(dd) is DefaultOrderedDict
    dod = iterate_anova_tables(aov_table=aov_table, aov_table_sqr=aov_table_sqr)
    db().save_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name=test.name, anova_result=dod)


def start_workflow(id, key, alpha, nrOfImportantFactors, performAnova=False):
    stage_ids, samples, knobs = get_tuples(id, key)
    experiment = db().get_experiment(id)
    print(stage_ids)
    print(knobs)
    if performAnova:
        save_anova(key, stage_ids, samples, knobs)

    retrieved = db().get_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name='two-way-anova')
    significant_interactions = get_significant_interactions(retrieved['anova_result'], alpha, nrOfImportantFactors)
    significant_interactions = assign_iterations(experiment, significant_interactions)
    print("ssi", significant_interactions)

def sort():
    tuples = []
    tuple_1 = ({"ep": 0.2, "rrs": 0.4}, 0.5555)
    tuple_2 = ({"ep": 0.5, "rrs": 0.3}, 0.4444)
    tuple_3 = ({"ep": 0.2222, "rrs": 0.222}, 0.8888)
    tuple_4 = ({"ep": 0.3333, "rrs": 0.333}, 0.6666)
    tuples.append(tuple_1)
    tuples.append(tuple_2)
    tuples.append(tuple_3)
    tuples.append(tuple_4)
    sorted_tuples = sorted(tuples, key=lambda x: x[1])
    print("sorted_tuples", sorted_tuples)
    print("best_knob", sorted_tuples[0][0], " best_value", sorted_tuples[0][1])
    # new_tuples = [k for (k, v) in sorted(tuples, key=lambda x: x[1])]
    # print(new_tuples)
    # tuples = tuples.sort(key=lambda x: x[1])
    # print(tuples)

if __name__ == '__main__':
    # nrOfParameters = 3 # to be retrieved from analysis definition
    # alpha = 0.5 # to be retrieved from analysis definition
    # setup_experiment_database("elasticsearch", "localhost", 9200)
    # id = "f11fcd7b-784a-6611-93a7-e7e9b641015e"
    # key = "overhead"
    # # set performAnova to true if there are data in DB & you want to save fresh anova result to DB
    # start_workflow(id, key, alpha, nrOfParameters)
    sort()