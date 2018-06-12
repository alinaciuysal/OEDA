from flask_restful import Resource
from oeda.databases import db


class StageController(Resource):

    @staticmethod
    def get(experiment_id, step_no):
        stage_ids, stages = db().get_stages(experiment_id=experiment_id, step_no=step_no)
        new_stages = stages
        i = 0
        for _ in stages:
            new_stages[i]["id"] = stage_ids[i]
            new_stages[i]["knobs"] = _["knobs"]
            i += 1
        return new_stages
