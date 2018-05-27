from oeda.databases import setup_experiment_database, db
from oeda.analysis.analysis_execution import start_t_test, start_anova



if __name__ == '__main__':
    setup_experiment_database("elasticsearch", "localhost", 9200)
    # t_test_id = "011d86bc-524f-645a-07c2-8b29d66b4ebd"

    id = "10d9a596-34ce-6341-4f8e-b65b1472f67b"
    # start_anova(id=id)
    start_t_test(id=id)