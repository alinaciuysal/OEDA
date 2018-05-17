from abc import ABCMeta, abstractmethod
from colorama import Fore
from oeda.databases import db
from oeda.log import *


class Analysis(object):

    __metaclass__ = ABCMeta

    def __init__(self, experiment_ids, y_key):
        self.experiment_ids = experiment_ids
        self.y_key = y_key
        self.stages_count = 0

    def start(self, data, knobs):

        if not data[0]:
            error("Tried to run " + self.name + " on empty data.")
            error("Aborting analysis.")
            return

        return self.run(data, knobs)

    @abstractmethod
    def run(self, data, knobs):
        """ analysis-specific logic """
        pass

    '''Currently not used'''
    def get_data(self):
        first_experiment_id = self.experiment_ids[0]
        data, knobs, stages_count = db().get_data_for_run(first_experiment_id)

        for experiment_id in self.experiment_ids[1:]:
            new_data, new_knobs, new_stages_count = db().get_data_for_run(experiment_id)
            for i in range(new_stages_count):
                data[stages_count + i] = new_data[i]
                knobs[stages_count + i] = new_knobs[i]
            self.stages_count += new_stages_count
        return data, knobs

    '''Currently not used'''
    def combine_data(self):
        first_experiment_id = self.experiment_ids[0]
        data, knobs, self.stages_count = db().get_data_for_run(first_experiment_id)

        for experiment_id in self.experiment_ids[1:]:
            new_data, new_knobs, new_stages_count = db().get_data_for_run(experiment_id)
            for i in range(self.stages_count):
                data[i] += new_data[i]
                knobs[i] += new_knobs[i]

        return data, knobs

    '''Currently not used'''
    def save_result(self, analysis_name, result):
        db().save_analysis(self.experiment_ids, analysis_name, result)
        info("> ", Fore.CYAN)
        info("> Analysis of type '" + self.name + "' performed on datasets [" +
             ", ".join(str(x) for x in self.experiment_ids) + "] of " + str(self.stages_count) + " experiments", Fore.CYAN)
        info("> Result: " + str(result), Fore.CYAN)