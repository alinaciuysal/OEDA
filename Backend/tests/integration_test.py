from oeda.databases.__init__ import setup_experiment_database, db
from oeda.rtxlib.dataproviders.__init__ import createInstance
from oeda.utilities.TestUtility import parse_config, create_experiment
from oeda.config.R_config import Config
from oeda.log import *
from tests.backend import initiate

import requests
import unittest

# Sim. systems should be running in the background
# names of test cases are important
# see https://stackoverflow.com/questions/5387299/python-unittest-testcase-execution-order/5387956#5387956 and
# https://docs.python.org/2/library/unittest.html#unittest.TestLoader.sortTestMethodsUsing
class IntegrationTest(unittest.TestCase):
    experiment = None
    stage_ids = None

    for_tests = True
    # docker without http authentication can be used
    # elasticsearch_ip = "192.168.99.100"
    elasticsearch_ip = None
    elasticsearch_port = None

    def setUp(self):
        config = parse_config(["oeda", "databases"], "experiment_db_config")
        self.assertTrue(config)
        self.assertTrue(config["host"])
        self.assertTrue(config["port"])
        IntegrationTest.elasticsearch_ip = str(config["host"])
        IntegrationTest.elasticsearch_port = str(config["port"])
        setup_experiment_database("elasticsearch", IntegrationTest.elasticsearch_ip, IntegrationTest.elasticsearch_port, for_tests=IntegrationTest.for_tests)

    def test_db(self):
        es = db().get_instance()
        health = es.cluster.health()
        # yellow means that the primary shard is allocated but replicas are not
        # and green means that all shards are allocated
        self.assertEqual('yellow', health["status"])

    # use a regular http GET request
    def test_db_2(self):
        res = requests.get("http://" + IntegrationTest.elasticsearch_ip + ":" + IntegrationTest.elasticsearch_port).json()
        self.assertTrue(res["cluster_name"])
        self.assertTrue(res["cluster_uuid"])

    # as we're only using crowdnav_config for now,
    # make sure right values have been set in dataProviders.json file under oeda/crowdnav_config folder
    # also you need to add 127.0.0.1 kafka entry to /etc/hosts file because we're using kafka:9092
    def test_data_provider(self):
        data_providers = parse_config(["oeda", "config", "crowdnav_config"], "dataProviders")
        default_variables = parse_config(["oeda", "config", "crowdnav_config"], "knobs")
        self.assertTrue(data_providers)
        self.assertTrue(default_variables)

        for dp in data_providers:
            self.assertTrue(dp["type"])
            self.assertTrue(dp["serializer"])
            createInstance(wf=None, cp=dp)
            self.assertTrue(dp["instance"])

    def test_r_connection(self):
        self.assertTrue(Config.plumber_host)
        self.assertTrue(Config.plumber_port)
        # res should be [u'Plumber API is running']
        res = requests.get("http://" + Config.plumber_host + ":" + str(Config.plumber_port)).json()
        info(res[0], Fore.CYAN)
        self.assertTrue(res[0])

    # this must be executed before the rest below
    def test_a_initiate(self):
        experiment = initiate()
        self.assertTrue(experiment)
        IntegrationTest.experiment = experiment

    def test_b_stages(self):
        experiment_id = IntegrationTest.experiment["id"]
        self.assertTrue(experiment_id)
        stage_ids = db().get_stages(experiment_id)[0] # 0 = _id, 1 = _source
        self.assertTrue(stage_ids)
        IntegrationTest.stage_ids = stage_ids

    def test_c_data_points(self):
        for stage_id in IntegrationTest.stage_ids:
            self.assertTrue(stage_id)
            data_points = db().get_data_points(IntegrationTest.experiment["id"], stage_id)
            for point in data_points:
                self.assertTrue(point["payload"])
                self.assertTrue(point["created"])
        info("Data points are valid, finished integration test", Fore.CYAN)

if __name__ == '__main__':
    unittest.main()
    exit(1)