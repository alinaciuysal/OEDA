import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Params, Router} from '@angular/router';
import {NotificationsService} from "angular2-notifications";
import {LayoutService} from "../../../../shared/modules/helper/layout.service";
import {PlotService} from "../../../../shared/util/plot-service";
import {EntityService} from "../../../../shared/util/entity-service";
import {Experiment, Target, OEDAApiService, StageEntity} from "../../../../shared/modules/api/oeda-api.service";
import {AmChartsService, AmChart} from "@amcharts/amcharts3-angular";
import {isNullOrUndefined} from "util";

@Component({
  selector: 'show-successful-experiment',
  templateUrl: './show-successful-experiment.component.html'
})

export class ShowSuccessfulExperimentComponent implements OnInit {
  private scatter_plot: AmChart;
  private histogram: AmChart;
  private first_render_of_page: boolean;
  private all_data: StageEntity[];
  private decimal_places: number;
  public stage_details: string;

  public dataAvailable: boolean;
  public is_collapsed: boolean;
  public incoming_data_type: object;
  public experiment_id: string;
  public experiment: Experiment;
  public targetSystem: Target;

  public initial_threshold_for_scatter_chart: number;
  public retrieved_data_length: number; // number of data points retrieved so far

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

  constructor(private layout: LayoutService,
              private apiService: OEDAApiService,
              private plotService: PlotService,
              private entityService: EntityService,
              private AmCharts: AmChartsService,
              private activated_route: ActivatedRoute,
              private router: Router,
              private notify: NotificationsService) {

    this.decimal_places = 3;
    this.dataAvailable = false;
    this.is_all_stages_selected = false;
    this.is_qq_plot_rendered = false;
    this.qqJSPlotIsRendered = false;
    this.is_enough_data_for_plots = false;
    this.is_collapsed = true;
    this.first_render_of_page = true;
    this.all_data = [];
    this.retrieved_data_length = 0;
    this.scale = "Normal";
    this.stage_details = "All Stages";

    this.distribution = "Norm";
    this.available_distributions = ['Norm', 'Gamma', 'Logistic', 'T', 'Uniform', 'Lognorm', 'Loggamma'];

    this.selected_stage_for_qq_js = "Select a stage";
    this.incoming_data_type = null;

    // subscribe to router event
    this.activated_route.params.subscribe((params: Params) => {
      // id is retrieved from URI
      if (params["id"] && this.router.url.toString().includes("/control/experiments/show")) {
        this.experiment_id = params["id"];
      }

      // distinguish between successful and interrupted
      if (this.router.url.toString().includes("interrupted")) {
        this.layout.setHeader("Interrupted Experiment Results", "");
      } else if (this.router.url.toString().includes("success")) {
        this.layout.setHeader("Successful Experiment Results", "");
      } else {
        this.layout.setHeader("Experiment Results", "");
      }
    });
  }
  /* tslint:disable */

