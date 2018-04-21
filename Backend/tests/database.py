from oeda.databases import db
from oeda.databases import setup_experiment_database

if __name__ == '__main__':
    # setup_experiment_database("elasticsearch", "localhost", "9200")
    # mock = db()
    # exps = mock.get_experiments()
    # experiment_id = exps[0][len(exps[0]) - 1] # get latest experiment
    # print(experiment_id)
    # stage_no = 1
    # aggs_1 = mock.get_aggregation(experiment_id=experiment_id, stage_no=stage_no, aggregation_name="stats", field="overhead")
    # print(aggs_1)
    # count = mock.get_count(experiment_id=experiment_id, stage_no=stage_no, field="complaint", value=1)
    # total = mock.get_aggregation(experiment_id=experiment_id, stage_no=stage_no, aggregation_name="stats", field="complaint")["count"]
    # print(count)
    # print(total)
    # data = mock.get_data_points(experiment_id=experiment_id, stage_no=stage_no)
    # print(data)
    exit(1)