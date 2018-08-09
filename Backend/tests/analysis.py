from oeda.databases import setup_experiment_database, setup_user_database, db
from collections import defaultdict
from oeda.analysis.factorial_tests import FactorialAnova
from oeda.analysis.one_sample_tests import ShapiroWilk, AndersonDarling, DAgostinoPearson, KolmogorovSmirnov
from oeda.analysis.two_sample_tests import Ttest
from oeda.analysis.n_sample_tests import Levene, Bartlett, FlignerKilleen, KruskalWallis, OneWayAnova
import json
import os
import shutil
import errno
import itertools
import numpy as np
import matplotlib.pyplot as plt

from pprint import pprint as pp

def delete_files(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


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

def get_non_default_config_results(experiments):
    # delete_files("./results/crowdnav")
    # delete_files("./results/platooning")
    make_sure_path_exists("./results/crowdnav")
    make_sure_path_exists("./results/platooning")

    crowdnav_results = []
    platooning_results = []
    for experiment in experiments:
        if str(experiment["status"]) != "RUNNING" and str(experiment["status"]) != "ERROR" and "Default" in experiment["name"]:
            # file_name = str(experiment["name"]).split("Experiment #")[1][:2].rstrip() + "_"
            file_name = str(experiment["name"]).split("Default Run with ")[1] + "_"
            print(file_name, experiment["status"])

            targetSystemId = experiment["targetSystemId"]
            ts = db().get_target(targetSystemId)

            file_name += str(experiment["executionStrategy"]["sample_size"]) + "_"
            file_name += str(experiment["executionStrategy"]["stages_count"]) + "_"
            file_name += str(experiment["analysis"]["data_type"]["name"])

            out_json = {}
            out_json["fn"] = file_name
            # out_json["experiment"] = experiment

            stage_ids, stages = db().get_stages(experiment["id"])
            stages = sorted(stages, key=lambda k: k['stage_result'])
            out_json["stages"] = stages
            if "Platooning" in ts["name"]:
                platooning_results.append(out_json)
            elif "CrowdNav" in ts["name"]:
                crowdnav_results.append(out_json)

    for res1 in platooning_results:
        fn = res1["fn"]
        with open('./results/platooning/' + str(fn) + '_default.json', 'w') as outfile:
            json.dump(res1, outfile, sort_keys=True, indent=4, ensure_ascii=False)

    for res2 in crowdnav_results:
        fn = res2["fn"]
        with open('./results/crowdnav/' + str(fn) + '_default.json', 'w') as outfile2:
            json.dump(res2, outfile2, sort_keys=True, indent=4, ensure_ascii=False)

# assuming sequential str. is only used for default configurations
def get_default_config_results(experiments):
    effect_size = 0.7
    alpha = 0.05
    make_sure_path_exists("./results/default/crowdnav")
    make_sure_path_exists("./results/default/platooning")
    crowdnav_passed = []
    crowdnav_total = []

    platooning_passed = []
    platooning_total = []
    for experiment in experiments:
        if "Default" in experiment["name"] and experiment["executionStrategy"]["type"] == "sequential":
            if str(experiment["status"]) != "RUNNING" and str(experiment["status"]) != "ERROR":
                data_type = experiment["analysis"]["data_type"]["name"]
                if data_type != 'complaint':
                    file_name = str(experiment["name"]).split("Default Run with ")[1] + "_"
                    file_name += str(experiment["executionStrategy"]["sample_size"]) + "_"
                    file_name += data_type
                    ttest_passed = 0
                    ttest_failed = 0

                    out_json = {}
                    out_json["fn"] = file_name
                    out_json["experiment"] = experiment
                    out_json["ttest"] = {}

                    stage_ids, samples, knobs = get_tuples(experiment["id"], data_type)
                    # perform two-sample-tests
                    combinations = list(itertools.combinations(stage_ids, 2))

                    for comb in combinations:
                        stage_id_1 = comb[0]
                        stage_id_idx_1 = stage_ids.index(stage_id_1)
                        data_points_1 = samples[stage_id_idx_1]

                        stage_id_2 = comb[1]
                        stage_id_idx_2 = stage_ids.index(stage_id_2)
                        data_points_2 = samples[stage_id_idx_2]

                        test1 = Ttest(stage_ids=[stage_id_1, stage_id_2], y_key=data_type, alpha=alpha)
                        result = test1.run(data=[data_points_1, data_points_2], knobs=knobs)
                        if result["different_averages"] == False:
                            ttest_passed += 1
                        elif result["different_averages"] == True and result["effect_size"] <= effect_size:
                            ttest_passed += 1
                        else:
                            ttest_failed += 1
                    print("exp_name:", file_name, " passed:", ttest_passed, "failed", ttest_failed)
                    targetSystemId = experiment["targetSystemId"]
                    ts = db().get_target(targetSystemId)

                    if "Platooning" in ts["name"]:
                        platooning_passed.append(ttest_passed)
                        platooning_total.append(len(combinations))

                    elif "CrowdNav" in ts["name"]:
                        crowdnav_passed.append(ttest_passed)
                        crowdnav_total.append(len(combinations))

        platooning_results = {}
        platooning_results["ttest_passed"] = platooning_passed
        platooning_results["ttest_total"] = platooning_total
        with open('./results/default/platooning/results.json', 'w') as outfile:
            json.dump(platooning_results, outfile, sort_keys=True, indent=4, ensure_ascii=False)

        crowdnav_results = {}
        crowdnav_results["ttest_passed"] = crowdnav_passed
        crowdnav_results["ttest_total"] = crowdnav_total
        with open('./results/default/crowdnav/results.json', 'w') as outfile:
            json.dump(crowdnav_results, outfile, sort_keys=True, indent=4, ensure_ascii=False)


def draw_default_config_results(experiment_ids, incoming_data_type, ts_name):
    make_sure_path_exists("./results/default/crowdnav")
    make_sure_path_exists("./results/default/platooning")

    results = []
    total_nr_of_iterations_of_all_experiments = 0

    for experiment_id in experiment_ids:
        experiment = db().get_experiment(experiment_id)
        # if "Default" in experiment["name"] and experiment["executionStrategy"]["type"] == "sequential":
        if str(experiment["status"]) != "RUNNING" and str(experiment["status"]) != "ERROR":
            data_type = experiment["analysis"]["data_type"]["name"]
            sample_size = experiment["executionStrategy"]["sample_size"]
            optimizer_iterations = experiment["executionStrategy"]["optimizer_iterations"]
            optimizer_iterations_in_design = experiment["executionStrategy"]["optimizer_iterations_in_design"]
            total_nr_of_iterations = optimizer_iterations + optimizer_iterations_in_design
            total_nr_of_iterations_of_all_experiments += total_nr_of_iterations
            if data_type != 'complaint' and data_type == incoming_data_type:
                stage_ids, stages = db().get_stages(experiment["id"])
                targetSystemId = experiment["targetSystemId"]
                ts = db().get_target(targetSystemId)

                if ts_name in ts["name"]:
                    results.append((sample_size, total_nr_of_iterations, stages))

                    # data, knobs = db().get_data_for_analysis(experiment["id"])
                    # extract_inner_values(key=key, stage_ids=stage_ids, data=data)
                    # stage_ids, samples, knobs = get_tuples(experiment["id"], data_type)

    # Create plot
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    colors = ("red", "green", "blue", "purple")
    for (sample_size, total_nr_of_iterations, stages), color in zip(results, colors):
        # create an index for each tick position
        xi = [i + 1 for i in range(total_nr_of_iterations)]
        stage_results = [] # y_values in the plot
        for json_obj in stages:
            stage_results.append(json_obj["stage_result"])
        ax.scatter(xi, stage_results, alpha=0.8, c=color, edgecolors='none', s=30, label=sample_size)
    plt.title('Results for optimization of ' + ts_name + '')
    plt.legend(loc=2)
    plt.show()
        # stage_results = []
        # for stage_id in data.keys():
        #     data_points_in_stage = []
        #     for json_obj in data[stage_id]:
        #         data_points_in_stage.append(json_obj["payload"][incoming_data_type])
        #     stage_results.append(np.mean(data_points_in_stage))
        # print(incoming_data_type, sample_size, stage_results)


def perform_t_test(optimized_results, default_results, y_key, alpha=0.05):
    experiment_id, stage_no = optimized_results
    stage_id = str(experiment_id) + "#" + str(stage_no)
    default_experiment_id, default_stage_no = default_results
    default_stage_id = str(experiment_id) + "#" + str(stage_no)

    exp = db().get_experiment(experiment_id)
    default_exp = db().get_experiment(default_experiment_id)
    # pp(exp)
    # pp(default_exp)

    data_points_1 = db().get_data_points(experiment_id, stage_no)
    print(data_points_1)
    only_data_1 = [d["payload"][y_key] for d in data_points_1]
    print(only_data_1)

    data_points_2 = db().get_data_points(default_experiment_id, default_stage_no)
    only_data_2 = [d["payload"][y_key] for d in data_points_2]
    print(only_data_2)

    test1 = Ttest(stage_ids=[stage_id, default_stage_id], y_key=y_key, alpha=alpha)
    result = test1.run(data=[only_data_1, only_data_2], knobs=None)

    avg_1 = np.mean(only_data_1)
    avg_default = np.mean(only_data_2)
    print(avg_1, avg_default)
    opt_percentage = -1.0 * percentage_change(avg_1, avg_default)
    result["opt_percentage"] = opt_percentage
    print(result)

def percentage_change(optimized, default):
    if default != 0:
        return float(optimized - default) / abs(default) * 100
    else:
        return "undefined"

if __name__ == '__main__':
    setup_experiment_database("elasticsearch", "localhost", 9200)
    experiments = db().get_experiments()[1]
    # get_non_default_config_results(experiments)

    # get_default_config_results(experiments)
    # draw_default_config_results(experiments, "overhead", "Platooning")
    # draw_default_config_results(experiments, "fuelConsumption", "Platooning")

    ########################
    # crowd-nav avg overhead
    # optimized_results = ("6b5776ab-1d3d-5bdf-a77a-46bb40e61afc", 93)
    # optimized_results = ("5743e5b2-5545-3a9a-4d27-25a3b68771d2", 27)

    # default_results = ("6a916c78-f122-bb2c-c93f-f2304c4cb8bc", 8)
    # default_results = ("e731c263-a5f2-ed44-587d-cd1c98b30aae", 4)
    # default_results = ("317fe993-6186-9efa-2730-aaaa50b0d490", 2)
    # perform_t_test(optimized_results, default_results, "overhead")
    ########################

    ########################
    # platooning avg overhead
    # optimized_results = ("e01777c1-883e-97c7-b123-0cd32a1a1d85", 81)
    # optimized_results = ("cb53c88d-5a47-b61e-9080-3806293b6457", 34)

    # default_results = ("a2f7025b-0899-a207-98dd-daeebaab8b6d", 1)
    # default_results = ("44cc33e4-6eea-b655-82c4-967c8c08b7f5", 8)
    # default_results = ("65d8866f-37e1-e627-fd59-64a661874e2c", 9)
    # perform_t_test(optimized_results, default_results, "overhead")
    ########################

    ########################
    # platooning avg fuelConsumption
    # optimized_results = ("a65da561-1938-eb8a-b82a-d5c8d5a8b81c", 62)
    # optimized_results = ("446dd6db-99ba-3f79-7d2e-3abb452b7542", 19)

    # default_results = ("77f422b8-1ded-7d5b-9c33-5f44cbfd64e2", 6)
    # default_results = ("d35c17ac-9252-ec76-a511-ed3289a1ce0a", 4)
    # perform_t_test(optimized_results, default_results, "fuelConsumption")
    ########################

    ########################
    # platooning avg tripDuration
    # optimized_results = ("90683eac-48be-a806-a3fd-5e344e00c8a7", 96)
    # optimized_results = ("4f39aef6-d853-6575-9994-38d2f5dc1351", 37)

    # default_results = ("2664b55f-a824-670d-4879-764deb07b350", 1)
    # default_results = ("6049776b-c391-c37a-2c64-ac6d6b354da2", 9)
    # perform_t_test(optimized_results, default_results, "tripDuration")
    ########################



    # retrieved = db().get_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name="two-way-anova")
    # print(retrieved)
    #
    # start_anova(id=id)
    # start_two_sample_tests(id=id)