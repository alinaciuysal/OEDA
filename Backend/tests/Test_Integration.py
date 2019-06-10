import os
import requests
import integration_test_utility as util
import pytest
from oeda.databases import setup_experiment_database, db
from sumolib import checkBinary
from oeda.config.R_config import Config
from oeda.log import *
from oeda.rtxlib.dataproviders import createInstance

''' 
    Integration test for OEDA using CrowdNav which should be running in the background:

    main method contains a test suite that executes tests for following tests:
        - checks db connection
        - mlrMBO-API connection
        - SUMO connection
        - data providers and their connections defined in config/crowdnav_config/data_providers.json
        - knobs defined in config/crowdnav_config/knobs.json
        - parsing knobs
        - target system creation
        - experiment creation and execution
        - testing stages and data points in the experiment
    
    The class name should also start with "Test" in order to be discovered by Pytest
    Usage: pytest -s -v Test_Integration.py
    
'''
@pytest.mark.incremental
class Test_Integration():
    # docker without http authentication can also be used
    # by setting host as "192.168.99.100" in oeda.databases.experiment_db_config.json
    elasticsearch_ip = None
    elasticsearch_port = None

    for_tests = True
    knobs = None # for integration tests, they're used as default variables
    changeableVariables = None
    considered_data_types = None # these are subset of all data types, but they account for the weight in overall result
    data_providers = None
    
    target_system = None
    experiment = None
    stage_ids_anova = None
    stage_ids_bogp = None
    stage_ids_ttest = None
    analysis = None

    def test_db_1(self):
        config = util.parse_config(["oeda", "databases"], "experiment_db_config")
        assert config 
        assert config["host"] 
        assert config["port"] 
        assert config["index_definitions"].keys() 
        Test_Integration.elasticsearch_ip = str(config["host"])
        Test_Integration.elasticsearch_port = str(config["port"])
        setup_experiment_database("elasticsearch", Test_Integration.elasticsearch_ip, Test_Integration.elasticsearch_port, for_tests=Test_Integration.for_tests)
        assert db() 

    def test_db_2(self):
        health = db().es.cluster.health()
        # yellow means that the primary shard is allocated but replicas are not
        # and green means that all shards are allocated
        assert health["status"] == 'yellow'

    # uses regular http GET request
    def test_db_3(self):
        res = requests.get("http://" + Test_Integration.elasticsearch_ip + ":" + Test_Integration.elasticsearch_port).json()
        assert res["cluster_name"] 
        assert res["cluster_uuid"] 

    def test_mlrMBO_connection(self):
        assert Config.plumber_host 
        assert Config.plumber_port 
        res = requests.get("http://" + Config.plumber_host + ":" + str(Config.plumber_port)).text
        info(res, Fore.CYAN)
        assert str(res) == '["Plumber API is running"]'

    def test_sumo(self):
        try:
            var = os.environ.get("SUMO_HOME")
            assert var 
            sys.path.append(var)
            sumoGuiBinary = checkBinary('sumo-gui')
            assert sumoGuiBinary 
            sumoBinary = checkBinary('sumo')
            assert sumoBinary 
        except ImportError:
            sys.exit("please declare environment variable 'SUMO_HOME' as the root directory"
                     " of your sumo installation (it should contain folders 'bin', 'tools' and 'docs')")

    # as we're only using crowdnav_config for now,
    # make sure right values have been set in dataProviders.json file under oeda/crowdnav_config folder
    # also you need to add 127.0.0.1 kafka entry to /etc/hosts file because we're using kafka:9092 there
    # one important point: we need to set dp["instance"] to Null after assertion
    # because it will be created by oeda.rtxlib.dataproviders.init_data_providers method
    # if we don't do so, ES gives serialization error while saving
    def test_data_provider(self):
        data_providers = util.parse_config(["oeda", "config", "crowdnav_config"], "dataProviders")
        assert data_providers 
        for dp in data_providers:
            assert dp["type"] 
            assert dp["serializer"] 
            createInstance(wf=None, cp=dp)
            assert dp["instance"] 
            dp["instance"] = None
        Test_Integration.data_providers = data_providers

    def test_knobs(self):
        knobs = util.parse_config(["oeda", "config", "crowdnav_config"], "knobs")
        assert knobs 
        # integrity check
        for knob in knobs:
            assert knob["name"] 
            assert knob["description"] 
            assert knob["scale"] 
            assert type(knob["min"]) is float or type(knob["min"]) is int
            assert type(knob["max"]) is float or type(knob["min"]) is int
            assert type(knob["default"]) is float or type(knob["default"]) is int
        Test_Integration.knobs = knobs

    def test_considered_data_types(self):
        data_providers = util.parse_config(["oeda", "config", "crowdnav_config"], "dataProviders")
        assert data_providers 
        # integrity check
        for dp in data_providers:
            assert dp["name"]
            assert dp["description"]
            assert dp["type"]
            assert dp["serializer"]
            assert dp["incomingDataTypes"]

            for dt in dp["incomingDataTypes"]:
                assert dt["name"]
                assert dt["description"]
                assert dt["scale"]
                assert dt["dataProviderName"]
                assert dt["criteria"]

            if dp["name"] == "Trips":
                considered_data_types = util.adjust_functions_and_weights(dp["incomingDataTypes"])
                assert considered_data_types 
                Test_Integration.considered_data_types = considered_data_types

    def test_analysis(self):
        analysis = util.create_analysis_definition(type='3_phase', anovaAlpha=0.05, sample_size=100, tTestEffectSize=0.7)
        assert analysis
        Test_Integration.analysis = analysis

    def test_changeable_variables(self):
        # at least 2 variables (factors) should present if we want to use two-way-anova
        changeableVariables = util.create_changeable_variables(numberOfVariables=2)
        assert changeableVariables
        Test_Integration.changeableVariables = changeableVariables

    # this case must be executed before the rest below
    def test_create_target_system(self):
        target_system = util.create_ts_definition_crowdnav(data_providers=Test_Integration.data_providers,
                                                           knobs=Test_Integration.knobs,
                                                           changeableVariables=Test_Integration.changeableVariables,
                                                           ignore_first_n_samples=30)
        assert target_system
        db().save_target(target_system)
        Test_Integration.target_system = target_system

    def test_create_experiment(self):
        experiment = util.create_experiment_with_mlr_mbo("mlr_mbo",
                                                    sample_size=20,
                                                    knobs=Test_Integration.knobs,
                                                    considered_data_types=Test_Integration.considered_data_types,
                                                    analysis=Test_Integration.analysis,
                                                    optimizer_iterations_in_design=len(Test_Integration.knobs)*4,
                                                    acquisition_method="ei",
                                                    optimizer_iterations=5)
        assert experiment
        assert experiment["id"]
        experiment["targetSystemId"] = Test_Integration.target_system["id"]
        db().save_experiment(experiment)
        saved_experiment = db().get_experiment(experiment["id"])
        assert saved_experiment
        Test_Integration.experiment = experiment

    def test_execution(self):
        workflow = util.rtx_execution(experiment=Test_Integration.experiment, target=Test_Integration.target_system)
        assert workflow
        target_status = db().get_target(Test_Integration.target_system["id"])["status"]
        assert target_status == "READY"
        experiment_status = db().get_experiment(Test_Integration.experiment["id"])["status"]
        assert experiment_status == "SUCCESS"
        self.test_anova()
        self.test_anova_data_points()

    def test_anova(self):
        experiment_id = Test_Integration.experiment["id"]
        assert experiment_id
        stage_ids_anova = db().get_stages(experiment_id=experiment_id, step_no=1)[0] # 0 = _ids, 1 = _source
        assert stage_ids_anova
        Test_Integration.stage_ids_anova = stage_ids_anova

    def test_anova_data_points(self):
        for idx, stage_id in enumerate(Test_Integration.stage_ids_anova):
            assert stage_id
            data_points = db().get_data_points(experiment_id=Test_Integration.experiment["id"], step_no=1, stage_no=idx + 1) # because stages start from 1 whereas idx start from 0
            for point in data_points:
                assert point["payload"]
                assert point["createdDate"]