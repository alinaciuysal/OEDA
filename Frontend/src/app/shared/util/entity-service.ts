import {NotificationsService} from "angular2-notifications";
import {LoggerService} from "../modules/helper/logger.service";
import {Injectable} from "@angular/core";
import {StageEntity, Experiment, OedaCallbackEntity, UserEntity} from "../modules/api/oeda-api.service";
import {isNullOrUndefined} from "util";

@Injectable()
/** This class provides methods related with experiment data object(s) that are retrieved from backend */
export class EntityService {

  private decimal_places: number;

  constructor(public notify: NotificationsService, public log: LoggerService) {
    this.decimal_places = 3;
  }

  /** returns data of the selected stage from all_data structure */
  public get_data_from_local_structure(all_data, stage_no) {
    let retrieved_data = all_data[stage_no - 1];
    if (retrieved_data !== undefined) {
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
        // if (called_for_successful_experiment) {
        //   single_stage_object = JSON.parse(single_stage_object);
        // }
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

              if (scale === "Log") {
                newElement[yAttribute] = Number(Math.log(data_point["payload"][incoming_data_type_name]).toFixed(ctrl.decimal_places));
              } else if (scale === "Normal") {
                newElement[yAttribute] = Number(data_point["payload"][incoming_data_type_name].toFixed(ctrl.decimal_places));
              } else {
                ctrl.notify.error("Error", "Please provide a valid scale");
                return;
              }
              processedData.push(newElement);
            } else {
              // this is for plotting qq plot with JS, as it only requires raw data in log or normal scale
              if (scale === "Log") {
                processedData.push(Number(Math.log(data_point["payload"][incoming_data_type_name]).toFixed(ctrl.decimal_places)));
              } else if (scale === "Normal") {
                processedData.push(Number(data_point["payload"][incoming_data_type_name].toFixed(ctrl.decimal_places)));
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
  public process_response_for_successful_experiment(response, all_data): StageEntity[] {
    if (isNullOrUndefined(response)) {
      this.notify.error("Error", "Cannot retrieve data from DB, please try again");
      return;
    }

    // we can retrieve more than one array of stages and data points
    for (const index in response) {
      if (response.hasOwnProperty(index)) {
        const parsed_json_object = JSON.parse(response[index]);
        // distribute data points to empty bins
        const new_entity = this.create_stage_entity();
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

  public create_stage_entity(): StageEntity {
    return {
      number: "",
      values: [],
      knobs: null
    }
  }

  /** we do not allow user to take Log of Nominal data */
  public scale_allowed(user_selected_scale, data_scale) {
    if (user_selected_scale === "Log" && data_scale === "Nominal") {
      return false;
    }
    return true;
  }

  /** returns true if payload object at index 0 contains the given incoming data type's name */
  public is_data_type_disabled(stage_data, incoming_data_type): boolean {
    if (stage_data !== undefined) {
      if (stage_data.hasOwnProperty("values")) {
        const first_tuple = stage_data.values;
        const first_payload = first_tuple[0]["payload"];
        if(first_payload.hasOwnProperty(incoming_data_type.name)){
          return false;
        }
      }
    }
    return true;
  }

  /** tries to set the initially-selected incoming data type name by looking at the payload and target system's optimized data type(s)
   *  we retrieve stages and data points in following format
   *  e.g. [ 0: {number: 1, values: ..., knobs: [...]}, 1: {number: 2, values: ..., knobs: [...] }...]
   *  this method should be called after checking whether it's the first render of page or not.
   *  because, if it's not the first time, then user's selection of incoming data type (via dropdown UI) is important
   *  but: before plotting, we must ensure that a proper & valid incoming data type is selected
   */
  public get_candidate_data_type(experiment, targetSystem, first_stage_data) {

    if (typeof first_stage_data === 'string') {
      first_stage_data = JSON.parse(first_stage_data);
    }

    // first check if we can get one of the optimized data types from payload
    for (let k = 0; k < experiment.optimized_data_types.length; k++) {
      const candidate_incoming_optimized_data_type = experiment.optimized_data_types[k];
      if (candidate_incoming_optimized_data_type["is_optimized"]) {
        if (!this.is_data_type_disabled(first_stage_data, candidate_incoming_optimized_data_type)) {
          return candidate_incoming_optimized_data_type;
        }
      }
    }

    // now check regular incoming data types
    for (let j = 0; j < targetSystem.incomingDataTypes.length; j++) {
      const candidate_incoming_data_type = targetSystem.incomingDataTypes[j];
        if (!this.is_data_type_disabled(first_stage_data, candidate_incoming_data_type)) {
          return candidate_incoming_data_type;
        }
    }
    return null;
  }

  /**
   * for successful experiments, we pass string representation
   * @param {selected_stage} JSON representation of selected stage object
   * @returns {string}
   */
  public get_stage_details(selected_stage: any): string {
    let details: string = "Stage: ";
    details += selected_stage["number"] + " ";
    let json_str = JSON.stringify(selected_stage["knobs"]);
    json_str = json_str.replace(/["']/g, "");
    json_str = json_str.replace(",", ", ");
    json_str = json_str.replace("{", "[");
    json_str = json_str.replace("}", "]");
    details += json_str;
    return details;
  }

  /**
   * iterates given knob object and round their values to given decimal number
   */
  public round_knob_values(iterable_knob_object: any, decimal: number) {
    Object.getOwnPropertyNames(iterable_knob_object).forEach(key => {
      let value = iterable_knob_object[key];
      iterable_knob_object[key] = Number(value.toFixed(decimal));
    });
    return iterable_knob_object;
  }

  /** returns keys of the given map */
  get_keys(object) : Array<string> {
    if (!isNullOrUndefined(object)) {
      return Object.keys(object);
    }
    return null;
  }

  /**
   * puts non-exiting knob keys & values to the actual knob object for a single stage entity.
   * All knob keys & values are iterated using targetSystem's defaultVariables
   * experimentKnobs: empty or non-empty object
   * targetSystemVariables: object[]
   * return value -> experimentKnobs: object
   */
  public populate_knob_objects_with_default_variables(experimentKnobs, targetSystemVariables) {
    let ctrl = this;
    let knob_keys = ctrl.get_keys(experimentKnobs);
    targetSystemVariables.forEach(function(target_system_knob, target_system_knob_index) {
      if (knob_keys.length > 0) {
        // knob_keys.forEach(function(experiment_knob_key) {
          if (!knob_keys.includes(target_system_knob.name)) {
            let not_found_knob_name = targetSystemVariables[target_system_knob_index].name;
            experimentKnobs[not_found_knob_name] = targetSystemVariables[target_system_knob_index].default;
          }
        // });
      } else {
        // this case is for populating all_stage, initially experimentKnobs is an empty Map
        experimentKnobs[target_system_knob.name] = target_system_knob.default;
      }
    });
    return experimentKnobs
  }
}
