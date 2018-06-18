from oeda.databases import setup_experiment_database, setup_user_database, db
from oeda.analysis.factorial_tests import FactorialAnova
from oeda.analysis.two_sample_tests import Ttest
from oeda.analysis.analysis_execution import delete_combination_notation, \
    iterate_anova_tables, get_significant_interactions, get_tuples, assign_iterations
from oeda.controller.experiment_results import get_all_stage_data
import json
import pprint
pp = pprint.PrettyPrinter(indent=4)

def start_workflow_with_anova(experiment_id, step_no, key, alpha, nrOfImportantFactors, executionStrategyType, performAnova=False):
    stage_ids, samples, knobs = get_tuples(experiment_id, step_no, key)
    experiment = db().get_experiment(experiment_id)
    print(json.dumps(experiment, indent=4))
    print(stage_ids)
    print(json.dumps(experiment, indent=4))
    # if performAnova:
    #     save_anova(experiment_id, step_no, stage_ids, samples, knobs, key)

    # retrieved = db().get_analysis(experiment_id=experiment_id, step_no=step_no, analysis_name='two-way-anova')
    # significant_interactions = get_significant_interactions(retrieved['anova_result'], alpha, nrOfImportantFactors)
    # significant_interactions = assign_iterations(experiment, significant_interactions, executionStrategyType)
    # print("ssi", significant_interactions)

def test_data_points(experiment_id, step_no):
    data, knobs = db().get_data_for_analysis(experiment_id, step_no)
    print("data", data)
    print("knobs", knobs)

def save_anova(experiment_id, step_no, stage_ids, samples, knobs, key):
    test = FactorialAnova(stage_ids=stage_ids, y_key=key, knob_keys=None, stages_count=len(stage_ids))
    aov_table, aov_table_sqr = test.run(data=samples, knobs=knobs)
    print(json.dumps(aov_table, indent=4))

    aov_table = delete_combination_notation(aov_table)
    aov_table_sqr = delete_combination_notation(aov_table_sqr)

    print(json.dumps(aov_table, indent=4))

    # type(dd) is DefaultOrderedDict
    dod = iterate_anova_tables(aov_table=aov_table, aov_table_sqr=aov_table_sqr)
    print(json.dumps(dod, indent=4))
    # db().save_analysis(experiment_id=experiment_id, step_no=step_no, analysis_name=test.name, anova_result=dod)

def start_workflow_with_ttest(experiment_id, key, alpha):
    experiment = db().get_experiment(experiment_id)
    pp.pprint(experiment)
    last_step_no = experiment["numberOfSteps"]
    stage_ids, samples, knobs = get_tuples(experiment_id=experiment_id, step_no=last_step_no, key=key)
    pp.pprint(stage_ids)
    pp.pprint(samples)
    pp.pprint(knobs)

    #
    # test1 = Ttest(stage_ids=stage_ids, y_key=key, alpha=alpha)
    # result = test1.run(data=samples, knobs=knobs)
    # print(json.dumps(result, indent=4))
    # db().save_analysis(experiment_id=experiment_id, step_no=wf.step_no, analysis_name=test1.name, result=result)

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

if __name__ == '__main__':
    nrOfImportantFactors = 3 # to be retrieved from analysis definition
    alpha = 0.05 # to be retrieved from analysis definition
    setup_experiment_database("elasticsearch", "localhost", 9200)
    experiment_id = "2b4fff74-c6ba-4469-7036-3fc4a3726e48"
    step_no = "1" # 1 denotes step-strategy phase for ANOVA, last one denotes T-test, intermediate ones denote Bayesian Opt
    key = "overhead"
    test_data_points(experiment_id, step_no)
    # set performAnova to true if there are data in DB & you want to save fresh anova result to DB
    # start_workflow_with_anova(experiment_id, step_no, key, alpha, nrOfImportantFactors, 'self-optimizer', True)
    # start_workflow_with_ttest(experiment_id=experiment_id, key=key, alpha=alpha)
    # asd = db().get_experiment(experiment_id=experiment_id)["numberOfSteps"]
    # all_stage_data = get_all_stage_data(experiment_id=experiment_id)
    # print(json.dumps(all_stage_data, indent=4))
    # print(all_stage_data.keys())
    # print(all_stage_data[1])
    # stage_ids, stages = db().get_stages(experiment_id=experiment_id, step_no=step_no)

