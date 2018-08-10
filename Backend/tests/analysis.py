from oeda.databases import setup_experiment_database, setup_user_database, db
from collections import defaultdict
from oeda.analysis.factorial_tests import FactorialAnova
from oeda.analysis.one_sample_tests import ShapiroWilk, AndersonDarling, DAgostinoPearson, KolmogorovSmirnov
from oeda.analysis.two_sample_tests import Ttest
import statsmodels.api as sm
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import json
import os
import shutil
import errno
import itertools
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pprint
pp = pprint.PrettyPrinter(indent=4)


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
    crowdnav_different_averages = []
    crowdnav_not_different_averages = []
    crowdnav_exp_names = []

    platooning_different_averages = []
    platooning_not_different_averages = []
    platooning_exp_names = []

    for experiment in experiments:
        if "Default" in experiment["name"] and experiment["executionStrategy"]["type"] == "sequential":
            if str(experiment["status"]) != "RUNNING" and str(experiment["status"]) != "ERROR":
                data_type = experiment["analysis"]["data_type"]["name"]
                sample_size = str(experiment["executionStrategy"]["sample_size"])
                if data_type != 'complaint' and data_type != 'tripDuration':
                    file_name = str(experiment["name"]).split("Default Run with ")[1] + "_"
                    file_name += sample_size + "_"
                    file_name += data_type
                    different_averages = 0
                    not_different_averages = 0
                    inner_index = 0

                    out_json = {}
                    out_json["fn"] = file_name
                    out_json["experiment"] = experiment
                    out_json["ttest"] = {}

                    targetSystemId = experiment["targetSystemId"]
                    ts = db().get_target(targetSystemId)
                    stage_ids, samples, knobs = get_tuples(experiment["id"], data_type)
                    # perform two-sample-tests
                    combinations = list(itertools.combinations(stage_ids, 2))

                    for comb in combinations:
                        inner_index += 1
                        stage_id_1 = comb[0]
                        stage_id_idx_1 = stage_ids.index(stage_id_1)
                        data_points_1 = samples[stage_id_idx_1]

                        stage_id_2 = comb[1]
                        stage_id_idx_2 = stage_ids.index(stage_id_2)
                        data_points_2 = samples[stage_id_idx_2]

                        pp_x = sm.ProbPlot(np.asarray(data_points_1))
                        pp_y = sm.ProbPlot(np.asarray(data_points_2))
                        fig1 = sm.qqplot_2samples(pp_x, pp_y, line='r')

                        if "Platooning" in ts["name"]:
                            fig1.savefig("./results/default/platooning/" + file_name + "_" + str(inner_index) + ".png", format='png')
                        elif "CrowdNav" in ts["name"]:
                            fig1.savefig("./results/default/crowdnav/" + file_name + "_" + str(inner_index) + ".png", format='png')
                        plt.close('all')

                        test1 = Ttest(stage_ids=[stage_id_1, stage_id_2], y_key=data_type, alpha=alpha)
                        result = test1.run(data=[data_points_1, data_points_2], knobs=knobs)
                        if result["effect_size"] > 0.2 and result["different_averages"] == True:
                            different_averages += 1
                            print("different", file_name, str(inner_index))
                        else:
                            not_different_averages += 1


                    # print("exp_name:", file_name, " different_averages:", different_averages, "not_different_averages", not_different_averages)

                    if "Platooning" in ts["name"]:
                        platooning_different_averages.append(different_averages)
                        platooning_not_different_averages.append(not_different_averages)
                        platooning_exp_names.append(file_name)

                    elif "CrowdNav" in ts["name"]:
                        crowdnav_different_averages.append(different_averages)
                        crowdnav_not_different_averages.append(not_different_averages)
                        crowdnav_exp_names.append(file_name)

        platooning_results = {}
        platooning_results["different_averages"] = platooning_different_averages
        platooning_results["not_different_averages"] = platooning_not_different_averages
        platooning_results["exp_names"] = platooning_exp_names
        with open('./results/default/platooning/results.json', 'w') as outfile:
            json.dump(platooning_results, outfile, sort_keys=True, indent=4, ensure_ascii=False)

        crowdnav_results = {}
        crowdnav_results["different_averages"] = crowdnav_different_averages
        crowdnav_results["not_different_averages"] = crowdnav_not_different_averages
        crowdnav_results["exp_names"] = crowdnav_exp_names
        with open('./results/default/crowdnav/results.json', 'w') as outfile2:
            json.dump(crowdnav_results, outfile2, sort_keys=True, indent=4, ensure_ascii=False)


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


