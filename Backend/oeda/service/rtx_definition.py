from oeda.databases import db
import numpy as np
from math import isnan
from oeda.log import *

class RTXDefinition:

    name = None
    folder = None
    _oeda_experiment = None
    _oeda_target = None
    _oeda_callback = None
    _oeda_stop_request = None
    primary_data_provider = None
    secondary_data_providers = []
    change_provider = None
    id = None
    stage_counter = None
    all_knobs = None
    remaining_time_and_stages = None
    incoming_data_types = None
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

        # set-up primary data provider
        primary_data_provider = oeda_target["primaryDataProvider"]
        primary_data_provider["data_reducer"] = RTXDefinition.primary_data_reducer
        self.primary_data_provider = primary_data_provider

        if oeda_target["secondaryDataProviders"] is not None:
            for dp in oeda_target.get("secondaryDataProviders"):  # see dataProviders.json for the mapping
                dp["data_reducer"] = RTXDefinition.secondary_data_reducer
                self.secondary_data_providers.append(dp)

        # TODO: knob_value[2] is only provided in step_explorer strategy?
        execution_strategy = oeda_experiment["executionStrategy"]
        if execution_strategy["type"] == 'step_explorer':
            new_knobs = {}
            for knob_key, knob_value in oeda_experiment["executionStrategy"]["knobs"].iteritems():
                new_knobs[knob_key] = ([knob_value[0], knob_value[1]], knob_value[2])
            execution_strategy["knobs"] = new_knobs

        self.execution_strategy = execution_strategy
        self.state_initializer = RTXDefinition.state_initializer
        self.evaluator = RTXDefinition.evaluator
        self.folder = None
        self.setup_stage = RTXDefinition.setup_stage

        if execution_strategy["type"] == "step_explorer" or execution_strategy["type"] == "sequential":
            knob_values = get_experiment_list(execution_strategy["type"], execution_strategy["knobs"])
            knob_keys = get_knob_keys(execution_strategy["type"], execution_strategy["knobs"])
            self.all_knobs = get_all_knobs(knob_keys, knob_values)

    def run_oeda_callback(self, dictionary):
        dictionary['stage_counter'] = self.stage_counter
        self._oeda_callback(dictionary, self.id)

    """ saves the data provided by the primary data provider
        new_data is sth like {'overhead' : 1.22253, 'minimalCosts': '200.2522', ...} but count is same for all keys """
    @staticmethod
    def primary_data_reducer(new_data, wf):
        info("index of primary data " + str(wf.primary_data_counter) + str(new_data))
        db().save_data_point(new_data, wf.primary_data_counter, wf.id, wf.stage_counter, None)
        wf.primary_data_counter += 1
        # for index, (data_type_name, data_type_value) in enumerate(new_data.items()):
        #     data_type_count = str(data_type_name) + "_cnt"
        #     cnt = state.get(data_type_count)
        #     if index == 0:  # perform save operation only once
        #         db().save_data_point(new_data, cnt, wf.id, wf.stage_counter, None)
        #     state[str(data_type_name)] = (state[str(data_type_name)] * cnt + data_type_value) / (cnt + 1)
        #     state[data_type_count] += 1
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
        info("index of secondary data " + str(wf.secondary_data_counter) + str(new_data))
        db().save_data_point(new_data, wf.secondary_data_counter, wf.id, wf.stage_counter, idx)
        wf.secondary_data_counter += 1
        # for index, (data_type_name, data_type_value) in enumerate(new_data.items()):
        #     data_type_count = str(data_type_name) + "_cnt"
        #     cnt = state.get(data_type_count)
        #     if index == 0:  # perform save operation only once by passing index of data provider(idx)
        #         db().save_data_point(new_data, cnt, wf.id, wf.stage_counter, idx)
        #     state[data_type_count] += 1
        # return state
        return wf

    @staticmethod
    def state_initializer(state, wf):

        for data_type in wf.primary_data_provider["incomingDataTypes"]:
            data_type_name = str(data_type["name"])
            data_type_count = data_type_name + "_cnt"
            state[data_type_name] = 0
            state[data_type_count] = 0

        if len(wf.secondary_data_providers) > 0:
            # initialize all secondary data types, not only the hard-coded ones; as well as their counts to 0
            for dp in wf.secondary_data_providers:
                for data_type in dp["incomingDataTypes"]:
                    data_type_name = str(data_type["name"])
                    data_type_count = data_type_name + "_cnt"
                    state[data_type_name] = 0
                    state[data_type_count] = 0

        return state

    @staticmethod
    def setup_stage(wf, stage_knob):
        db().save_stage(wf.stage_counter, stage_knob, wf.id)

    @staticmethod
    def calculate_result(state, wf):
        weighted_sum = 0
        for data_type in wf.considered_data_types:
            data_type_name = data_type["name"]
            data_type_aggregate_function = str(data_type['aggregateFunction'])
            aggs = db().get_aggregation(wf.id, wf.stage_counter, "stats", data_type_name)
            print(aggs)
            # distinction between nominal scale TODO: more scale will be added
            if data_type["scale"] == "Nominal":
                # now data_type_aggregate_function is either count-True or count-False
                field_value = data_type_aggregate_function.split("-")[1] # fetch value
                field_value = 1 if field_value == 'True' else 0 # because we store them in binary, not in True/False
                count = db().get_count(wf.id, wf.stage_counter, data_type_name, field_value)
                total = db().get_aggregation(wf.id, wf.stage_counter, "stats", data_type_name)["count"]
                value = float(count) / total
            else:
                if 'percentiles' in data_type_aggregate_function:
                    # we have percentiles-25, percentiles-50 etc and parse it to use percentiles as outer aggregate_function
                    aggregate_function, percentile_number = data_type_aggregate_function.split("-")
                    values = db().get_aggregation(wf.id, wf.stage_counter, aggregate_function, data_type_name)
                    value = values[str(float(percentile_number))]
                else:
                    aggregate_function = "stats"
                    if data_type_aggregate_function in ['sum_of_squares', 'variance', 'std_deviation']:
                        aggregate_function = "extended_stats"
                    values = db().get_aggregation(wf.id, wf.stage_counter, aggregate_function, data_type_name)
                    value = values[data_type_aggregate_function] # retrieve exact value from response
                print("retrieved value", value)
            if value is not None and isnan(float(value)) is False:
                # maximization criteria before calculating the result
                if data_type["criteria"] == "Maximize":
                    print("value before ", value)
                    value = np.reciprocal(value)
                    print("value after ", value)
                weighted_sum += value * float(data_type["weight"]) / 100
            info("data_type_name: " + data_type_name + " value: " + str(value) + " weight: " + str(data_type["weight"]) + " weighted_sum: " + str(weighted_sum))
        state["result"] = weighted_sum / len(wf.considered_data_types)
        return state

    @staticmethod
    def evaluator(state, wf):
        wf.stage_counter += 1
        # do the actual calculation of output variable (y)
        state = RTXDefinition.calculate_result(state, wf)
        info("---------------- result")
        info(state["result"])
        return state["result"]

