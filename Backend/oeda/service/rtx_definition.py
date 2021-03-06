from oeda.databases import db
from math import isnan
from oeda.log import *
from oeda.utilities.MathUtility import take_inverse

class RTXDefinition:

    name = None
    _oeda_experiment = None
    _oeda_target = None
    _oeda_callback = None
    _oeda_stop_request = None
    primary_data_provider = None
    secondary_data_providers = []
    change_provider = None
    id = None
    stage_counter = None # for each different step, this stage counter is reset to 1
    all_knobs = None
    remaining_time_and_stages = None
    incoming_data_types = None
    step_no = None
    step_name = None
    considered_data_types = []

    def __init__(self, oeda_experiment, oeda_target, oeda_callback, oeda_stop_request):
        self._oeda_experiment = oeda_experiment
        self._oeda_target = oeda_target
        self._oeda_callback = oeda_callback
        self._oeda_stop_request = oeda_stop_request
        self.name = oeda_experiment["name"]
        self.id = oeda_experiment["id"]
        self.stage_counter = 1
        self.primary_data_counter = 1
        self.secondary_data_counter = 1
        self.remaining_time_and_stages = dict() # contains remaining time and stage for an experiment
        self.change_provider = oeda_target["changeProvider"]
        self.incoming_data_types = oeda_target["incomingDataTypes"] # contains all of the data types provided by both config & user
        self.considered_data_types = oeda_experiment["considered_data_types"]
        self.analysis = oeda_experiment["analysis"]

        # set-up primary data provider
        primary_data_provider = oeda_target["primaryDataProvider"]
        primary_data_provider["data_reducer"] = RTXDefinition.primary_data_reducer
        self.primary_data_provider = primary_data_provider

        if oeda_target["secondaryDataProviders"] is not None:
            for dp in oeda_target.get("secondaryDataProviders"):  # see dataProviders.json for the mapping
                dp["data_reducer"] = RTXDefinition.secondary_data_reducer
                self.secondary_data_providers.append(dp)

        execution_strategy = oeda_experiment["executionStrategy"]
        self.execution_strategy = execution_strategy
        self.evaluator = RTXDefinition.evaluator
        self.setup_stage = RTXDefinition.setup_stage
        self.resetExperimentCounter = RTXDefinition.resetExperimentCounter

    def run_oeda_callback(self, dictionary):
        dictionary['stage_counter'] = self.stage_counter
        dictionary['step_no'] = self.step_no
        dictionary['step_name'] = self.step_name
        self._oeda_callback(dictionary, self.id)

    """ saves the data provided by the primary data provider
        new_data is sth like {'overhead' : 1.22253, 'minimalCosts': '200.2522', ...} but count is same for all keys """
    @staticmethod
    def primary_data_reducer(new_data, wf):
        db().save_data_point(experiment_id=wf.id, step_no=wf.step_no, stage_no=wf.stage_counter,
                             data_point_count=wf.primary_data_counter, secondary_data_provider_index=None, payload=new_data)
        wf.primary_data_counter += 1
        if wf._oeda_stop_request.isSet():
            raise RuntimeError("Experiment interrupted from OEDA while reducing primary data.")
        return wf

    """ important assumption here: there's a 1-1 mapping between secondary data provider and its payload
        i.e. payload (data) with different attributes can be published to same topic of Kafka
        new_data is a type of dict, e.g. {'routingDuration': 12, 'xDuration': 555.25...} is handled accordingly
        but publishing different types of payloads to the same topic will not work, 
        declare another secondary data provider for this purpose """
    @staticmethod
    def secondary_data_reducer(new_data, wf, idx):
        db().save_data_point(experiment_id=wf.id, step_no=wf.step_no, stage_no=wf.stage_counter,
                             data_point_count=wf.secondary_data_counter, secondary_data_provider_index=idx, payload=new_data)
        wf.secondary_data_counter += 1
        return wf

    @staticmethod
    def setup_stage(wf, knobs):
        db().save_stage(experiment_id=wf.id, step_no=wf.step_no, step_name=wf.step_name, stage_no=wf.stage_counter, knobs=knobs)

    @staticmethod
    def calculate_result(wf):
        data_type = wf.considered_data_types[0]
        data_type_name = data_type["name"]
        data_type_aggregate_function = str(data_type['aggregateFunction'])
        if data_type["scale"] == "Boolean":
            # now data_type_aggregate_function is either count-True or count-False
            field_value = data_type_aggregate_function.split("-")[1] # fetch value
            # we store them in binary, not in True/False
            if field_value == 'True':
                field_value = 1
            else:
                field_value = 0
            count = db().get_count(wf.id, wf.step_no, wf.stage_counter, data_type_name, field_value)
            total = db().get_aggregation(wf.id, wf.step_no, wf.stage_counter, "stats", data_type_name)["count"]
            value = float(count) / total
        else:
            if 'percentiles' in data_type_aggregate_function:
                # we have percentiles-25, percentiles-50 etc and parse it to use percentiles as outer aggregate_function
                aggregate_function, percentile_number = data_type_aggregate_function.split("-")
                values = db().get_aggregation(wf.id, wf.step_no, wf.stage_counter, aggregate_function, data_type_name)
                value = values[str(float(percentile_number))]
            else:
                aggregate_function = "stats"
                if data_type_aggregate_function in ['sum_of_squares', 'variance', 'std_deviation']:
                    aggregate_function = "extended_stats"
                values = db().get_aggregation(wf.id, wf.step_no, wf.stage_counter, aggregate_function, data_type_name)
                value = values[data_type_aggregate_function] # retrieve exact value from response
        if value is not None and isnan(float(value)) is False:
            # maximization criteria before calculating the result
            if data_type["criteria"] == "Maximize":
                value = take_inverse(value)
            info("data_type_name: " + data_type_name + " value: " + str(value))
            return value
        else:
            error("data_type_name: " + data_type_name + " value: 0")
            return 0

    @staticmethod
    def evaluator(wf):
        # do the actual calculation of output variable (y)
        result = RTXDefinition.calculate_result(wf)
        info("---------------- result")
        info(result)
        db().update_stage(experiment_id=wf.id, step_no=wf.step_no, stage_no=wf.stage_counter, field="stage_result", value=result)
        wf.stage_counter += 1 # this must be done after all calculations of a single stage
        return result

    @staticmethod
    def resetExperimentCounter(wf):
        if hasattr(wf, "experimentCounter"):
            delattr(wf, "experimentCounter")