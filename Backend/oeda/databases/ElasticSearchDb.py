import logging
from datetime import datetime

from elasticsearch.exceptions import ConnectionError
from elasticsearch.exceptions import TransportError

from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import scan

from Database import Database
from oeda.log import *


class ElasticSearchDb(Database):

    def __init__(self, host, port, db_config):
        self.es = Elasticsearch([{"host": host, "port": port}])
        try:
            if self.es.ping():
                es_logger = logging.getLogger('elasticsearch')
                es_logger.setLevel(logging.CRITICAL)

                index = db_config["index"]
                self.index = index["name"]

                stage_type = db_config["stage_type"]
                self.stage_type_name = stage_type["name"]

                analysis_type = db_config["analysis_type"]
                self.analysis_type_name = analysis_type["name"]

                data_point_type = db_config["data_point_type"]
                self.data_point_type_name = data_point_type["name"]

                target_system_type = db_config["target_system_type"]
                self.target_system_type_name = target_system_type["name"]

                experiment_system_type = db_config["experiment_type"]
                self.experiment_type_name = experiment_system_type["name"]

                mappings = dict()
                # user can specify an type without a mapping (dynamic mapping)
                if "mapping" in stage_type:
                    mappings[self.stage_type_name] = stage_type["mapping"]
                if "mapping" in analysis_type:
                    mappings[self.analysis_type_name] = analysis_type["mapping"]
                if "mapping" in data_point_type:
                    mappings[self.data_point_type_name] = data_point_type["mapping"]

                body = dict()
                if "settings" in index:
                    body["settings"] = index["settings"]
                if mappings:
                    body["mappings"] = mappings

                self.body = body
                self.indices_client = IndicesClient(self.es)
                if not self.indices_client.exists(self.index):
                    self.indices_client.create(index=self.index, body=self.body)
            else:
                raise ConnectionError("Host/port values are not valid")
        except TransportError as err1:
            error("TransportError while creating elasticsearch instance for experiments. Check type mappings in experiment_db_config.json.")
            raise err1

    def save_target(self, target_system_data):
        target_system_data["createdDate"] = datetime.now().isoformat(' ')
        target_system_id = target_system_data["id"]
        try:
            self.es.index(index=self.index, doc_type=self.target_system_type_name, id=target_system_id, body=target_system_data)
            return target_system_data
        except ConnectionError as err1:
            error("ConnectionError while saving target system. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while saving target system. Check type mappings in experiment_db_config.json.")
            raise err2

    def get_target(self, target_system_id):
        try :
            res = self.es.get(index=self.index, doc_type=self.target_system_type_name, id=target_system_id)
            return res["_source"]
        except ConnectionError as err1:
            error("ConnectionError while retrieving target. Check connection to elasticsearch.")
            raise err1

    def get_targets(self):
        try:
            query = {
                "size" : 1000,
                "query": {
                    "match_all": {}
                }
            }
            res = self.es.search(index=self.index, doc_type=self.target_system_type_name, body=query)
            return [r["_id"] for r in res["hits"]["hits"]], [r["_source"] for r in res["hits"]["hits"]]
        except ConnectionError as err1:
            error("ConnectionError while retrieving targets. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving targets. Check type mappings in experiment_db_config.json.")
            raise err2

    def save_experiment(self, experiment_data):
        experiment_data["status"] = "OPEN"
        experiment_data["createdDate"] = datetime.now().isoformat(' ')
        experiment_id = experiment_data["id"]
        try:
            self.es.index(index=self.index, doc_type=self.experiment_type_name, body=experiment_data, id=experiment_id)
        except ConnectionError as err1:
            error("ConnectionError while saving experiment data. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while saving experiment data. Check type mappings in experiment_db_config.json.")
            raise err2

    def get_experiment(self, experiment_id):
        try:
            res = self.es.get(index=self.index, doc_type=self.experiment_type_name, id=experiment_id)
            return res["_source"]
        except ConnectionError as err1:
            error("ConnectionError while retrieving an experiment. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving an experiment. Check type mappings in experiment_db_config.json.")
            raise err2

    def get_experiments(self):
        query = {
            "size": 1000,
            "query": {
                "match_all": {}
            }
        }
        try:
            res = self.es.search(index=self.index, doc_type=self.experiment_type_name, body=query, sort='createdDate')
            return [r["_id"] for r in res["hits"]["hits"]], [r["_source"] for r in res["hits"]["hits"]]
        except ConnectionError as err1:
            error("ConnectionError while getting experiments. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving experiments. Check type mappings in experiment_db_config.json.")
            raise err2

    def update_experiment_status(self, experiment_id, status):
        body = {"doc": {"status": status}}
        try:
            self.es.update(index=self.index, doc_type=self.experiment_type_name, id=experiment_id, body=body)
        except ConnectionError as err:
            error("ConnectionError while updating experiment status. Check connection to elasticsearch.")
            raise err
        except TransportError as err2:
            error("TransportError while updating experiment status. Check type mappings in experiment_db_config.json.")
            raise err2

    def update_target_system_status(self, target_system_id, status):
        body = {"doc": {"status": status}}
        try:
            self.es.update(index=self.index, doc_type=self.target_system_type_name, id=target_system_id, body=body)
        except ConnectionError as err1:
            error("ConnectionError while updating target system status. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while updating target system status. Check type mappings in experiment_db_config.json.")
            raise err2

    def update_data_point(self, experiment_id, status):
        body = {"doc": {"status": status}}
        try:
            self.es.update(index=self.index, doc_type=self.experiment_type_name, id=experiment_id, body=body)
        except ConnectionError as err1:
            error("ConnectionError while updating experiment status. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while updating experiment status. Check type mappings in experiment_db_config.json.")
            raise err2

    def save_stage(self, stage_no, knobs, experiment_id):
        stage_id = self.create_stage_id(experiment_id, str(stage_no))
        body = dict()
        body["number"] = stage_no
        body["knobs"] = knobs
        body["createdDate"] = datetime.now().isoformat(' ')
        try:
            self.es.index(index=self.index, doc_type=self.stage_type_name, id=stage_id, body=body, parent=experiment_id)
        except ConnectionError as err1:
            error("ConnectionError while saving stage. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while saving stage. Check type mappings in experiment_db_config.json.")
            raise err2

    def update_stage(self, experiment_id, stage_no, stage_result):
        stage_id = self.create_stage_id(experiment_id, str(stage_no))
        body = {"doc": {"stage_result": stage_result}}
        try:
            self.es.update(index=self.index, doc_type=self.stage_type_name, id=stage_id, body=body, parent=experiment_id)
        except ConnectionError as err1:
            error("ConnectionError while updating stage result. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while updating stage result. Check type mappings in experiment_db_config.json.")
            raise err2

    def get_stages(self, experiment_id):
        query = {
            "query": {
                "has_parent": {
                    "parent_type": "experiment",
                    "query": {
                        "match": {
                            "_id": str(experiment_id)
                        }
                    }
                }
            }
        }

        try:
            res = self.es.search(index=self.index, doc_type=self.stage_type_name, body=query, size=10000, sort='createdDate')
            return [r["_id"] for r in res["hits"]["hits"]], [r["_source"] for r in res["hits"]["hits"]]
        except ConnectionError as err1:
            error("ConnectionError while retrieving stages. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving stages. Check type mappings in experiment_db_config.json.")
            raise err2

    def get_stages_after(self, experiment_id, timestamp):
        query = {
            "query": {
                "has_parent": {
                    "parent_type": "experiment",
                    "query": {
                        "match": {
                            "_id": str(experiment_id)
                        }
                    }
                }
            },
            "post_filter": {
                "range": {
                    "createdDate": {
                        "gt": timestamp,
                        "format": "yyyy-MM-dd HH:mm:ss.SSSSSS"
                    }
                }
            }
        }

        try:
            res = self.es.search(index=self.index, doc_type=self.stage_type_name, body=query, sort='createdDate')
            return [r["_id"] for r in res["hits"]["hits"]], [r["_source"] for r in res["hits"]["hits"]]
        except ConnectionError as err1:
            error("ConnectionError while getting stage data. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while getting stage data. Check type mappings in experiment_db_config.json.")
            raise err2

    def save_data_point(self, payload, data_point_count, experiment_id, stage_no, secondary_data_provider_index):
        data_point_id = Database.create_data_point_id(experiment_id, stage_no, data_point_count, secondary_data_provider_index)
        stage_id = Database.create_stage_id(experiment_id, stage_no)
        body = dict()
        body["payload"] = payload
        body["createdDate"] = datetime.now().isoformat(' ')  # used to replace 'T' with ' '
        try:
            self.es.index(index=self.index, doc_type=self.data_point_type_name, body=body, id=data_point_id, parent=stage_id)
        except ConnectionError as err1:
            error("ConnectionError while saving data point. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while saving data point. Check type mappings in experiment_db_config.json.")
            raise err2

    def get_data_points(self, experiment_id, stage_no):
        stage_id = Database.create_stage_id(experiment_id, stage_no)
        query = {
            "query": {
                "has_parent": {
                    "type": "stage",
                    "query": {
                        "match": {
                            "_id": str(stage_id)
                        }
                    }
                }
            }
        }
        try:
            # https://stackoverflow.com/questions/9084536/sorting-by-multiple-params-in-pyes-and-elasticsearch
            # sorting is required for proper visualization of data
            res = self.es.search(index=self.index, body=query, size=10000, sort='createdDate')
            return [r["_source"] for r in res["hits"]["hits"]]
        except ConnectionError as err1:
            error("ConnectionError while retrieving data points. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving data points. Check type mappings in experiment_db_config.json.")
            raise err2

    def get_aggregation(self, experiment_id, stage_no, aggregation_name, field):
        stage_id = self.create_stage_id(experiment_id, stage_no)
        exact_field_name = "payload" + "." + str(field)
        query = {
            "query": {
                "has_parent": {
                    "type": "stage",
                    "query": {
                        "match": {
                            "_id": str(stage_id)
                        }
                    }
                }
            }
        }
        query["size"] = 0 # we are not interested in matching data points

        # prepare the aggregation query
        # https://www.elastic.co/guide/en/elasticsearch/reference/5.5/search-aggregations-metrics-stats-aggregation.html
        # aggregation name can be extended_stats, stats, percentiles etc.
        # so aggregation_result_name would be percentiles_overhead, extended_stats_minimalCosts etc.
        aggregation_key = aggregation_name + "_" + str(field)
        query["aggs"] = {aggregation_key: {aggregation_name: {"field": exact_field_name} } }
        try:
            res = self.es.search(index=self.index, body=query)
            if aggregation_name == "percentiles":
                return res["aggregations"][aggregation_key]["values"]
            else:
                return res["aggregations"][aggregation_key]
        except ConnectionError as err1:
            error("ConnectionError while retrieving aggregations. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving aggregations. Check type mappings in experiment_db_config.json.")
            raise err2

    # https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-filter-aggregation.html
    # can be extended with aggregations using above link
    # for now we are only interested in the document count
    # we are interested in the ratio of given field=value / number of all data that includes this field
    # so, we only return the doc_count here, another query should be issued to get 'count' of all points
    # if we had used res["hits"]["total"] here, it would be wrong because it also includes data from secondary providers
    def get_count(self, experiment_id, stage_no, field, value):
        stage_id = self.create_stage_id(experiment_id, stage_no)
        exact_field_name = "payload" + "." + str(field)
        aggregation_key = "count_" + str(field)
        query = {
            "query": {
                "has_parent": {
                    "type": "stage",
                    "query": {
                        "match": {
                            "_id": str(stage_id)
                        }
                    }
                }
            },
            "size": 0,
            "aggs": {
                aggregation_key: {
                    "filter": {"term": {exact_field_name: value} }
                }
            }
        }
        try:
            res = self.es.search(index=self.index, body=query)
            return res["aggregations"][aggregation_key]["doc_count"]
        except ConnectionError as err1:
            error("ConnectionError while retrieving aggregations from elasticsearch. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving aggregations. Check type mappings for experiments in experiment_db_config.json.")
            raise err2

    def get_data_points_after(self, experiment_id, stage_no, timestamp):
        stage_id = Database.create_stage_id(experiment_id, stage_no)
        query1 = {
            "query": {
                "has_parent": {
                    "parent_type": "stage",
                    "query": {
                        "match": {
                            "_id": str(stage_id)
                        }
                    }
                }
            }
        }

        query2 = {
            "query": {
                "has_parent": {
                    "parent_type": "stage",
                    "query": {
                        "match": {
                            "_id": str(stage_id)
                        }
                    }
                }
            },
            "post_filter": {
                "range": {
                    "createdDate": {
                        "gt": timestamp,
                        "format": "yyyy-MM-dd HH:mm:ss.SSSSSS"
                    }
                }
            }
        }
        try:
            # res1 = self.es.count(self.index, self.data_point_type_name, query1)
            # # first determine size, otherwise it returns only 10 data (by default)
            # size = res1['count']
            # if size is None:
            #     size = 10000

            # https://stackoverflow.com/questions/9084536/sorting-by-multiple-params-in-pyes-and-elasticsearch
            # sorting is required for proper visualization of data
            res = self.es.search(index=self.index, doc_type=self.data_point_type_name, body=query2, size=10000, sort='createdDate')
            return [r["_source"] for r in res["hits"]["hits"]]
        except ConnectionError as err1:
            error("ConnectionError while retrieving data points from elasticsearch. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while retrieving data points. Check type mappings for experiments in experiment_db_config.json.")
            raise err2

    def clear_db(self):
        try:
            if self.es.ping():
                self.indices_client.delete(index=self.index, ignore=[400, 404])  # remove all records
                self.indices_client.create(index=self.index, body=self.body)
        except ConnectionError as err1:
            error("ConnectionError while clearing database. Check connection to elasticsearch.")
            raise err1
        except TransportError as err2:
            error("TransportError while clearing database. Check type mappings for experiments in experiment_db_config.json.")
            raise err2

    def get_stages_count(self, experiment_id):
        res = self.es.get(index=self.index, doc_type=self.experiment_type_name, id=experiment_id, _source=["executionStrategy"])
        if "stages_count" not in res["_source"]["executionStrategy"]:
            error("'stages_count' does not exist in experiment strategy with id " + experiment_id)
            return 0
        return res["_source"]["executionStrategy"]["stages_count"]

    def get_data_for_analysis(self, experiment_id):
        data = dict()
        knobs = dict()
        stages = self.get_stages(experiment_id=experiment_id)
        print("retrieved_stages", stages)
        if len(stages[0]) > 0 and len(stages[1]) > 0:
            stage_ids = stages[0]
            sources = stages[1]
            for idx, stage_id in enumerate(stage_ids):
                data_points = self.get_data_points(experiment_id=experiment_id, stage_no=idx)
                if len(data_points) > 1:
                    print("data_points", data_points)
                    data[stage_id] = [d for d in data_points]
                    knobs[stage_id] = sources[idx]["knobs"]
            # return value 1 (data): is a key-value pair where key is stage_id and value is array of all data points of that stage,
            # return value 2 (knobs): is a key-value pair where key is stage_id and value is knob object of that stage
            return data, knobs
        raise Exception("Cannot retrieve stage and data from db, please restart")
