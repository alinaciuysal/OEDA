from oeda.rtxlib.executionstrategy.MlrStrategy import start_mlr_mbo_strategy
from uuid import uuid4

from oeda.service.rtx_definition import RTXDefinition
from glob import glob
from random import randint
import os.path
import json


def parse_crowd_nav_config():
    pattern = os.path.join('../oeda/config/crowdnav_config', '*.json')
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
def create_experiment_tuple(strategy_name, sample_size, knobs, acquisition_method, optimizer_iterations=15, optimizer_iterations_in_design=6):
    num = randint(0, 25)
    id = str(uuid4())
    experiment = dict(
        id=id,
        name="test_experiment_" + str(num),
        description="test_description_" + str(num),
        optimized_data_types=["overhead"],
        executionStrategy=dict(
            type=strategy_name,
            sample_size=sample_size,
            knobs=knobs,
            acquisition_method=acquisition_method,
            optimizer_iterations=optimizer_iterations,
            optimizer_iterations_in_design=optimizer_iterations_in_design
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
    start_mlr_mbo_strategy(wf)


if __name__ == '__main__':
    knobs = dict(
        route_random_sigma=(0, 0.2),
        exploration_percentage=(2, 2.7)
    )
    # knobs = dict(
    #     route_random_sigma=(1.5, 2.5),
    # )
    experiment = create_experiment_tuple(strategy_name="mlr_mbo", sample_size=20, knobs=knobs, acquisition_method="ei")
    dataProviders, config_knobs = parse_crowd_nav_config()
    create_rtx_definition(dataProviders, config_knobs, experiment, 30)
