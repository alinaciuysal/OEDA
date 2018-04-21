from oeda.databases import setup_experiment_database
from oeda.rtxlib.workflow import execute_workflow
from uuid import uuid4
from oeda.service.rtx_definition import RTXDefinition
from random import randint
from threading import Event
from oeda.controller.callback import set_dict as set_dict
from oeda.databases import db
from oeda.service.execution_scheduler import set_experiment_status
from oeda.service.execution_scheduler import set_target_system_status


import os.path
import json
import io
import copy

def parse_config(given_file_name):
    goal_dir = os.path.join(os.getcwd(), "..", "oeda", "config", "crowdnav_config")
    real_dir = os.path.realpath(goal_dir)
    json_object = {}
    for root, dirs, files in os.walk(real_dir):
        for file_name in files:
            if file_name.endswith('.json') and given_file_name in file_name:
                json_file_path = os.path.join(real_dir, file_name)
                with io.open(json_file_path, 'r', encoding='utf8') as json_data:
                    d = json.load(json_data)
                    json_object = d
    return json_object


# usable strategy_name = sequential, self_optimizer, uncorrelated_self_optimizer, step_explorer, forever, random, mlr_mbo
def create_experiment(strategy_name, sample_size, knobs, optimizer_iterations_in_design, acquisition_method="ei", optimizer_iterations=5):
    num = randint(0, 100)
    id = str(uuid4())
    experiment = dict(
        id=id,
        name="test_experiment_" + str(num),
        description="test_experiment_" + str(num),
        considered_data_types=[],
        changeableVariables=[],
        executionStrategy=dict(
            type=strategy_name,
            sample_size=sample_size,
            knobs=knobs
        )
    )
    if strategy_name in ["self_optimizer", "uncorrelated_self_optimizer", "mlr_mbo"]:
        experiment["executionStrategy"]["optimizer_iterations"] = optimizer_iterations
        experiment["executionStrategy"]["optimizer_iterations_in_design"] = optimizer_iterations_in_design
    if strategy_name == "mlr_mbo":
        experiment["executionStrategy"]["acquisition_method"] = acquisition_method
    return experiment


def create_target_system(experiment, data_providers, default_variables, ignore_first_n_samples):
    num = randint(0, 100)
    id = str(uuid4())
    target = dict(
        id=id,
        name="test_target_" + str(num),
        description="test_target_" + str(num),
        status="READY",
        dataProviders=data_providers,
        primaryDataProvider=dict(),
        secondaryDataProviders=[],
        changeProvider=dict(
            kafka_uri="kafka:9092",
            topic="crowd-nav-commands",
            serializer="JSON",
            type="kafka_producer"
        ),
        incomingDataTypes=[],
        defaultVariables=default_variables,
        changeableVariables=default_variables
    )
    for dp in data_providers:
        if dp["name"] == "Trips":
            dp["is_primary"] = True
            target["primaryDataProvider"] = dp
            target["primaryDataProvider"]["ignore_first_n_samples"] = ignore_first_n_samples
            considered_data_types = adjust_functions_and_weights(dp["incomingDataTypes"])
            experiment["considered_data_types"] = considered_data_types
        else:
            target["secondaryDataProviders"].append(dp)

        for data_type in dp["incomingDataTypes"]:
            target["incomingDataTypes"].append(data_type)

    for var in default_variables:
        if var["name"] == "route_random_sigma" or var["name"] == "max_speed_and_length_factor":
            experiment["changeableVariables"].append(var)
    return target

# this function can be agjusted to select different data providers
# deep copy is needed because otherwise incoming_data_types is modified (which is not the desired behavior)
def adjust_functions_and_weights(incoming_data_types):
    dict2 = copy.deepcopy(incoming_data_types)
    considered_data_types = []
    for data_type in dict2:
        if data_type["name"] == "overhead":
            data_type["is_considered"] = True
            data_type["weight"] = 99
            data_type["aggregateFunction"] = "avg"
            considered_data_types.append(data_type)
        elif data_type["name"] == "complaint":
            data_type["is_considered"] = True
            data_type["weight"] = 1
            data_type["aggregateFunction"] = "ratio-True"
            considered_data_types.append(data_type)
        # elif data_type["name"] == "minimalCosts":
        #     data_type["is_considered"] = True
        #     data_type["weight"] = 5
        #     data_type["aggregateFunction"] = "max"
        #     considered_data_types.append(data_type)
    return considered_data_types


def get_available_targets():
    targets, contents = db().get_targets()
    for target in contents:
        if target["status"] == "READY":
            return target

def oeda_callback(dictionary, experiment_id):
    """"Custom callback that RTX uses to update us with experiment progress information"""
    set_dict(dictionary, experiment_id)

def rtx_execution(experiment, target):
    set_experiment_status(experiment["id"], "RUNNING")
    set_target_system_status(experiment["targetSystemId"], "WORKING")
    set_dict(experiment["id"], None)
    wf = RTXDefinition(oeda_experiment=experiment, oeda_target=target, oeda_callback=oeda_callback, oeda_stop_request=Event())
    execute_workflow(wf)
    set_experiment_status(experiment["id"], "SUCCESS")
    set_target_system_status(experiment["targetSystemId"], "READY")

if __name__ == '__main__':
    setup_experiment_database("elasticsearch", "localhost", "9200")
    # clear database
    db().clear_db()

    data_providers = parse_config("dataProviders")
    default_variables = parse_config("knobs")


    experiment_knobs = dict(
        route_random_sigma=(0, 0.2),
        exploration_percentage=(2, 2.7)
    )
    experiment = create_experiment(strategy_name="mlr_mbo", sample_size=20, knobs=experiment_knobs, optimizer_iterations_in_design=len(experiment_knobs)*4, acquisition_method="ei")
    old_experiment_id = experiment["id"]

    target = create_target_system(experiment=experiment, data_providers=data_providers, default_variables=default_variables, ignore_first_n_samples=30)
    old_target_id = target["id"]
    experiment["targetSystemId"] = old_target_id

    db().save_target(target["id"], target)
    db().save_experiment(experiment["id"], experiment)

    experiment["id"] = old_experiment_id
    target["id"] = old_target_id
    # Assuming that server is running in the background, set this to False if you want to see the whole process information in the console & UI
    # With True flag, it executes the experiment again in the background, but only final results of stages are shown
    stand_alone = False
    if stand_alone:
        rtx_execution(experiment=experiment, target=target)