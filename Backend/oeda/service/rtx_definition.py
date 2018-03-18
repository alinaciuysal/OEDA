from oeda.databases import db
import numpy as np
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
    optimized_data_types = []

    def __init__(self, oeda_experiment, oeda_target, oeda_callback, oeda_stop_request):
        self._oeda_experiment = oeda_experiment
        self._oeda_target = oeda_target
        self._oeda_callback = oeda_callback
        self._oeda_stop_request = oeda_stop_request
        self.name = oeda_experiment["name"]
        self.id = oeda_experiment["id"]
        self.stage_counter = 1
        self.remaining_time_and_stages = dict() # contains remaining time and stage for an experiment
        self.change_provider = oeda_target["changeProvider"]
        self.incoming_data_types = oeda_target["incomingDataTypes"] # contains all of the data types provided by both config & user
        self.optimized_data_types = oeda_experiment["optimized_data_types"]

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

    # TODO: integrate other metrics using a parameter here, instead of default average metric
    """ new_data is sth like {'overhead' : 1.22253, 'minimalCosts': '200.2522', ...} but count is same for all keys """
    """ also https://stackoverflow.com/questions/41034963/typeerror-coercing-to-unicode-need-string-or-buffer-long-found"""
    @staticmethod
    def primary_data_reducer(state, new_data, wf):
        for index, (data_type_name, data_type_value) in enumerate(new_data.items()):
            data_type_count = str(data_type_name) + "_cnt"
            cnt = state.get(data_type_count)
            if index == 0:  # perform save operation only once
                db().save_data_point(new_data, cnt, wf.id, wf.stage_counter, None)
            state[str(data_type_name)] = (state[str(data_type_name)] * cnt + data_type_value) / (cnt + 1)
            state[data_type_count] += 1

        if wf._oeda_stop_request.isSet():
            raise RuntimeError("Experiment interrupted from OEDA while gathering data.")
        return state

    """ important assumption here: 1-1 mapping between secondary data provider and its payload """
    """ i.e. payload (data) with different attributes can be published to same topic of Kafka """
    """ new_data is a type of dict, e.g. {'routingDuration': 12, 'xDuration': 555.25...} is handled accordingly """
    """ but publishing different types of payloads to the same topic will not work, declare another secondary data provider for this purpose """
    @staticmethod
    def secondary_data_reducer(state, new_data, wf, idx):
        for index, (data_type_name, data_type_value) in enumerate(new_data.items()):
            data_type_count = str(data_type_name) + "_cnt"
            cnt = state.get(data_type_count)
            if index == 0:  # perform save operation only once by passing index of data provider(idx)
                db().save_data_point(new_data, cnt, wf.id, wf.stage_counter, idx)
            state[data_type_count] += 1
        return state

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
    def evaluator(result_state, wf):
        wf.stage_counter += 1
        result_state = match_criteria(result_state, wf)
        # TODO: TEST this!
        # if hasattr(wf, "optimized_data_types"):
        #     return [result_state[i] for i in wf.optimized_data_types]

        # TODO: remove [0] and return an array for multi-objective optimization
        return result_state[wf.optimized_data_types[0]['name']]


''' Takes the inverse of the result variable according to provided criteria'''
def match_criteria(result_state, wf):
    for data_type in wf.optimized_data_types:
        if data_type['criteria'] == 'Maximize':
            # get value of data type
            value = result_state[data_type['name']]
            # modify result_state by taking inverse of the value
            result_state[data_type['name']] = np.reciprocal(value)
    return result_state


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