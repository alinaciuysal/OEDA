from flask import jsonify
from flask_restful import Resource
import oeda.controller.stages as sc
from oeda.databases import db
import json as json
import traceback
from oeda.controller.experiment_results import get_all_stage_data
import oeda.controller.callback as cb # callback

class RunningAllStageResultsWithExperimentIdController(Resource):

    @staticmethod
    def get(experiment_id, step_no, timestamp):
        """ first gets all stages of given experiment, then concats all data to a single tuple """
        try:
            if step_no is None:
                return {"error": "step_no should not be null"}, 404

            if timestamp is None:
                return {"error": "timestamp should not be null"}, 404

            if timestamp == "-1":
                resp = jsonify(get_all_stage_data(experiment_id, step_no))
                resp.status_code = 200
                return resp

            all_stage_data = get_all_stage_data_after(experiment_id, timestamp)
            resp = jsonify(all_stage_data)
            resp.status_code = 200
            return resp
        except Exception as e:
            tb = traceback.format_exc()
            print(tb)
            return {"error": e.message}, 404


def get_all_stage_data_after(experiment_id, step_no, timestamp):
    all_stage_data = []
    new_stages = sc.StageController.get(experiment_id=experiment_id, step_no=step_no)
    for stage in new_stages:
        data = db().get_data_points_after(experiment_id=experiment_id, step_no=step_no, stage_no=stage['number'], timestamp=timestamp)
        # wrap the stage data with stage number if there are some data points
        if len(data) != 0:
            stage_and_data = {
                "knobs": stage["knobs"],
                "number": stage["number"],
                "values": data
            }
            json_data = json.dumps(stage_and_data)
            all_stage_data.append(json_data)
    return all_stage_data

# returns wf._oedaCallback via API
class OEDACallbackController(Resource):

    @staticmethod
    def get(experiment_id):
        try:
            if experiment_id is None:
                return {"error": "experiment_id should not be null"}, 404

            if cb.get_dict(experiment_id) is None:
                resp = jsonify({"status": "PROCESSING", "message": "OEDA callback for this experiment has not been processed yet..."})
            else:
                # should return the dict after callback is received
                resp = jsonify(cb.get_dict(experiment_id))

            resp.status_code = 200
            return resp

        except Exception as e:
            tb = traceback.format_exc()
            print(tb)
            return {"error": e.message}, 404