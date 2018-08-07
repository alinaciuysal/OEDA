from oeda.databases import setup_experiment_database, setup_user_database, db
from collections import defaultdict
from oeda.controller.stages import StageController as sc

import json
import os
import shutil
import numpy as np
from pprint import pprint as pp

# to calculate how much we are near/far away from default configurations of target systems in t-test
platooning_results = []
crowdnav_results = []


def delete_files(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


# https://stackoverflow.com/a/43034457
def percentage_change(final, initial):
    if initial != 0:
        return float(final - initial) / abs(initial) * 100
    else:
        return "undefined"


def add_to_ttest_results(target_system_type, steps_and_stages, last_step_number, direction):
    # first stage, the stage at index 0, is the result of default configuration, in db it's number is 1
    pp(steps_and_stages[last_step_number])
    default_config_results = float(steps_and_stages[last_step_number][0]["stage_result"])
    # second stage, the stage at index 1, is the result of optimizer configuration, in db it's number is 2
    optimizer_results = float(steps_and_stages[last_step_number][1]["stage_result"])
    res = percentage_change(optimizer_results, default_config_results)
    if direction == "Minimize":
        res = -1.0 * res

    if target_system_type == "Platooning":
        platooning_results.append(res)
    elif target_system_type == "CrowdNav":
        crowdnav_results.append(res)
    print("d: ", default_config_results, " opt: ", optimizer_results, " res: ", res)


if __name__ == '__main__':
    delete_files("./results")

    setup_experiment_database("elasticsearch", "localhost", 9200)
    experiment_ids = db().get_experiments()[0]

    nrOfExperiments = len(experiment_ids)

    nrOfPlatooningExperiments = 0
    passed_anova_platooning = 0
    passed_ttest_platooning = 0
    failed_anova_platooning = 0
    anova_size_error_platooning = 0
    failed_effect_size_platooning = 0
    failed_pvalue_platooning = 0
    failed_ttest_platooning = 0


    nrOfCrowdnavExperiments = 0
    passed_anova_crowdnav = 0
    passed_ttest_crowdnav = 0
    failed_anova_crowdnav = 0
    anova_size_error_crowdnav = 0
    failed_effect_size_crowdnav = 0
    failed_pvalue_crowdnav = 0
    failed_ttest_crowdnav = 0

    for exp_id in experiment_ids:
        experiment = db().get_experiment(exp_id)
        steps_and_stages = sc.get(experiment_id=exp_id)
        last_step_number = steps_and_stages.keys()[-1]

        file_name = str(experiment["name"]).split("Experiment #")[1][:2].rstrip() + "_"

        targetSystemId = experiment["targetSystemId"]
        ts = db().get_target(targetSystemId)

        direction = experiment["considered_data_types"][0]["criteria"]
        originalEffectSize = experiment["analysis"]["tTestEffectSize"]

        if "Platooning" in ts["name"]:
            file_name += "_Platooning_"
            nrOfPlatooningExperiments += 1

            try:
                anova = db().get_analysis(exp_id, 1, "two-way-anova")
                anova_eligible_for_bogp = anova["eligible_for_next_step"]
                if anova_eligible_for_bogp:
                    passed_anova_platooning += 1
                    t_test = db().get_analysis(exp_id, last_step_number, "t-test")
                    t_test_result = t_test["result"]
                    different_averages = t_test_result["different_averages"]
                    effect_size = t_test_result["effect_size"]
                    if direction == 'Maximize':
                        # significant and effect size is enough
                        if effect_size < -1.0 * originalEffectSize and different_averages:
                            passed_ttest_platooning += 1
                        # not significant but effect size is enough
                        elif effect_size < -1.0 * originalEffectSize and not different_averages:
                            failed_pvalue_platooning += 1
                        # significant but effect size is not enough
                        elif effect_size >= -1.0 * originalEffectSize and different_averages:
                            failed_effect_size_platooning += 1
                        # not significant and effect size is not enough
                        else:
                            failed_ttest_platooning += 1
                    else:
                        if effect_size > originalEffectSize and different_averages:
                            passed_ttest_platooning += 1
                        # not significant but effect size is enough
                        elif effect_size > originalEffectSize and not different_averages:
                            failed_pvalue_platooning += 1
                        # significant but effect size is not enough
                        elif effect_size <= originalEffectSize and different_averages:
                            failed_effect_size_platooning += 1
                        else:
                            failed_ttest_platooning += 1
                    add_to_ttest_results("Platooning", steps_and_stages, last_step_number, direction)
                else:
                    failed_anova_platooning += 1
            except:
                print("anova failed for Platooning Experiment # " + file_name)
                anova_size_error_platooning += 1

        elif "CrowdNav" in ts["name"]:
            file_name += "_CrowdNav_"
            nrOfCrowdnavExperiments += 1
            try:
                anova = db().get_analysis(exp_id, 1, "two-way-anova")
                anova_eligible_for_bogp = anova["eligible_for_next_step"]
                if anova_eligible_for_bogp:
                    passed_anova_crowdnav += 1
                    t_test = db().get_analysis(exp_id, last_step_number, "t-test")
                    t_test_result = t_test["result"]
                    different_averages = t_test_result["different_averages"]
                    effect_size = t_test_result["effect_size"]

                    if direction == 'Maximize':
                        if effect_size < -1.0 * originalEffectSize and different_averages:
                            passed_ttest_crowdnav += 1
                        elif effect_size < -1.0 * originalEffectSize and not different_averages:
                            failed_pvalue_crowdnav += 1
                        elif effect_size >= -1.0 * originalEffectSize and different_averages:
                            failed_effect_size_crowdnav += 1
                        else:
                            failed_ttest_crowdnav += 1
                    else:
                        if effect_size > originalEffectSize and different_averages:
                            passed_ttest_crowdnav += 1
                        elif effect_size > originalEffectSize and not different_averages:
                            failed_pvalue_crowdnav += 1
                        elif effect_size <= originalEffectSize and different_averages:
                            failed_effect_size_crowdnav += 1
                        else:
                            failed_ttest_crowdnav += 1
                    add_to_ttest_results("CrowdNav", steps_and_stages, last_step_number, direction)
                else:
                    failed_anova_crowdnav += 1
            except:
                print("anova failed for CrowdNav Experiment # " + file_name)
                anova_size_error_crowdnav += 1

        res = {}
        res["nrOfExperiments"] = nrOfExperiments
        res["platooning"] = {}
        res["platooning"]["anova"] = {}
        res["platooning"]["ttest"] = {}

        res["crowdnav"] = {}
        res["crowdnav"]["anova"] = {}
        res["crowdnav"]["ttest"] = {}

        res["platooning"]["nrOfExperiments"] = nrOfPlatooningExperiments
        res["platooning"]["anova"]["passed"] = passed_anova_platooning
        res["platooning"]["anova"]["failed"] = failed_anova_platooning
        res["platooning"]["anova"]["size_error"] = anova_size_error_platooning

        res["platooning"]["ttest"]["passed"] = passed_ttest_platooning
        res["platooning"]["ttest"]["failed"] = failed_ttest_platooning
        res["platooning"]["ttest"]["effect_size"] = failed_effect_size_platooning
        res["platooning"]["ttest"]["pvalue"] = failed_pvalue_platooning

        res["crowdnav"]["nrOfExperiments"] = nrOfCrowdnavExperiments
        res["crowdnav"]["anova"]["passed"] = passed_anova_crowdnav
        res["crowdnav"]["anova"]["failed"] = failed_anova_crowdnav
        res["crowdnav"]["anova"]["size_error"] = anova_size_error_crowdnav

        res["crowdnav"]["ttest"]["passed"] = passed_ttest_crowdnav
        res["crowdnav"]["ttest"]["failed"] = failed_ttest_crowdnav
        res["crowdnav"]["ttest"]["effect_size"] = failed_effect_size_crowdnav
        res["crowdnav"]["ttest"]["pvalue"] = failed_pvalue_crowdnav

        with open('./results/overall.json', 'w') as outfile:
            json.dump(res, outfile, sort_keys=False, indent=4, ensure_ascii=False)

        ttest_results = {}
        ttest_results["platooning"] = {}
        ttest_results["platooning"]["results"] = platooning_results
        ttest_results["platooning"]["avg"] = np.average(platooning_results)

        ttest_results["crowdnav"] = {}
        ttest_results["crowdnav"]["results"] = crowdnav_results
        ttest_results["crowdnav"]["avg"] = np.average(crowdnav_results)

        with open('./results/ttest.json', 'w') as outfile2:
            json.dump(ttest_results, outfile2, sort_keys=False, indent=4, ensure_ascii=False)

        # file_name += str(experiment["executionStrategy"]["sample_size"]) + "_"
        # file_name += str(experiment["executionStrategy"]["stages_count"]) + "_"
        # file_name += str(experiment["analysis"]["data_type"]["name"])
        #
        # out_json = {}
        # out_json["experiment"] = experiment
        # stage_ids, stages = db().get_stages(exp_id)
        # stages = sorted(stages, key=lambda k: k['stage_result'])
        # out_json["stages"] = stages
        # with open('./results/' + file_name + '.json', 'w') as outfile:
        #     json.dump(out_json, outfile, sort_keys=True, indent=4, ensure_ascii=False)