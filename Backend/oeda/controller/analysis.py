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
        test_names = []
        if experiment["analysis"]["type"] == 'factorial_tests':
            test_names = ["two-way-anova"]

        elif experiment["analysis"]["type"] == 'two_sample_tests':
            test_names = ["t-test", "t-test-power", "t-test-sample-estimation"]

        elif experiment["analysis"]["type"] == 'one_sample_tests':
            test_names = ["dagostino-pearson", "anderson-darling", "kolmogorov-smirnov", "shapiro-wilk"]

        elif experiment["analysis"]["type"] == 'n_sample_tests':
            test_names = ["one-way-anova", "kruskal-wallis", "levene", "bartlett", "fligner-killeen"]

        elif experiment["analysis"]["type"] == 'no_analysis':
            return {"error": "Analysis was not specified for this experiment"}, 404

        elif experiment["analysis"]["type"] == 'bayesian_opt':
            return {"error": "Analysis was not specified for bayesian optimization"}, 404

        stage_ids, samples, knobs = get_tuples(experiment_id, key)

        test_results = {}
        for test_name in test_names:
            res = db().get_analysis(experiment_id, stage_ids, test_name)
            test_results[test_name] = res

        resp = jsonify(test_results)
        resp.status_code = 200
        return resp