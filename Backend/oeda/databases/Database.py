# Abstract interface for a database
#
# A database stores the raw data and the experiment runs of RTX.


class Database:

    def __init__(self):
        pass

    def save_target(self, target_system_id, target_system_data):
        """ saves the data of an OEDA target system with the provided id """
        pass

    def get_target(self, target_system_id):
        """ returns the configuration of an OEDA target system """
        pass

    def get_targets(self):
        """ returns all the target systems """
        pass

    def save_experiment(self, experiment_id, experiment_data):
        """ saves the data of an OEDA experiment with the provided id """
        pass

    def get_experiment(self, experiment_id):
        """ returns the configuration of an OEDA experiment """
        pass

    def get_experiments(self):
        """ returns all OEDA experiments """
        pass

    def update_experiment_status(self, experiment_id, status):
        """ updates experiment status with provided id """
        pass

    def update_target_system_status(self, target_system_id, status):
        """ updates experiment status with provided id """
        pass

    def save_stage(self, stage_no, knobs, experiment_id):
        """ saves stage of an OEDA experiment with provided configuration and stage no """
        pass

    def get_stages(self, experiment_id):
        """ returns all stages of an OEDA experiment with provided id """
        pass

    def get_stages_after(self, experiment_id, timestamp):
        """ returns all stages of an OEDA experiment that are created after the timestamp """
        pass

    def save_data_point(self, payload, data_point_count, experiment_id, stage_no, secondary_data_provider_index):
        """ saves data retrieved from data provider for the given stage """
        pass

    def get_data_points(self, experiment_id, stage_no):
        """ returns data_points whose parent is the concatenated stage_id (see create_stage_id) """
        pass

    def get_data_points_after(self, experiment_id, stage_no, timestamp):
        """ returns data_points that are created after the given timestamp. Data points' parents are the concatenated stage_id (see create_stage_id) """
        pass

    def get_aggregation(self, experiment_id, stage_no, aggregation_name, field):
        """ returns aggregations for the given aggregation name, stage no, and data field found in the payload
            supported aggregations are stats (count, min, max, average, sum), extended_stats (more options),
            and percentiles (1.0, 5.0, 25.0, 50.0 (median), 75.0, 95.0, 99.0 """
        pass

    def get_count(self, experiment_id, stage_no, field, value):
        """ returns document count for the given data field and its value """
        pass

    def clear_db(self):
        """ just for testing, it re-creates an index """
        pass

    @staticmethod
    def create_stage_id(experiment_id, stage_no):
        return str(experiment_id) + "#" + str(stage_no)

    @staticmethod
    def create_data_point_id(experiment_id, stage_no, data_point_count, secondary_data_provider_index):
        """ if secondary_data_provider_index is provided, then data is meant to be coming from sec. data provider """
        if secondary_data_provider_index:
            return str(experiment_id) + "#" + str(stage_no) + "_" + str(data_point_count) + "-" + str(secondary_data_provider_index)
        return str(experiment_id) + "#" + str(stage_no) + "_" + str(data_point_count)

class TargetSystemNotFoundException(Exception):
    pass

