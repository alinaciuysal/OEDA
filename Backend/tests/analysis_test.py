from oeda.databases import setup_experiment_database, db
import unittest, random
from tests.unit_test import UnitTest
from oeda.utilities.TestUtility import parse_config
from oeda.analysis.two_sample_tests import Ttest, TtestPower, TtestSampleSizeEstimation
from oeda.analysis.one_sample_tests import DAgostinoPearson, AndersonDarling, KolmogorovSmirnov, ShapiroWilk
from oeda.analysis.n_sample_tests import Bartlett, FlignerKilleen, KruskalWallis, Levene, OneWayAnova
from math import sqrt
import numpy as np

''' Simulation systems should be running in the background
    see https://stackoverflow.com/questions/5387299/python-unittest-testcase-execution-order/5387956#5387956 and
    https://docs.python.org/2/library/unittest.html#unittest.TestLoader.sortTestMethodsUsing
    also, self.assertTrue(param) function checks if bool(x) is True, we use it for assertIsNotNone() - which is available 
    in Python >=3.1 - 
    
    names of test cases are important because of the default ordering of the unittest framework
    so, tests are named according to this pattern: test_<order>_<name>. 
        
    random experiment id and 2 stage ids are sampled for different purposes 
    
    TODO: main method should contain a test suite that executes 1)unit tests 2)integration tests 3)analysis tests 

'''
class AnalysisTest(unittest.TestCase):

    data = None
    knobs = None
    experiment_id = None
    stage_id = None
    outer_key = "payload"
    key = "overhead"
    mean_diff = 0.1 # as in crowdnav-elastic-ttest-sample-size/definition.py

    def test_a_db_1(self):
        config = parse_config(["oeda", "databases"], "experiment_db_config")
        self.assertTrue(config)
        self.assertTrue(config["host"])
        self.assertTrue(config["port"])
        self.assertTrue(config["index"]["name"])
        UnitTest.elasticsearch_index = config["index"]["name"] + "_test"
        UnitTest.elasticsearch_ip = str(config["host"])
        UnitTest.elasticsearch_port = str(config["port"])
        # set flag to false because we are interested in previously-created data points in "oeda" index for now
        setup_experiment_database("elasticsearch", UnitTest.elasticsearch_ip, UnitTest.elasticsearch_port, for_tests=False)
        self.assertTrue(db())

    def test_b_experiment_ids(self):
        experiment_ids, source = db().get_experiments()
        self.assertTrue(experiment_ids)
        random_experiment_id = random.choice(experiment_ids)
        self.assertTrue(random_experiment_id)
        # tries to sample an experiment with number of stages >= 2
        # TODO: can be problematic if there are 2 stages but experiment is interrupted somehow
        # TODO: and there are no data points in one of the stages
        while db().get_stages_count(experiment_id=random_experiment_id) < 2:
            random_experiment_id = random.choice(experiment_ids)
        self.assertTrue(random_experiment_id)
        AnalysisTest.experiment_id = random_experiment_id

    def test_c_data_points(self):
        data, knobs = db().get_data_for_analysis(AnalysisTest.experiment_id)
        self.assertTrue(data)
        self.assertTrue(knobs)
        AnalysisTest.data = data
        AnalysisTest.knobs = knobs

    def test_d_random_stage(self):
        stage_ids = AnalysisTest.data.keys()
        self.assertTrue(stage_ids)
        random_stage_ids = random.sample(stage_ids, 2)
        self.assertTrue(random_stage_ids)
        AnalysisTest.stage_ids = random_stage_ids
        AnalysisTest.stage_id = AnalysisTest.stage_ids[0]

    def test_e_convert_outer_payload(self):
       if AnalysisTest.outer_key is not None:
            for stage_id in AnalysisTest.stage_ids:
                res = []
                # AnalysisTest.data is a dict of stage_ids and data_points
                for data_point in AnalysisTest.data[stage_id]:
                    outer_key = AnalysisTest.outer_key
                    self.assertTrue(data_point[outer_key])
                    res.append(data_point[outer_key][AnalysisTest.key])
                AnalysisTest.data[stage_id] = res

    ##########################
    ## One sample tests (Normality tests)
    ##########################
    def test_f_anderson(self):
        stats, pvalue = AndersonDarling(AnalysisTest.experiment_id, AnalysisTest.key, alpha=0.05).get_statistic_and_pvalue(y=AnalysisTest.data[AnalysisTest.stage_id])
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    def test_g_dagostino(self):
        stats, pvalue = DAgostinoPearson(AnalysisTest.experiment_id, AnalysisTest.key, alpha=0.05).get_statistic_and_pvalue(y=AnalysisTest.data[AnalysisTest.stage_id])
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    def test_h_kolmogorov(self):
        stats, pvalue = KolmogorovSmirnov(AnalysisTest.experiment_id, AnalysisTest.key, alpha=0.05).get_statistic_and_pvalue(y=AnalysisTest.data[AnalysisTest.stage_id])
        self.assertTrue(stats)
        self.assertTrue(pvalue is not None or pvalue == 0.0) # TODO: is this valid?

    def test_i_shapiro(self):
        stats, pvalue = ShapiroWilk(AnalysisTest.experiment_id, AnalysisTest.key, alpha=0.05).get_statistic_and_pvalue(y=AnalysisTest.data[AnalysisTest.stage_id])
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    #########################
    # Two-sample tests
    #########################
    def test_j_Ttest(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        test = Ttest(experiment_ids=stage_ids, y_key=AnalysisTest.key).run(data=samples, knobs=knobs)
        self.assertTrue(test)
        for k in test:
            self.assertTrue(test[k] is not None) # we used this instead of assertTrue(test[k]) because value can be False

    def test_k_TtestPower(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        # TODO: check validity of this approach?
        # pooled_std = wf.math.sqrt((wf.np.var(x1) + wf.np.var(x2)) / 2)
        x1 = samples[0]
        x2 = samples[1]
        pooled_std = sqrt((np.var(x1) + np.var(x2)) / 2)
        effect_size = AnalysisTest.mean_diff / pooled_std
        test = TtestPower(experiment_ids=stage_ids, y_key=AnalysisTest.key, effect_size=effect_size).run(data=samples, knobs=knobs)
        self.assertTrue(test)
        for k in test:
            self.assertTrue(test[k] is not None)

    def test_l_TtestSampleSizeEstimation(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        # TODO: effect_size is None for now?
        test = TtestSampleSizeEstimation(experiment_ids=stage_ids, y_key=AnalysisTest.key, effect_size=None, mean_diff=AnalysisTest.mean_diff).run(data=samples, knobs=knobs)
        self.assertTrue(test)
        for k in test:
            self.assertTrue(test[k] is not None)

    #########################
    # Different distributions tests
    #########################
    def test_m_DifferentDistributionsTest(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        stats, pvalue = OneWayAnova(experiment_ids=stage_ids, y_key=AnalysisTest.key).get_statistic_and_pvalue(args=samples)
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    def test_n_KruskalWallis(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        stats, pvalue = KruskalWallis(experiment_ids=stage_ids, y_key=AnalysisTest.key).get_statistic_and_pvalue(args=samples)
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    ##########################
    ## Equal variance tests
    ##########################
    def test_o_Levene(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        stats, pvalue = Levene(experiment_ids=stage_ids, y_key=AnalysisTest.key).get_statistic_and_pvalue(y=samples)
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    def test_p_Bartlett(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        stats, pvalue = Bartlett(experiment_ids=stage_ids, y_key=AnalysisTest.key).get_statistic_and_pvalue(y=samples)
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    def test_r_FlignerKilleen(self):
        stage_ids, samples, knobs = AnalysisTest.get_data_for_two_sample_tests()
        stats, pvalue = FlignerKilleen(experiment_ids=stage_ids, y_key=AnalysisTest.key).get_statistic_and_pvalue(y=samples)
        self.assertTrue(stats)
        self.assertTrue(pvalue)

    """ helper fcn for two and n-sample tests """
    @staticmethod
    def get_data_for_two_sample_tests():
        stage_id_1 = AnalysisTest.stage_ids[0]
        stage_id_2 = AnalysisTest.stage_ids[1]
        stage_ids = [stage_id_1, stage_id_1]

        sample_1 = AnalysisTest.data[stage_id_1]
        sample_2 = AnalysisTest.data[stage_id_2]
        samples = [sample_1, sample_2]

        knob_1 = AnalysisTest.knobs[stage_id_1]
        knob_2 = AnalysisTest.knobs[stage_id_2]
        knobs = [knob_1, knob_2]

        return stage_ids, samples, knobs

def suite():
    """
        Gather all the tests from this module in a test suite.
    """
    test_suite = unittest.TestSuite()
    # test_suite.addTest(unittest.makeSuite(UnitTest))
    test_suite.addTest(unittest.makeSuite(AnalysisTest))
    return test_suite

if __name__ == '__main__':
    # ref https://stackoverflow.com/questions/12011091/trying-to-implement-python-testsuite
    mySuit=suite()
    runner=unittest.TextTestRunner()
    runner.run(mySuit)
    exit(1)