def draw_box_plot(incoming_data_type_name, x_values, y_values, ts_name):
    # Create a figure instance
    fig = plt.figure(1, figsize=(9, 6))
    # Create an axes instance
    ax = fig.add_subplot(111)

    # Create the boxplot & format it
    format_box_plot(ax, y_values)

    ax.set_title('Boxplots of optimizer and default runs')
    ax.set_ylabel(incoming_data_type_name)
    ax.set_xlabel("Stage Numbers of Different Experiments")

    # Custom x-axis labels for respective samples
    ax.set_xticklabels(x_values)

    # Remove top axes and right axes ticks
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()

    median_legend = mlines.Line2D([], [], color='green', marker='^', linestyle='None',
                                  markersize=5, label='Mean')

    mean_legend = mpatches.Patch(color='red', label='Median')

    plt.legend(handles=[median_legend, mean_legend])
    plot_path = './results/' + str(ts_name).lower() + '/best_' + str(incoming_data_type_name) + ".png"
    plt.savefig(plot_path, bbox_inches='tight', format='png')
    plt.close()


# http://blog.bharatbhole.com/creating-boxplots-with-matplotlib/
def format_box_plot(ax, y_values):
    bp = ax.boxplot(y_values, showmeans=True, showfliers=False)
    for median in bp['medians']:
        median.set_color('red')
    ## change the style of means and their fill
    for mean in bp['means']:
        mean.set_color('green')


def draw_box_plots_of_three_experiments(optimized_results, default_results, y_key, ts_name):
    y_values = []
    x_values = []

    for r1 in optimized_results:
        experiment_id, stage_no = r1
        data_points = db().get_data_points(experiment_id, stage_no)
        only_data = [d["payload"][y_key] for d in data_points]
        y_values.append(only_data)
        x_values.append("(Optimizer) " + str(stage_no))

    for r_default in default_results:
        default_experiment_id, default_stage_no = r_default
        data_points_3 = db().get_data_points(default_experiment_id, default_stage_no)
        default_data_3 = [d["payload"][y_key] for d in data_points_3]
        y_values.append(default_data_3)
        x_values.append("(Default) " + str(default_stage_no))



    draw_box_plot(y_key, x_values, y_values, ts_name)


def perform_t_test(optimized_results, default_results, y_key, alpha=0.05):
    experiment_id, stage_no = optimized_results
    stage_id = str(experiment_id) + "#" + str(stage_no)
    default_experiment_id, default_stage_no = default_results
    default_stage_id = str(experiment_id) + "#" + str(default_stage_no)

    data_points_1 = db().get_data_points(experiment_id, stage_no)
    only_data_1 = [d["payload"][y_key] for d in data_points_1]

    data_points_2 = db().get_data_points(default_experiment_id, default_stage_no)
    only_data_2 = [d["payload"][y_key] for d in data_points_2]

    test1 = Ttest(stage_ids=[stage_id, default_stage_id], y_key=y_key, alpha=alpha)
    result = test1.run(data=[only_data_1, only_data_2], knobs=None)

    avg_1 = np.mean(only_data_1)
    avg_default = np.mean(only_data_2)
    print(avg_1, avg_default)
    opt_percentage = -1.0 * percentage_change(avg_1, avg_default)
    result["opt_percentage"] = opt_percentage
    print(result)


def convert_time_difference_to_mins(tstamp1, tstamp2):
    if tstamp1 > tstamp2:
        td = tstamp1 - tstamp2
    else:
        td = tstamp2 - tstamp1
    td_mins = int(round(td.total_seconds() / 60))
    return td_mins


def get_results_of_optimization(tpl):
    experiment_id, stage_number = tpl
    experiment = db().get_experiment(experiment_id)
    stages_count = experiment["executionStrategy"]["stages_count"]

    first_stage_data = db().get_data_points(experiment_id, 1)
    first_timestamp = first_stage_data[0]["createdDate"]
    first_date = datetime.strptime(first_timestamp, "%Y-%m-%d %H:%M:%S.%f")

    last_stage_data = db().get_data_points(experiment_id, stages_count)
    last_timestamp = last_stage_data[len(last_stage_data) - 1]["createdDate"]
    last_date = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S.%f")
    print(first_date, last_date)

    diff = convert_time_difference_to_mins(first_date, last_date)
    print(diff)


def percentage_change(optimized, default):
    if default != 0:
        return float(optimized - default) / abs(default) * 100
    else:
        return "undefined"


