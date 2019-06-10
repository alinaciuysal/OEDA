from abc import ABCMeta, abstractmethod
from oeda.log import *

class Analysis(object):

    __metaclass__ = ABCMeta

    def __init__(self, y_key):
        self.y_key = y_key

    def start(self, data, knobs):
        if not data:
            error("Tried to run " + self.name + " on empty data.")
            error("Aborting analysis.")
            return

        return self.run(data, knobs)

    @abstractmethod
    def run(self, data, knobs, stage_ids=None):
        """ analysis-specific logic """
        pass