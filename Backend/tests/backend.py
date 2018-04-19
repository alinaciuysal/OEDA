from oeda.rtxlib.executionstrategy.__init__ import run_execution_strategy
from oeda.databases import setup_experiment_database
from oeda.rtxlib.workflow import execute_workflow
from uuid import uuid4
from oeda.service.rtx_definition import RTXDefinition
from random import randint
from threading import Event
from oeda.service.execution_scheduler import oeda_callback
from oeda.databases import db

import os.path
import json
import io

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
def create_experiment(strategy_name, sample_size, knobs, acquisition_method="ei", optimizer_iterations=10, optimizer_iterations_in_design=6):
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


def adjust_functions_and_weights(incoming_data_types):
    considered_data_types = []
    for dt in incoming_data_types:
        if dt["name"] == "overhead":
            dt["is_considered"] = True
            dt["weight"] = 50
            dt["aggregateFunction"] = "avg"
            considered_data_types.append(dt)
        elif dt["name"] == "complaint":
            dt["is_considered"] = True
            dt["weight"] = 50
            dt["aggregateFunction"] = "ratio-True"
            considered_data_types.append(dt)
    return considered_data_types


def create_rtx_definition(experiment, target):
    wf = RTXDefinition(oeda_experiment=experiment, oeda_target=target, oeda_callback=oeda_callback, oeda_stop_request=Event())
    return wf


def get_available_target():
    targets, contents = db().get_targets()
    for target in contents:
        if target["status"] == "READY":
            return target


if __name__ == '__main__':
    data_providers = parse_config("dataProviders")
    default_variables = parse_config("knobs")
    setup_experiment_database("elasticsearch", "localhost", "9200")

    experiment_knobs = dict(
        route_random_sigma=(0, 0.2),
        exploration_percentage=(2, 2.7)
    )
    experiment = create_experiment(strategy_name="mlr_mbo", sample_size=20, knobs=experiment_knobs, acquisition_method="ei")
    old_experiment_id = experiment["id"]

    target = create_target_system(experiment=experiment, data_providers=data_providers, default_variables=default_variables, ignore_first_n_samples=30)
    old_target_id = target["id"]
    experiment["targetSystemId"] = old_target_id

    db().save_target(target["id"], target)
    db().save_experiment(experiment["id"], experiment)
    #
    experiment["id"] = old_experiment_id
    target["id"] = old_target_id
    #
    wf = create_rtx_definition(experiment=experiment, target=target)
    execute_workflow(wf)
    run_execution_strategy(wf)