def flush_stage_results(tpl, y_key, ts_name):
    experiment_id, stage_number = tpl
    experiment = db().get_experiment(experiment_id)
    pp.pprint(experiment)
    stage_data = db().get_data_points(experiment_id, stage_number)
    pp.pprint(stage_data)
    stages_count = experiment["executionStrategy"]["stages_count"]
    sample_size = experiment["executionStrategy"]["sample_size"]
    out_json = {}
    out_json["experiment"] = experiment
    out_json["stage_data"] = stage_data
    with open('./results/' + str(ts_name).lower() + '/best_' + str(sample_size) + "_" + str(stages_count) + "_" + str(y_key) + '.json', 'w') as outfile:
        json.dump(out_json, outfile, sort_keys=False, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    setup_experiment_database("elasticsearch", "localhost", 9200)
    experiments = db().get_experiments()[1]
    # get_non_default_config_results(experiments)

    get_default_config_results(experiments)
    # draw_default_config_results(experiments, "overhead", "Platooning")
    # draw_default_config_results(experiments, "fuelConsumption", "Platooning")

    ########################
    # crowd-nav avg overhead
    # optimized_results_1 = ("6b5776ab-1d3d-5bdf-a77a-46bb40e61afc", 93)
    # optimized_results_2 = ("5743e5b2-5545-3a9a-4d27-25a3b68771d2", 27)
    # get_results_of_optimization(optimized_results_1)
    # flush_stage_results(optimized_results_1, "overhead", "CrowdNav")

    # default_results_1 = ("6a916c78-f122-bb2c-c93f-f2304c4cb8bc", 8)
    # default_results_2 = ("e731c263-a5f2-ed44-587d-cd1c98b30aae", 4)
    # default_results_3 = ("317fe993-6186-9efa-2730-aaaa50b0d490", 2)
    # perform_t_test(optimized_results, default_results, "overhead")
    # draw_box_plots_of_three_experiments([optimized_results_1, optimized_results_2], [default_results_1, default_results_2, default_results_3], "overhead", "CrowdNav")
    ########################

    ########################
    # platooning avg overhead
    # optimized_results_1 = ("e01777c1-883e-97c7-b123-0cd32a1a1d85", 81)
    # optimized_results_2 = ("cb53c88d-5a47-b61e-9080-3806293b6457", 34)
    # get_results_of_optimization(optimized_results)
    # flush_stage_results(optimized_results, "overhead", "Platooning")

    # default_results_1 = ("a2f7025b-0899-a207-98dd-daeebaab8b6d", 1)
    # default_results_2 = ("44cc33e4-6eea-b655-82c4-967c8c08b7f5", 8)
    # default_results_3 = ("65d8866f-37e1-e627-fd59-64a661874e2c", 9)
    # perform_t_test(optimized_results, default_results, "overhead")
    # draw_box_plots_of_three_experiments([optimized_results_1, optimized_results_2], [default_results_1, default_results_2, default_results_3], "overhead", "Platooning")

    ########################

    ########################
    # platooning avg fuelConsumption
    # optimized_results_1 = ("a65da561-1938-eb8a-b82a-d5c8d5a8b81c", 62)
    # optimized_results_2 = ("446dd6db-99ba-3f79-7d2e-3abb452b7542", 19)
    # flush_stage_results(optimized_results, "fuelConsumption", "Platooning")

    # get_results_of_optimization(optimized_results)
    # default_results_1 = ("77f422b8-1ded-7d5b-9c33-5f44cbfd64e2", 6)
    # default_results_2 = ("d35c17ac-9252-ec76-a511-ed3289a1ce0a", 4)
    # perform_t_test(optimized_results, default_results, "fuelConsumption")
    # draw_box_plots_of_three_experiments([optimized_results_1, optimized_results_2], [default_results_1, default_results_2], "fuelConsumption", "Platooning")
    ########################

    ########################
    # platooning avg tripDuration
    # optimized_results_1 = ("90683eac-48be-a806-a3fd-5e344e00c8a7", 96)
    # optimized_results_2 = ("4f39aef6-d853-6575-9994-38d2f5dc1351", 37)
    # flush_stage_results(optimized_results, "tripDuration", "Platooning")

    # get_results_of_optimization(optimized_results)
    # default_results_1 = ("2664b55f-a824-670d-4879-764deb07b350", 1)
    # default_results_2 = ("6049776b-c391-c37a-2c64-ac6d6b354da2", 9)
    # perform_t_test(optimized_results, default_results, "tripDuration")
    # draw_box_plots_of_three_experiments([optimized_results_1, optimized_results_2], [default_results_1, default_results_2], "tripDuration", "Platooning")
    ########################



    # retrieved = db().get_analysis(experiment_id=id, stage_ids=stage_ids, analysis_name="two-way-anova")
    # print(retrieved)
    #
    # start_anova(id=id)
    # start_two_sample_tests(id=id)