def get_experiment_list(strategy_type, knobs):

    if strategy_type == "sequential":
        return [config.values() for config in knobs]

    if strategy_type == "step_explorer":
        variables = []
        parameters_values = []
        for key in knobs:
            variables += [key]
            lower = knobs[key][0][0]
            upper = knobs[key][0][1]
            step = knobs[key][1]

            decimal_points = str(step)[::-1].find('.')
            multiplier = pow(10, decimal_points)

            value = lower
            parameter_values = []
            while value <= upper:
                parameter_values += [[value]]
                value = float((value * multiplier) + (step * multiplier)) / multiplier

            parameters_values += [parameter_values]
        return reduce(lambda list1, list2: [x + y for x in list1 for y in list2], parameters_values)

    if strategy_type == "random":
        return [config.values() for config in knobs]


def get_knob_keys(strategy_type, knobs):

    if strategy_type == "sequential":
        '''Here we assume that the knobs in the sequential strategy are specified in the same order'''
        return knobs[0].keys()

    if strategy_type == "step_explorer":
        return knobs.keys()

    if strategy_type == "random":
        return knobs[0].keys()


def get_all_knobs(knob_keys, knob_values):
    all_knobs = []
    for i in range(len(knob_values)):
        knobs = {}
        index = 0
        for k in knob_keys:
            knobs[k] = knob_values[i][index]
            index += 1
        all_knobs.append(knobs)
    return all_knobs