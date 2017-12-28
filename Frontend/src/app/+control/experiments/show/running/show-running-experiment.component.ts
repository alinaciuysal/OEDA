import {Component, OnInit, OnDestroy} from '@angular/core';
import {ActivatedRoute, Params, Router} from '@angular/router';
import {NotificationsService} from "angular2-notifications";
import {LayoutService} from "../../../../shared/modules/helper/layout.service";
import {Experiment, Target, OEDAApiService, Entity, OedaCallbackEntity} from "../../../../shared/modules/api/oeda-api.service";
import {AmChart} from "@amcharts/amcharts3-angular";
import {isNullOrUndefined} from "util";
import {Observable} from "rxjs/Observable";
import {PlotService} from "../../../../shared/util/plot-service";
import {EntityService} from "../../../../shared/util/entity-service";

@Component({
  selector: 'show-running-experiment',
  templateUrl: './show-running-experiment.component.html'
})

// QQ plot reference: https://gist.github.com/mbostock/4349187

export class ShowRunningExperimentComponent implements OnInit, OnDestroy {
  private scatter_plot: AmChart;
  private histogram: AmChart;

  public dataAvailable: boolean;
  public is_collapsed: boolean;

  private divId: string;
  private histogramDivId: string;
  private qqPlotDivId: string;
  private qqPlotDivIdJS: string;
  private filterSummaryId: string;
  private histogramLogDivId: string;
  private processedData: object;
  private timer: any;
  private subscription: any;
  private first_render_of_page: boolean;
  private first_render_of_plots: boolean;
  private experiment_ended: boolean;
  private timestamp: string;
  private incoming_data_type_name: string;

  private all_data: Entity[];

  public experiment_id: string;
  public experiment: Experiment;
  public targetSystem: Target;

  public initial_threshold_for_scatter_plot: number;

  // following attributes are used for QQ plotting in Python
  public available_distributions: object;
  public distribution: string;
  public scale: string;
  public is_qq_plot_rendered: boolean;

  public selected_stage_for_qq_js: string;
  public qqJSPlotIsRendered: boolean;
  public is_enough_data_for_plots: boolean;
  public is_all_stages_selected: boolean;

  public available_stages = [];
  public available_stages_for_qq_js = [];

  public selected_stage: any;
  public oedaCallback: OedaCallbackEntity;


  constructor(private layout: LayoutService,
              private apiService: OEDAApiService,
              private entityService: EntityService,
              private plotService: PlotService,
              private activated_route: ActivatedRoute,
              private router: Router,
              private notify: NotificationsService) {

    this.layout.setHeader("Experiment Results", "");
    this.dataAvailable = false;
    this.is_all_stages_selected = false;
    this.is_qq_plot_rendered = false;
    this.qqJSPlotIsRendered = false;
    this.is_enough_data_for_plots = false;
    this.experiment_ended = false;
    this.is_collapsed = true;
    this.first_render_of_page = true;
    this.all_data = [];
    this.scale = "Normal";
    this.first_render_of_plots = true;

    this.distribution = "Norm";
    this.available_distributions = ['Norm', 'Gamma', 'Logistic', 'T', 'Uniform', 'Lognorm', 'Loggamma'];

    this.selected_stage_for_qq_js = "Select a stage";
    this.oedaCallback = this.entityService.create_oeda_callback_entity();


    this.divId = "chartdiv";
    this.histogramDivId = "histogram";
    this.histogramLogDivId = "histogram_log";
    this.filterSummaryId = "filterSummary";
    this.qqPlotDivId = "qqPlot";
    this.qqPlotDivIdJS = "qqPlotJS";

    // subscribe to router event
    this.activated_route.params.subscribe((params: Params) => {
      // id is retrieved from URI
      if (params["id"] && this.router.url.toString().includes("/control/experiments/show")) {
        this.experiment_id = params["id"];
      }
    });
  }

  /* tslint:disable */

