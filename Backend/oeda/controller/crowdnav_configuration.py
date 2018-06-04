from flask import jsonify
from flask_restful import Resource
from oeda.config.crowdnav_config import Config
from oeda.log import *
import traceback
import json


class CrowdNavConfigController(Resource):
    @staticmethod
    def get():
        try:
            validAggregationFcns = ['avg', 'min', 'max', 'count', 'sum', 'percentiles-1','percentiles-5',
                                    'percentiles-25','percentiles-50','percentiles-75','percentiles-95','percentiles-99',
                                    'sum_of_squares','variance','std_deviation', 'ratio-True', 'ratio-False']
            knobs = json.loads(open('oeda/config/crowdnav_config/knobs.json').read())
            dataProviders = json.loads(open('oeda/config/crowdnav_config/dataProviders.json').read())
            # check dataProviders if there's a default data type & its aggregationFcn
            valid = False
            for dp in dataProviders:
                for dataType in dp["incomingDataTypes"]:
                    if "is_default" in dataType and "defaultAggregationFcn" in dataType:
                        if dataType["is_default"] is True and dataType["defaultAggregationFcn"] in validAggregationFcns:
                            valid = True
                            break
            if valid:
                data = {
                    "name": "CrowdNav",
                    "description": "Simulation based on SUMO",
                    "kafkaTopicRouting": Config.kafkaTopicRouting,
                    "kafkaTopicTrips": Config.kafkaTopicTrips,
                    "kafkaTopicPerformance": Config.kafkaTopicPerformance,
                    "kafkaHost": Config.kafkaHost,
                    "kafkaCommandsTopic": Config.kafkaCommandsTopic, # for now, kafkaHost and kafkaCommandsTopic are only fetched & used for populating change provider entity in OEDA
                    "knobs": knobs, # used to populate changeableVariables in OEDA
                    "dataProviders": dataProviders # used to populate dataProviders in OEDA
                }
                resp = jsonify(data)
                resp.status_code = 200
                return resp
            else:
                msg = "At least one incoming data type should have default & defaultAggregationFcn fields"
                error(msg)
                return {"error": msg}, 404

        except Exception as e:
            tb = traceback.format_exc()
            print(tb)
            return {"error": e.message}, 404
