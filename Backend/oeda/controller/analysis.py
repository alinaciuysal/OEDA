from flask_restful import Resource
from oeda.databases import db
from oeda.analysis.analysis_execution import get_tuples
from flask import jsonify, request

class AnalysisController(Resource):

    @staticmethod
    def post(experiment_id):
        if experiment_id is None:
            return {"error": "experiment_id cannot be null"}, 404

        experiment = request.get_json()
        # as we only have one considered_data_type
        key = experiment["considered_data_types"][0]["name"]
        stage_ids, samples, knobs = get_tuples(experiment_id, key)

        # naming conventions
        test_name = "two-way-anova"
        test_results = {}
        res = db().get_analysis(experiment_id, stage_ids, test_name)
        test_results[test_name] = res

        resp = jsonify(res)
        resp.status_code = 200
        return resp