  ngOnDestroy() {
    this.subscription.unsubscribe();
  }

  ngOnInit() {
    if (!isNullOrUndefined(this.experiment_id)) {
      this.apiService.loadExperimentById(this.experiment_id).subscribe(experiment => {
        if (!isNullOrUndefined(experiment)) {
          this.experiment = experiment;
          this.experiment.id = this.experiment_id;
          if (!isNullOrUndefined(experiment.targetSystemId)) {
            // retrieve target system
            this.apiService.loadTargetById(experiment.targetSystemId).subscribe(targetSystem => {
              if (!isNullOrUndefined(targetSystem)) {
                this.targetSystem = targetSystem;
                this.targetSystem.id = this.experiment.targetSystemId;
                this.incoming_data_type_name = targetSystem.incomingDataTypes[0]["name"].toString();
                // retrieve stages
                this.apiService.loadAvailableStagesWithExperimentId(this.experiment_id).subscribe(stages => {
                  if (!isNullOrUndefined(stages)) {
                    // initially selected stage is "All Stages"
                    this.selected_stage = {"number": -1, "knobs": ""};
                    this.available_stages.push(this.selected_stage);
                    for (let j = 0; j < stages.length; j++) {
                      this.available_stages.push(stages[j]);
                    }
                    stages.sort(this.entityService.sort_by('number', true, parseInt));

                    // prepare available stages for qq js that does not include all stages
                    this.available_stages_for_qq_js = this.available_stages.slice(1);
                    this.dataAvailable = true;

                    // polling using Timer (2 sec interval) for real-time data visualization
                    this.timer = Observable.timer(1000, 2000);

                    this.subscription = this.timer.subscribe(t => {
                      this.fetch_oeda_callback();
                    });

                  }
                });
              }
            });
          }
        } else {
          this.notify.error("Error", "Cannot retrieve details of selected experiment, make sure DB is up and running");
        }
      });
    } else {
      this.notify.error("Error", "Failed retrieving experiment id, please check URI");
    }

  }

