from oeda.databases import setup_experiment_database, db
from oeda.rtxlib.workflow import execute_workflow
from oeda.service.rtx_definition import RTXDefinition
from threading import Event
from oeda.controller.callback import set_dict as set_dict
from oeda.service.execution_scheduler import set_experiment_status
from oeda.service.execution_scheduler import set_target_system_status
from oeda.utilities.TestUtility import parse_config, create_experiment, create_target_system


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

# this function/script can run independently & locally, just set stand_alone flag to True or False.
# Assuming that actual server is running in the background locally:
# set stand_alone to False if you want to see the whole process information in the console & UI
# set it to True, if you want only to see final results of stages in the console
def initiate(stand_alone=True):
    setup_experiment_database("elasticsearch", "localhost", "9200")
    # clear database
    # db().clear_db()

    data_providers = parse_config(["oeda", "config", "crowdnav_config"], "dataProviders")
    default_variables = parse_config(["oeda", "config", "crowdnav_config"], "knobs")

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

    if stand_alone:
        rtx_execution(experiment=experiment, target=target)
    # with this returned experiment tuple, we can retrieve required information for tests easily
    return experiment

if __name__ == '__main__':
    initiate()