import {NotificationsService} from "angular2-notifications";
import {LoggerService} from "../modules/helper/logger.service";
import {Injectable} from "@angular/core";
import {Entity, OedaCallbackEntity, UserEntity} from "../modules/api/oeda-api.service";
import {isNullOrUndefined} from "util";

@Injectable()
export class EntityService {

  constructor(public notify: NotificationsService, public log: LoggerService) {}

  public create_entity(): Entity {
    return {
      number: "",
      values: [],
      knobs: null
    }
  }

  /** returns data of the selected stage from all_data structure */
  public get_data_from_local_structure(all_data, stage_no) {
    let retrieved_data = all_data[stage_no - 1];
    if (retrieved_data !== undefined) {
      // if (retrieved_data.values.length === 0) {
      //   this.notify.error("Error", "Selected stage might not contain data points. Please select another stage.");
      //   return;
      // }
      return retrieved_data;
    } else {
      this.notify.error("Error", "Cannot retrieve data from local storage");
      return;
    }

  }

  /** parses single stage data with given attributes & scale, and returns values in array */
  public process_single_stage_data(single_stage_object, xAttribute, yAttribute, scale, incoming_data_type_name, called_for_successful_experiment): Array<number> {
    const ctrl = this;
    try {
      if (single_stage_object !== undefined) {
        const processedData = [];
        // Parsing string into json should only be done here.
        if (called_for_successful_experiment) {
          single_stage_object = JSON.parse(single_stage_object);
        }
        single_stage_object.values.forEach(function(data_point) {
          // filter out points that are retrieved from other data providers, o/w they will be undefined
          if (!isNullOrUndefined(data_point["payload"][incoming_data_type_name])){
            // first check if log value can be calculated properly
            if (scale === "Log" && data_point["payload"][incoming_data_type_name] <= 0) {
              let err = {};
              err["message"] = "Log scale cannot be applied to "  + incoming_data_type_name;
              throw(err);
            }
            if (xAttribute !== null && yAttribute !== null) {
              const newElement = {};
              newElement[xAttribute] = data_point["created"];
              // if (incoming_data_type_name === "lastTickDuration" || incoming_data_type_name === "routingDuration") {
              //   console.log(data_point["payload"][incoming_data_type_name]);
              // }

              if (scale === "Log") {
                newElement[yAttribute] = Math.log(data_point["payload"][incoming_data_type_name]);
              } else if (scale === "Normal") {

                newElement[yAttribute] = data_point["payload"][incoming_data_type_name];
              } else {
                ctrl.notify.error("Error", "Please provide a valid scale");
                return;
              }
              processedData.push(newElement);
            } else {
              // this is for plotting qq plot with JS, as it only requires raw data in log or normal scale
              if (scale === "Log") {
                processedData.push(Math.log(data_point["payload"][incoming_data_type_name]));
              } else if (scale === "Normal") {
                processedData.push(data_point["payload"][incoming_data_type_name]);
              } else {
                ctrl.notify.error("Error", "Please provide a valid scale");
                return;
              }
            }
        }
        });
        return processedData;
      }
    } catch (err) {
      this.notify.error("Error", err.message);
      throw err;
    }
  }

  /** stage object contains more than one stages here */
  public process_all_stage_data(all_stage_object, xAttribute, yAttribute, scale, incoming_data_type_name, called_for_successful_experiment): Array<number> {
    const ctrl = this;
    try {
      if (all_stage_object !== undefined) {
        const processedData = [];

        all_stage_object.forEach(function(single_stage_object) {
          const data_array = ctrl.process_single_stage_data(single_stage_object, xAttribute, yAttribute, scale, incoming_data_type_name, called_for_successful_experiment);
          data_array.forEach(function(data_value){
            processedData.push(data_value);
          });
        });
        return processedData;
      } else {
        this.notify.error("Error", "Failed to process all stage data");
      }
    } catch (err) {
      this.notify.error("Error", err.message);
      throw err;
    }
  }

  /** https://stackoverflow.com/questions/979256/sorting-an-array-of-javascript-objects */
  public sort_by(field, reverse, primer) {
    if (!isNullOrUndefined(field)) {
      const key = function (x) {return primer ? primer(x[field]) : x[field]};
      return function (a, b) {
        const A = key(a), B = key(b);
        return ( (A < B) ? -1 : ((A > B) ? 1 : 0) ) * [-1, 1][+!!reverse];
      }
    }
    return function (a, b) {
      return ( (a < b) ? -1 : ((a > b) ? 1 : 0) ) * [-1, 1][+!!reverse];
    }

  }

  /** parses static response object returned from server, creates new stage-point tuple(s) and pushes them to the all_data (array of json strings) */
  public process_response_for_successful_experiment(response, all_data): Entity[] {
    if (isNullOrUndefined(response)) {
      this.notify.error("Error", "Cannot retrieve data from DB, please try again");
      return;
    }

    // we can retrieve more than one array of stages and data points
    for (const index in response) {
      if (response.hasOwnProperty(index)) {
        const parsed_json_object = JSON.parse(response[index]);
        // distribute data points to empty bins
        const new_entity = this.create_entity();
        new_entity.number = parsed_json_object['number'].toString();
        new_entity.values = parsed_json_object['values'];
        new_entity.knobs = parsed_json_object['knobs'];
        // important assumption here: we retrieve stages and data points in a sorted manner with respect to created field
        // thus, pushed new_entity will have a key of its "number" with this assumption
        // e.g. [ 0: {number: 1, values: ..., knobs: [...]}, 1: {number: 2, values: ..., knobs: [...] }...]
        all_data.push(new_entity);
      }
    }
    return all_data;
  }

  public create_oeda_callback_entity(): OedaCallbackEntity {
    return {
      status: "Initializing...",
      message: "",
      index: 0,
      size: 0,
      complete: 0,
      experiment_counter: 0,
      total_experiments: 0,
      stage_counter: null,
      current_knob: new Map<string, number>(),
      remaining_time_and_stages: new Map<any, any>()
    };
  }

  public create_user_entity(): UserEntity {
    return {
      name: "",
      password: "",
      db_configuration: new Map<string, string>()
    };
  }

}