  private fetch_oeda_callback() {
    const ctrl = this;

    ctrl.apiService.getOedaCallback(ctrl.experiment_id).subscribe(oedaCallback => {
      if(!isNullOrUndefined(oedaCallback)) {
        console.log(oedaCallback);
        ctrl.oedaCallback["status"] = oedaCallback.status;
        ctrl.oedaCallback["stage_counter"] = oedaCallback.stage_counter;

        // keywords (index, size) are same for the first two cases, but they indicate different things
        if (oedaCallback.status.toString() === "PROCESSING") {
          ctrl.oedaCallback["message"] = oedaCallback.message;
        } else if (oedaCallback.status.toString() === "IGNORING_SAMPLES") {
          ctrl.oedaCallback["index"] = oedaCallback.index;
          ctrl.oedaCallback["size"] = oedaCallback.size;
          ctrl.oedaCallback["complete"] = (Number(oedaCallback.index)) / (Number(oedaCallback.size));
          ctrl.oedaCallback.current_knob = oedaCallback.current_knob;
          // remaining_time_and_stages is a experiment-wise unique dict that contains remaining stages and time
          ctrl.oedaCallback.remaining_time_and_stages = oedaCallback.remaining_time_and_stages;

          if (oedaCallback.remaining_time_and_stages === undefined)
            ctrl.oedaCallback.remaining_time_and_stages["remaining_stages"] = ctrl.experiment.executionStrategy.sample_size;
          else
            ctrl.oedaCallback.remaining_time_and_stages["remaining_stages"] = ctrl.oedaCallback.remaining_time_and_stages.remaining_stages;

          if (oedaCallback.remaining_time_and_stages["remaining_time"] !== undefined)
            ctrl.oedaCallback.remaining_time_and_stages["remaining_time"] = oedaCallback.remaining_time_and_stages["remaining_time"];

        } else if (oedaCallback.status.toString() === "COLLECTING_DATA") {
          ctrl.oedaCallback["index"] = oedaCallback.index;
          ctrl.oedaCallback["size"] = oedaCallback.size;
          ctrl.oedaCallback["complete"] = (Number(oedaCallback.index)) / (Number(oedaCallback.size));
          ctrl.oedaCallback.current_knob = oedaCallback.current_knob;
          // remaining_time_and_stages is a experiment-wise unique dict that contains remaining stages and time
          ctrl.oedaCallback.remaining_time_and_stages = oedaCallback.remaining_time_and_stages;

          if (oedaCallback.remaining_time_and_stages["remaining_stages"] === undefined)
            ctrl.oedaCallback.remaining_time_and_stages["remaining_stages"] = ctrl.experiment.executionStrategy.sample_size;
          else
            ctrl.oedaCallback.remaining_time_and_stages["remaining_stages"] = ctrl.oedaCallback.remaining_time_and_stages.remaining_stages;

          if (oedaCallback.remaining_time_and_stages["remaining_time"] !== undefined)
            ctrl.oedaCallback.remaining_time_and_stages["remaining_time"] = oedaCallback.remaining_time_and_stages["remaining_time"];


          if (ctrl.first_render_of_page) {
            ctrl.apiService.loadAllDataPointsOfExperiment(ctrl.experiment_id).subscribe(response => {
              let is_successful_fetch = ctrl.entityService.process_response_for_running_experiment(response, ctrl.all_data, ctrl.first_render_of_page, ctrl.available_stages, ctrl.available_stages_for_qq_js, ctrl.timestamp);
              if (is_successful_fetch) {
                ctrl.first_render_of_page = false;
                ctrl.draw_all_plots();
              }
            });
          } else {
            if (ctrl.timestamp == undefined) {
              ctrl.timestamp = "-1";
            }
            ctrl.apiService.loadAllDataPointsOfRunningExperiment(ctrl.experiment_id, ctrl.timestamp).subscribe(response => {
              ctrl.entityService.process_response_for_running_experiment(response, ctrl.all_data, ctrl.first_render_of_page, ctrl.available_stages, ctrl.available_stages_for_qq_js, ctrl.timestamp);
              ctrl.draw_all_plots();
            });
          }
        } else if (oedaCallback.status.toString() === "EXPERIMENT_STAGE_DONE") {
          if (oedaCallback.remaining_time_and_stages["remaining_stages"] == 0) {
            ctrl.disable_polling("Success", "Data is up-to-date, stopped polling.");

            // switch to successful experiment page to show other plots to the user
            ctrl.router.navigate(["control/experiments/show/"+ctrl.experiment_id+"/success"]).then(() => {
              console.log("navigated to successful experiments page");
            });
          }
        }
      }
    });
  }

