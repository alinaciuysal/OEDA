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
        key = experiment["analysis"]["data_type"]

        # naming conventions
        if experiment["analysis"]["type"] == 'anova':
            test_name = "anova"
        elif experiment["analysis"]["type"] == 't_test':
            test_name = "t-test"
        elif experiment["analysis"]["type"] == 'no_analysis':
            return {"error": "Analysis was not specified for this experiment"}, 404
        elif experiment["analysis"]["type"] == 'bayesian_opt':
            return {"error": "Analysis was not specified for bayesian optimization"}, 404

        stage_ids, samples, knobs = get_tuples(experiment_id, key)
        res = db().get_analysis(experiment_id, stage_ids, test_name)
        resp = jsonify(res)
        resp.status_code = 200
        return resp