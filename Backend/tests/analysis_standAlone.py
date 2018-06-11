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
    if performAnova:
        save_anova(key, stage_ids, samples, knobs)

    retrieved = db().get_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name='two-way-anova')
    significant_interactions = get_significant_interactions(retrieved['anova_result'], alpha, nrOfImportantFactors)
    significant_interactions = assign_iterations(experiment, significant_interactions)
    print("ssi", significant_interactions)


if __name__ == '__main__':
    nrOfParameters = 3 # to be retrieved from analysis definition
    alpha = 0.5 # to be retrieved from analysis definition
    setup_experiment_database("elasticsearch", "localhost", 9200)
    id = "0ad830ff-02b2-285a-93e6-5c7229a91f58"
    key = "overhead"
    # set performAnova to true if there are data in DB & you want to save fresh anova result to DB
    start_workflow(id, key, alpha, nrOfParameters)