  /** uses stage_object (that can be either one stage or all_stage) and PlotService to draw plots accordingly */
  private draw_all_plots() {
    const ctrl = this;
    // set it to false in case a new scale is selected
    ctrl.is_enough_data_for_plots = false;


    // if "all stages" is selected
    if (ctrl.selected_stage.number == -1) {
      var start = new Date().getTime();
      ctrl.processedData = ctrl.entityService.process_all_stage_data(ctrl.all_data, "timestamp", "value", ctrl.scale, ctrl.incoming_data_type_name, false);
      var end = new Date().getTime();
      var time = end - start;
      console.log('process_all_stage_data: ', time);
    }
    // if any other stage is selected
    else {
      ctrl.processedData = ctrl.all_data[ctrl.selected_stage.number - 1];
      var start2 = new Date().getTime();
      ctrl.processedData = ctrl.entityService.process_single_stage_data(ctrl.processedData,"timestamp", "value", ctrl.scale, ctrl.incoming_data_type_name);
      var end2 = new Date().getTime();
      var time2 = end2 - start2;
      console.log('process_single_stage_data: ', time2);
    }
    // https://stackoverflow.com/questions/597588/how-do-you-clone-an-array-of-objects-in-javascript
    const clonedData = JSON.parse(JSON.stringify(ctrl.processedData));
    ctrl.initial_threshold_for_scatter_plot = ctrl.plotService.calculate_threshold_for_given_percentile(clonedData, 95, 'value');

    if (ctrl.first_render_of_plots) {
      ctrl.scatter_plot = ctrl.plotService.draw_scatter_plot(ctrl.divId, ctrl.filterSummaryId, ctrl.processedData, ctrl.incoming_data_type_name, ctrl.initial_threshold_for_scatter_plot);
      ctrl.histogram = ctrl.plotService.draw_histogram(ctrl.histogramDivId, ctrl.processedData, ctrl.incoming_data_type_name);
      ctrl.first_render_of_plots = false;
    } else {
      // now create a new graph with updated values
      ctrl.scatter_plot.dataProvider = ctrl.processedData;
      var start3 = new Date().getTime();
      ctrl.scatter_plot.validateData();
      var end3 = new Date().getTime();
      var time3 = end3 - start3;
      console.log('validating scatter_plot data: ', time3);
      var start4 = new Date().getTime();
      ctrl.histogram.dataProvider = ctrl.plotService.categorize_data(ctrl.processedData);
      ctrl.histogram.validateData();
      var end4 = new Date().getTime();
      var time4 = end4 - start4;
      console.log('validating histogram data: ', time4);
    }
    ctrl.is_enough_data_for_plots = true;
  }

  /** called when stage dropdown (All Stages, Stage 1 [...], Stage 2 [...], ...) in main page is changed */
  stage_changed() {
    if (isNullOrUndefined(this.scale)) {
      this.notify.error("Error", "Scale is null or undefined, please try again");
      return;
    }
    this.draw_all_plots();
  }

  /** called when scale dropdown (Normal, Log) in main page is changed */
  scale_changed(scale: string) {
    this.scale = scale;
    this.stage_changed();
  }

  /** disables polling upon user click, and informs user */
  disable_polling(status: string, content: string) {
    document.getElementById("polling_off_button").setAttribute('class', 'btn btn-primary active');
    document.getElementById("polling_on_button").setAttribute('class', 'btn btn-default');
    this.subscription.unsubscribe();
    if (!isNullOrUndefined(status) && !isNullOrUndefined(content)) {
      this.notify.success(status, content);
    } else {
      this.notify.success("Success", "Polling disabled");
    }
  }

  /** re-creates the subscription object to periodically fetch data from server */
  enable_polling() {
    document.getElementById("polling_on_button").setAttribute('class', 'btn btn-primary active');
    document.getElementById("polling_off_button").setAttribute('class', 'btn btn-default');
    this.subscription = this.timer.subscribe(t => {
      this.fetch_oeda_callback();
    });
    this.notify.success("Success", "Polling enabled");
  }

  /** returns keys the given data structure */
  keys(object) : Array<string> { //this.oedaCallback.current_knob
    if (!isNullOrUndefined(object)) {
      return Object.keys(object);
    }
  }

  stopRunningExperiment(): void {
    alert("Do you really want to stop the running experiment?");
    this.experiment.status = "INTERRUPTED";
    this.apiService.updateExperiment(this.experiment).subscribe(response => {
      this.targetSystem.status = "READY";
      this.apiService.updateTarget(this.targetSystem).subscribe(response2 => {
        this.notify.success("Success", response.message);
      }, errorResp2 => {
        this.notify.error("Error", errorResp2.message);
      });
    }, errorResp => {
      this.notify.error("Error", errorResp.message);
    });
  }

  // helper function that filters out data above the given threshold
  filter_outliers(event) {
    const target = event.target || event.srcElement || event.currentTarget;
    const idAttr = target.attributes.id;
    const value = idAttr.nodeValue;
    console.log(target);
    console.log(idAttr);
    console.log(value);
  }
}
