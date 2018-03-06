from oeda.rtxlib.executionstrategy.MlrStrategy import start_mlr_mbo_strategy
import numpy as np
from uuid import uuid4

from oeda.service.rtx_definition import RTXDefinition
from glob import glob
from random import randint
import os.path
import json


def parse_crowd_nav_config():
    pattern = os.path.join('../oeda/crowdnav_config', '*.json')
    arr = []
    for file_name in glob(pattern):
        with open(file_name) as file:
            json_object = json.load(file)
            if str(file_name).find("dataProviders"):
                arr.append(json_object)
            elif str(file_name).find("knobs"):
                arr.append(json_object)
    return arr


# usable strategy_name = sequential, self_optimizer, uncorrelated_self_optimizer, step_explorer, forever, random, mlr
def create_experiment_tuple(strategy_name, sample_size, knobs, optimizer_iterations=5, optimizer_random_starts=3):
    num = randint(0, 25)
    experiment_id=str(uuid4())
    experiment = dict(
        id=experiment_id,
        name="test_experiment_" + str(num),
        description="test_description_" + str(num),
        optimized_data_types=["overhead"],
        executionStrategy=dict(
            type=strategy_name,
            sample_size=sample_size,
            knobs=knobs,
            optimizer_iterations=optimizer_iterations,
            optimizer_random_starts=optimizer_random_starts
        )
    )
    return experiment


def create_rtx_definition(dataProviders, config_knobs, experiment, ignore_first_n_samples):
    target = dict(
        primaryDataProvider=dict(),
        secondaryDataProviders=[],
        changeProvider=dict(
            kafka_uri="kafka:9092",
            topic="crowd-nav-commands",
            serializer="JSON",
            type="kafka_producer"
        ),
        incomingDataTypes=[]
    )
    for dp in dataProviders:
        if dp["name"] == "Trips":
            target["primaryDataProvider"] = dp
            target["primaryDataProvider"]["ignore_first_n_samples"] = ignore_first_n_samples
        else:
            target["secondaryDataProviders"].append(dp)
        target["incomingDataTypes"].append(dp["incomingDataTypes"])

    wf = RTXDefinition(oeda_experiment=experiment, oeda_target=target, oeda_callback=dict(), oeda_stop_request=None)
    print(wf)
    # wf["execution_strategy"]["sample_size"] = 50
    # wf["execution_strategy"]["knobs"]["route_random_sigma"] = (0, 0.3)
    # wf["execution_strategy"]["knobs"]["exploration_percentage"] = (1, 1.7)
    start_mlr_mbo_strategy(wf)


if __name__ == '__main__':
    knobs = dict(
        route_random_sigma=(0, 0.3),
        exploration_percentage=(1, 1.7)
    )
    experiment = create_experiment_tuple(strategy_name="mlr", sample_size=20, knobs=knobs)
    dataProviders, config_knobs = parse_crowd_nav_config()
    create_rtx_definition(dataProviders, config_knobs, experiment, 30)
