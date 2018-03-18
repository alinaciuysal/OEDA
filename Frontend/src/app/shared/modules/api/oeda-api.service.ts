import {Injectable} from "@angular/core";
import {NotificationsService} from "angular2-notifications";
import {AuthHttp} from "angular2-jwt";
import {Http, Response} from "@angular/http";
import {RESTService} from "../../util/rest-service";
import {LoggerService} from "../helper/logger.service";
import {Observable} from "rxjs/Observable";


@Injectable()
export class OEDAApiService extends RESTService {

  constructor(http: Http, authHttp: AuthHttp, notify: NotificationsService, log: LoggerService) {
    super(http, authHttp, notify, log);
  }

  public loadAllExperiments(): Observable<Experiment[]> {
    return this.doGETPublicRequest("/experiments")
  }

  public loadExperimentById(experiment_id: string): Observable<Experiment> {
    return this.doGETPublicRequest("/experiments/" + experiment_id)
  }

  public loadAllDataPointsOfExperiment(experiment_id: string): Observable<any> {
    return this.doGETPublicRequest("/experiment_results/" + experiment_id)
  }

  public loadAllDataPointsOfRunningExperiment(experiment_id: string, timestamp: string): Observable<any> {
    return this.doGETPublicRequest("/running_experiment_results/" + experiment_id + "/" + timestamp)
  }

  public loadAvailableStagesWithExperimentId(experiment_id: string): Observable<any> {
    return this.doGETPublicRequest("/stages/" + experiment_id)
  }

  public getOedaCallback(experiment_id: string): Observable<any> {
    return this.doGETPublicRequest("/running_experiment_results/oeda_callback/" + experiment_id)
  }

  public getQQPlot(experiment_id: string, stage_no: string, distribution: string, scale: string, incoming_data_type_name: string): Observable<any> {
    return this.doGETPublicRequest("/qqPlot/" + experiment_id + "/" + stage_no + "/" + distribution + "/" + scale + "/" + incoming_data_type_name);
  }

  public getConfigFromAPI(url: string): Observable<any> {
    return this.doGETPublicRequestForConfig(url)
  }

  public saveExperiment(experiment: Experiment): Observable<any> {
    return this.doPOSTPublicRequest("/experiments/" + experiment.id, experiment)
  }

  public updateExperiment(experiment: Experiment): Observable<any> {
    return this.doPUTPublicRequest("/experiments/" + experiment.id, experiment)
  }

  public loadAllTargets(): Observable<Target[]> {
    return this.doGETPublicRequest("/targets")
  }

  public loadTargetById(id: string): Observable<Target> {
    return this.doGETPublicRequest("/targets/" + id)
  }

  public saveTarget(target: Target): Observable<Target> {
    return this.doPOSTPublicRequest("/targets/" + target.id, target)
      .map((res: Response) => res.json())
  }

  public updateTarget(target: Target): Observable<any> {
    return this.doPUTPublicRequest("/targets/" + target.id, target)
  }

  public updateUser(user: UserEntity): Observable<any> {
    return this.doPOSTPublicRequest("/user/" + user.name, user);
  }

  public registerUser(user: UserEntity): Observable<any> {
    return this.doPOSTPublicRequest("/auth/register", user);
  }

  // remove in production
  public clear_database(): Observable<any> {
    return this.doGETPublicRequest("/delete");
  }
}

export interface Experiment {
  id: string,
  name: string,
  description: string,
  status: string,
  targetSystemId: string,
  changeableVariables: any,
  executionStrategy: ExecutionStrategy,
  optimized_data_types: object[]
}

export interface StageEntity {
  number: string,
  values: object[],
  knobs: any
}


export interface Target {
  id: string,
  name: string,
  status: string,
  description: string,
  dataProviders: any, // generic one
  primaryDataProvider: any,
  secondaryDataProviders: any,
  changeProvider: any,
  incomingDataTypes: any,
  changeableVariables: any,
  defaultVariables: any
}

export interface ExecutionStrategy {
  type: string,
  sample_size: number,
  knobs: any,
  stages_count: number,
  optimizer_iterations_in_design: number,
  optimizer_iterations: number,
  acquisition_method: any
}

export interface OedaCallbackEntity {
  status: string,
  message: string,
  index: number,
  size: number,
  complete: number,
  experiment_counter: number,
  total_experiments: number,
  stage_counter: number,
  current_knob: any,
  remaining_time_and_stages: any
}

export interface Configuration {
  host: string,
  port: number,
  type: string
}

export interface UserEntity {
  name: string,
  password: string,
  db_configuration: Map<string, string>
}