  ngOnInit() {

    if (!isNullOrUndefined(this.experiment_id)) {
      this.apiService.loadExperimentById(this.experiment_id).subscribe(experiment => {

        if (!isNullOrUndefined(experiment)) {
          this.experiment = experiment;
          if (!isNullOrUndefined(experiment.targetSystemId) && !isNullOrUndefined(experiment.targetSystemId)) {

            // retrieve target system
            this.apiService.loadTargetById(experiment.targetSystemId).subscribe(targetSystem => {
              if (!isNullOrUndefined(targetSystem)) {
                this.targetSystem = targetSystem;
                // retrieve stages
                this.apiService.loadAvailableStagesWithExperimentId(this.experiment_id).subscribe(stages => {
                  if (!isNullOrUndefined(stages)) {
                    console.log(stages);
                    // initially selected stage is "All Stages"
                    this.selected_stage = {"number": -1, "knobs": {}};
                    this.selected_stage.knobs = this.entityService.populate_knob_objects_with_variables(this.selected_stage.knobs, this.targetSystem.defaultVariables, true, this.experiment.executionStrategy.type);
                    this.available_stages.push(this.selected_stage);
                    for (let j = 0; j < stages.length; j++) {
                      // if there are any existing stages, round their values of stages to provided decimal places
                      if (!isNullOrUndefined(stages[j]["knobs"])) {
                        stages[j]["knobs"] = this.entityService.round_knob_values(stages[j]["knobs"], this.decimal_places);
                        stages[j]["knobs"] = this.entityService.populate_knob_objects_with_variables(stages[j]["knobs"], this.targetSystem.defaultVariables, false, this.experiment.executionStrategy.type);
                        stages[j]["stage_result"] = Number(stages[j]["stage_result"].toFixed(this.decimal_places));
                      }
                      this.available_stages.push(stages[j]);
                    }
                    stages.sort(this.entityService.sort_by('number', true, parseInt));
                    // prepare available stages for qq js that does not include all stages
                    this.available_stages_for_qq_js = this.available_stages.slice(1);
                    this.dataAvailable = true;
                    this.fetch_data();
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

  /** uses stage_object (that can be either one stage or all_stage) and PlotService to draw plots accordingly */
  draw_all_plots(stage_object) {
    const ctrl = this;
    if (stage_object !== undefined && stage_object.length !== 0) {
      ctrl.selectDistributionAndDrawQQPlot(ctrl.distribution);
      // draw graphs for all_data
      if (ctrl.selected_stage.number === -1) {
        try {
          let processedData = ctrl.entityService.process_all_stage_data(stage_object, "timestamp", "value", ctrl.scale, ctrl.incoming_data_type["name"], true);
          if (!isNullOrUndefined(processedData)) {
            // https://stackoverflow.com/questions/597588/how-do-you-clone-an-array-of-objects-in-javascript
            const clonedData = JSON.parse(JSON.stringify(processedData));
            ctrl.initial_threshold_for_scatter_chart = ctrl.plotService.calculate_threshold_for_given_percentile(clonedData, 95, 'value', ctrl.decimal_places);
            ctrl.scatter_plot = ctrl.plotService.draw_scatter_plot("chartdiv", "filterSummary", processedData, ctrl.incoming_data_type["name"], ctrl.initial_threshold_for_scatter_chart, "All Stages", ctrl.decimal_places, ctrl.experiment.executionStrategy.sample_size);            ctrl.histogram = ctrl.plotService.draw_histogram("histogram", processedData, ctrl.incoming_data_type["name"], "All Stages", ctrl.decimal_places);

            ctrl.is_enough_data_for_plots = true;
          } else {
            ctrl.notify.error("Error", "Selected scale might not be appropriate for the selected incoming data type");
            return;
          }
        } catch (err) {
          ctrl.is_enough_data_for_plots = false;
          ctrl.notify.error("Error", err.message);
          return;
        }
      }
      // draw graphs for selected stage data
      else {
        try {
          let processedData = ctrl.entityService.process_single_stage_data(stage_object,"timestamp", "value", ctrl.scale, ctrl.incoming_data_type["name"], true);
          if (!isNullOrUndefined(processedData)) {
            const clonedData = JSON.parse(JSON.stringify(processedData));
            ctrl.initial_threshold_for_scatter_chart = ctrl.plotService.calculate_threshold_for_given_percentile(clonedData, 95, 'value', ctrl.decimal_places);
            ctrl.stage_details = ctrl.entityService.get_stage_details(ctrl.selected_stage);
            ctrl.scatter_plot = ctrl.plotService.draw_scatter_plot("chartdiv", "filterSummary", processedData, ctrl.incoming_data_type["name"], ctrl.initial_threshold_for_scatter_chart, ctrl.stage_details, ctrl.decimal_places, ctrl.experiment.executionStrategy.sample_size);
            ctrl.histogram = ctrl.plotService.draw_histogram("histogram", processedData, ctrl.incoming_data_type["name"], ctrl.stage_details, ctrl.decimal_places);

            // check if next stage exists for javascript side of qq plot
            ctrl.available_stages_for_qq_js.some(function (element) {
              if (Number(element.number) == Number(ctrl.selected_stage.number) + 1) {
                ctrl.selected_stage_for_qq_js = (element.number).toString();
                ctrl.plotService.draw_qq_js("qqPlotJS", ctrl.all_data, ctrl.selected_stage, ctrl.selected_stage_for_qq_js, ctrl.scale, ctrl.incoming_data_type["name"], ctrl.decimal_places);
                ctrl.qqJSPlotIsRendered = true;
                return true; // required as a callback for .some function
              }
            });
            ctrl.is_enough_data_for_plots = true;
          }
        } catch (err) {
          ctrl.is_enough_data_for_plots = false;
          ctrl.notify.error("Error", err.message);
          return;
        }
      }
    }
  }

  /** called when theoretical distribution in QQ Plot's dropdown is changed */
  selectDistributionAndDrawQQPlot(distName) {
    this.distribution = distName;
    this.plotService.retrieve_qq_plot_image(this.experiment_id, this.selected_stage, this.distribution, this.scale, this.incoming_data_type["name"]).subscribe(response => {
      const imageSrc = 'data:image/jpg;base64,' + response;
      document.getElementById("qqPlot").setAttribute('src', imageSrc);
      this.is_qq_plot_rendered = true;
    }, err => {
      this.notify.error("Error", err.message);
    });
  }

  /** retrieves all_data from server */
  fetch_data() {
    const ctrl = this;
    this.apiService.loadAllDataPointsOfExperiment(this.experiment_id).subscribe(
      retrieved_data => {
        if (isNullOrUndefined(retrieved_data)) {
          this.notify.error("Error", "Cannot retrieve data from DB, please try again");
          return;
        }
        this.all_data = ctrl.entityService.process_response_for_successful_experiment(retrieved_data, this.all_data);
        for (let stage_data of this.all_data) {
          this.retrieved_data_length += stage_data['values'].length;
        }

        if(this.first_render_of_page) {
          if(this.incoming_data_type == null)
            this.incoming_data_type = this.entityService.get_candidate_data_type(this.experiment, this.targetSystem, this.all_data[0]);
          this.first_render_of_page = false;
        }
        this.draw_all_plots(this.all_data);
      }
    );
  }

  /** called when stage dropdown (All Stages, Stage 1 [...], Stage 2 [...], ...) in main page is changed */
  stage_changed(selected_stage) {
    const ctrl = this;
    if (selected_stage !== null)
      ctrl.selected_stage = selected_stage;
    if (this.entityService.scale_allowed(this.scale, this.incoming_data_type["scale"])) {
      if (!isNullOrUndefined(ctrl.selected_stage.number)) {
        if (ctrl.selected_stage.number === -1) {
          if (!isNullOrUndefined(ctrl.all_data)) {
            // redraw plots with all data that was previously retrieved
            ctrl.draw_all_plots(ctrl.all_data);
          } else {
            // fetch data from server again and draw plots
            ctrl.fetch_data();
          }
        } else {
          /*
            Draw plots for the selected stage by retrieving it from local storage
          */
          const stage_data = ctrl.entityService.get_data_from_local_structure(ctrl.all_data, ctrl.selected_stage.number);
          if (!isNullOrUndefined(stage_data)) {
            ctrl.draw_all_plots(stage_data);
          } else {
            ctrl.notify.error("", "Please select another stage");
            return;
          }
        }
      } else {
        ctrl.notify.error("Error", "Stage number is null or undefined, please try again");
        return;
      }
    } else {
      // inform user and remove graphs from page for now
      this.is_enough_data_for_plots = false;
      this.notify.error(this.scale + " scale cannot be applied to " + this.incoming_data_type["name"]);
    }
  }

  /** called when incoming data type of the target system is changed
   * for_initial_processing flag is true when we determine the candidate data type by looking at the payload retrieved
   * use-case: */
  incoming_data_type_changed(incoming_data_type) {
    this.incoming_data_type = incoming_data_type;
    if (this.entityService.scale_allowed(this.scale, this.incoming_data_type["scale"])) {
      // trigger plot drawing process via stage_changed function
      this.stage_changed(null);
    } else {
      // inform user and remove graphs from page for now
      this.is_enough_data_for_plots = false;
      this.notify.error(this.scale + " scale cannot be applied to " + this.incoming_data_type["name"]);
    }
  }
  /** called when scale dropdown (Normal, Log) in main page is changed */
  scale_changed(user_selected_scale) {
    this.scale = user_selected_scale;
    if (this.entityService.scale_allowed(this.scale, this.incoming_data_type["scale"])) {
      // trigger plot drawing process via stage_changed function
      this.stage_changed(null);
    } else {
      // inform user and remove graphs from page for now
      this.is_enough_data_for_plots = false;
      this.notify.error(this.scale + " scale cannot be applied to " + this.incoming_data_type["name"]);
    }
  }

  is_considered(data_type_name) {
    return this.entityService.is_considered(this.experiment.considered_data_types, data_type_name);
  }

  /** called when selected stage dropdown in QQ JS is changed */
  selectStageNoForQQJS(selected_stage_for_qq_js) {
    this.selected_stage_for_qq_js = selected_stage_for_qq_js;
    this.plotService.draw_qq_js("qqPlotJS", this.all_data, this.selected_stage, this.selected_stage_for_qq_js, this.scale, this.incoming_data_type["name"], this.decimal_places);
    this.qqJSPlotIsRendered = true;
  }
}
