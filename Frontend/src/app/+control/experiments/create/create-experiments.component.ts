import {OnInit, Component} from "@angular/core";
import {NotificationsService} from "angular2-notifications";
import {Router} from "@angular/router";
import {LayoutService} from "../../../shared/modules/helper/layout.service";
import {OEDAApiService, Experiment, Target, ExecutionStrategy} from "../../../shared/modules/api/oeda-api.service";
import * as _ from "lodash.clonedeep";
import {UUID} from "angular2-uuid";
import {isNull, isNullOrUndefined} from "util";
import {TempStorageService} from "../../../shared/modules/helper/temp-storage-service";
import {forEach} from "@angular/router/src/utils/collection";
import {EntityService} from "../../../shared/util/entity-service";
import {hasOwnProperty} from "tslint/lib/utils";


@Component({
  selector: 'control-experiments',
  templateUrl: './create-experiments.component.html',
})
export class CreateExperimentsComponent implements OnInit {
  experiment: Experiment;
  originalExperiment: Experiment;
  availableTargetSystems: any;
  targetSystem: any;
  executionStrategy: any;
  variable: any;
  initialVariables: any;
  selectedTargetSystem: any;
  stages_count: any;
  is_collapsed: boolean;
  errorButtonLabel: string;
  aggregateFunctionsMetric: any;
  aggregateFunctionsBoolean: any;

  constructor(private layout: LayoutService, private api: OEDAApiService,
              private router: Router, private notify: NotificationsService,
              private temp_storage: TempStorageService, private entityService: EntityService) {
    this.availableTargetSystems = [];
    this.initialVariables = [];

    // create experiment, target system, and execution strategy
    this.executionStrategy = this.entityService.create_execution_strategy();
    this.targetSystem = this.entityService.create_target_system();
    this.experiment = this.entityService.create_experiment(this.executionStrategy);
    this.originalExperiment = _(this.experiment);
    this.stages_count = null;
    this.is_collapsed = true;
    /** TODO: add support for other scales */
    this.aggregateFunctionsMetric = [
      {key:'avg',label:'Average'},
      {key:'min',label:'Min'},
      {key:'max',label:'Max'},
      {key:'count',label:'Count'},
      {key:'sum',label:'Sum'},
      {key:'percentiles-1', label:'1st Percentile'},
      {key:'percentiles-5', label:'5th Percentile'},
      {key:'percentiles-25', label:'25th Percentile'},
      {key:'percentiles-50', label:'50th Percentile (median)'},
      {key:'percentiles-75', label:'75th Percentile'},
      {key:'percentiles-95', label:'95th Percentile'},
      {key:'percentiles-99', label:'99th Percentile'},
      {key:'sum_of_squares', label:'Sum of Squares'},
      {key:'variance', label:'Variance'},
      {key:'std_deviation', label:'Std. Deviation'}
    ];
    this.aggregateFunctionsBoolean = [
      {key:'ratio-True',label:'True Ratio'},
      {key:'ratio-False',label:'False Ratio'}
    ];
  }

  ngOnInit(): void {
    const ctrl = this;
    ctrl.layout.setHeader("Create an Experiment", "");
    ctrl.api.loadAllTargets().subscribe(
      (data) => {
        if (!isNullOrUndefined(data)) {
          for (var k = 0; k < data.length; k++) {
            if (data[k]["status"] === "READY") {
              ctrl.availableTargetSystems.push(data[k]);
            }
          }
        } else {
          this.notify.error("Error", "Please create target system first");
        }
      }
    );
  }

  saveExperiment() {
    if (!this.hasErrors()) {
      let all_knobs = [];
      let experiment_type = this.experiment.executionStrategy.type;
      // push names & default values of target system to executionStrategy for forever strategy if there are no errors
      if (experiment_type === 'forever') {
        for (let j = 0; j < this.targetSystem.defaultVariables.length; j++) {
          let default_knob  = this.targetSystem.defaultVariables[j];
          let knob = [];
          knob.push(default_knob["name"]);
          knob.push(default_knob["default"]);
          all_knobs.push(knob);
        }
      } else {
        // regular knob creation (name, min, max, step -if applicable-)
        for (let j = 0; j < this.experiment.changeableVariables.length; j++) {
          let changeable_variable = this.experiment.changeableVariables[j];
          const knob = [];
          knob.push(changeable_variable.name);
          knob.push(Number(changeable_variable.min));
          knob.push(Number(changeable_variable.max));
          if (this.experiment.executionStrategy.type === "step_explorer") {
            knob.push(Number(changeable_variable.step));
          }
          all_knobs.push(knob);
        }
        // prepare other attributes
        if (experiment_type === "random" || experiment_type === "mlr_mbo" || experiment_type === "self_optimizer" || experiment_type === "uncorrelated_self_optimizer") {
          this.experiment.executionStrategy.optimizer_iterations = Number(this.experiment.executionStrategy.optimizer_iterations);
          this.experiment.executionStrategy.optimizer_iterations_in_design = Number(this.experiment.executionStrategy.optimizer_iterations_in_design);
        }
        this.experiment.executionStrategy.sample_size = Number(this.experiment.executionStrategy.sample_size);
        this.calculateTotalNrOfStages();
        this.experiment.executionStrategy.stages_count = Number(this.stages_count);
      }
      this.experiment.executionStrategy.knobs = all_knobs;
      // now take the incoming data type labeled as "optimize"
      for (let item of this.targetSystem.incomingDataTypes) {
        if (item.is_considered === true) {
          this.experiment.considered_data_types.push(item);
        }
      }
      this.api.saveExperiment(this.experiment).subscribe(
        (success) => {
          this.notify.success("Success", "Experiment saved");
          this.temp_storage.setNewValue(this.experiment);
          this.router.navigate(["control/experiments"]);
        }, (error) => {
          this.notify.error("Error", error.toString());
        }
      )
    }
  }

  // called for every div that's bounded to *ngIf=!hasErrors() expression.
  hasErrors(): boolean {
    const cond1 = this.targetSystem.status === "WORKING";
    const cond2 = this.targetSystem.status === "ERROR";
    if (cond1 || cond2) {
      this.errorButtonLabel = "Target system is not available";
      return true;
    }

    const cond3 = this.experiment.name === null;
    const cond4 = this.experiment.name.length === 0;
    if (cond3 || cond4) {
      this.errorButtonLabel = "Provide experiment name";
      return true;
    }

    // check data types to be considered
    let weight_sum = 0;
    for (let item of this.targetSystem.incomingDataTypes) {
      if (item.is_considered) {
        // check aggregate functions
        if (isNullOrUndefined(item["aggregateFunction"])) {
          this.errorButtonLabel = "Provide valid aggregate function(s)";
          return true;
        }

        // check weights
        if (isNullOrUndefined(item["weight"])) {
          this.errorButtonLabel = "Provide valid weight(s)";
          return true;
        } else {
          if (item["weight"] <= 0 || item["weight"] > 100) {
            this.errorButtonLabel = "Provide valid weight(s)";
            return true;
          }
          else {
            weight_sum += item["weight"];
          }
        }
      }
    }
    if (this.entityService.get_number_of_considered_data_types(this.targetSystem) == 0) {
      this.errorButtonLabel = "Provide at least one incoming type to be optimized";
      return true;
    }

    // check weights' sum with 3-decimal precision
    if (weight_sum < 99.999 || weight_sum > 100) {
      this.errorButtonLabel = "Weights should sum up to 100";
      return true;
    }

    if (this.experiment.executionStrategy.type.length === 0) {
      this.errorButtonLabel = "Provide execution strategy";
      return true;
    } else {
      let execution_strategy_type = this.experiment.executionStrategy.type;
      if (execution_strategy_type === "step_explorer") {
        // check inputs for step strategy changeable variables
        for (let j = 0; j < this.experiment.changeableVariables.length; j++) {
          let variable = this.experiment.changeableVariables[j];
          if (variable["step"] <= 0 || variable["min"] >= variable["max"] || variable["step"] > variable["max"] - variable["min"]) {
            this.errorButtonLabel = "Provide valid inputs for step strategy variable(s)";
            return true;
          }
        }
      }
      // for this phase, changeable variables are still accessible at targetSystem.defaultVariables
      // if everything is ok, it skips this step and we match targetSystem.defaultVariables with experiment.executionStrategy.knobs before saving experiment
      else if (execution_strategy_type === "forever") {
        for (let j = 0; j < this.targetSystem.defaultVariables.length; j++) {
          let variable = this.targetSystem.defaultVariables[j];
          // TODO: can we have variables less than 0 ? is this correct?
          if (variable["default"] < 0 || variable["default"] > variable["max"] || variable["default"] < variable["min"]) {
            this.errorButtonLabel = "Provide valid inputs for forever strategy variable(s)";
            return true;
          }
        }
      }
      // TODO: check inputs of sequential strategy after UI updates
      else if(execution_strategy_type === "sequential") {

      }
      // now check iteration inputs for respective strategies
      else if (execution_strategy_type === "random" || execution_strategy_type === "mlr_mbo" || execution_strategy_type === "self_optimizer" || execution_strategy_type === "uncorrelated_self_optimizer") {
        if (this.experiment.executionStrategy.optimizer_iterations === null || this.experiment.executionStrategy.optimizer_iterations_in_design === null
          || this.experiment.executionStrategy.optimizer_iterations <= 0 || this.experiment.executionStrategy.optimizer_iterations_in_design < 0) {
          this.errorButtonLabel = "Provide valid inputs for execution strategy";
          return true;
        }
      }

      // check if initial design of mlr mbo is large enough
      if (execution_strategy_type === "mlr_mbo") {
        let minimum_number_of_iterations = this.experiment.changeableVariables.length * 4;
        if (this.experiment.executionStrategy.optimizer_iterations_in_design < minimum_number_of_iterations) {
          this.errorButtonLabel = "Number of optimizer iterations in design should be greater than " + minimum_number_of_iterations.toString() + " for " + execution_strategy_type;
          return true;
        }
      } else if (execution_strategy_type === "uncorrelated_self_optimizer" || execution_strategy_type === "self_optimizer") {
        // check if number of iterations for skopt are enough
        let minimum_number_of_iterations = 5;
        if (this.experiment.executionStrategy.optimizer_iterations < minimum_number_of_iterations) {
          this.errorButtonLabel = "Number of optimizer iterations should be greater than " + minimum_number_of_iterations.toString() + " for " + execution_strategy_type;
          return true;
        }
      }
      if (execution_strategy_type === "self_optimizer" || execution_strategy_type === "uncorrelated_self_optimizer" || execution_strategy_type === "mlr_mbo") {
        if (this.experiment.executionStrategy.acquisition_method === null) {
          this.errorButtonLabel = "Provide valid input for the acquisition method of the selected strategy";
          return true;
        }
      }
    }

    const cond5 = this.experiment.changeableVariables == null;
    const cond6 = this.experiment.changeableVariables.length === 0;
    const cond7 = this.experiment.executionStrategy.type !== 'forever';
    if ( (cond5 || cond6) && cond7) {
      this.errorButtonLabel = "Provide at least one changeable variable";
      return true;
    }

    if (this.experiment.executionStrategy.sample_size <= 0) {
      this.errorButtonLabel = "Provide a valid sample size";
      return true;
    }
    return false;
  }

  navigateToTargetSystemPage() {
    this.router.navigate(["control/targets/create"]).then(() => {
      console.log("navigated to target system creation page");
    });
  }

  targetSystemChanged(targetSystemName: any) {
    this.selectedTargetSystem = this.availableTargetSystems.find(item => item.name === targetSystemName);
    if (this.selectedTargetSystem !== undefined) {
      if (this.selectedTargetSystem.changeableVariables.length === 0) {
        this.notify.error("Error", "Target does not contain a changeable variable.");
        return;
      }

      // remove previously added variables if they exist
      if (this.experiment.changeableVariables.length > 0) {
        this.experiment.changeableVariables = this.experiment.changeableVariables.splice();
      }

      if (this.experiment.name != null) {
        this.experiment.name = "";
      }

      // also refresh variable model if anything is left from previous state
      if (this.variable != null) {
        this.variable = null;
      }

      // now copy all changeable variables to initialVariables array
      this.initialVariables = this.selectedTargetSystem.changeableVariables.slice(0);

      this.targetSystem = this.selectedTargetSystem;
      // relate target system with experiment now
      this.experiment.targetSystemId = this.selectedTargetSystem.id;

    } else {
      this.notify.error("Error", "Cannot fetch selected target system, please try again");
      return;
    }
  }

  addChangeableVariable(variable) {
    const ctrl = this;
    if (!isNullOrUndefined(variable)) {
      if (ctrl.experiment.changeableVariables.some(item => item.name === variable.name) ) {
        ctrl.notify.error("Error", "This variable is already added");
      } else {
        ctrl.experiment.changeableVariables.push(_(variable));
        this.preCalculateStepSize();
        this.calculateTotalNrOfStages();
      }
    }
  }

  addAllChangeableVariables() {
    const ctrl = this;
    for (var i = 0; i < ctrl.targetSystem.changeableVariables.length; i++) {
      if (ctrl.experiment.changeableVariables.filter(item => item.name === ctrl.targetSystem.changeableVariables[i].name).length === 0) {
        /* vendor does not contain the element we're looking for */
        ctrl.experiment.changeableVariables.push(_(ctrl.targetSystem.changeableVariables[i]));
      }
    }
    this.preCalculateStepSize();
    this.calculateTotalNrOfStages();
  }

  // re-calculates number of stages after each change to step size
  stepSizeChanged(stepSize) {
    if (!isNullOrUndefined(stepSize)) {
      this.calculateTotalNrOfStages();
    }
  }

  // if one of min and max is not valid, sets stages_count to null, so that it will get hidden
  minMaxModelsChanged(value) {
    if (isNullOrUndefined(value)) {
      this.stages_count = null;
    } else {
      this.calculateTotalNrOfStages();
    }
  }

  // User can select execution strategy while creating an experiment
  executionStrategyModelChanged(execution_strategy_key) {
    this.experiment.executionStrategy.type = execution_strategy_key;
    if (execution_strategy_key === 'step_explorer') {
      this.preCalculateStepSize();
      this.calculateTotalNrOfStages();
    } else if (execution_strategy_key === 'mlr_mbo') {
      this.acquisitionMethodChanged("ei");
    } else if (execution_strategy_key === 'self_optimizer' || execution_strategy_key === 'uncorrelated_self_optimizer') {
      this.acquisitionMethodChanged("gp_hedge");
    }
  }

  // User can select acquisition function for respective strategies
  acquisitionMethodChanged(acquisition_method_key) {
    this.experiment.executionStrategy.acquisition_method = acquisition_method_key;
  }

  // pre-determines step size of all added variables if selected execution strategy is step_explorer
  preCalculateStepSize() {
    if (this.experiment.executionStrategy.type === 'step_explorer') {
      for (var j = 0; j < this.experiment["changeableVariables"].length; j++) {
        if (!this.experiment["changeableVariables"][j]["step"]) {
          this.experiment["changeableVariables"][j]["step"] =
            (this.experiment["changeableVariables"][j]["max"] - this.experiment["changeableVariables"][j]["min"]) / 10;
        }
      }
    }
  }

  // returns number of stages using min, max, step size if the selected strategy is step_explorer
  // or sets stage_counts to sum of optimizer_iterations and optimizer_iterations in design for bayesian opt. methods & random method
  calculateTotalNrOfStages() {
    this.stages_count = null;
    if (this.experiment.executionStrategy.type === 'step_explorer') {
      const stage_counts = [];
      for (var j = 0; j < this.experiment.changeableVariables.length; j++) {
        if (this.experiment.changeableVariables[j]["step"] <= 0) {
          this.stages_count = null;
          break;
        } else {
          if (this.experiment.changeableVariables[j]["step"] > this.experiment.changeableVariables[j]["max"] - this.experiment.changeableVariables[j]["min"]) {
            stage_counts.push(1);
          } else {
            const stage_count = Math.floor((this.experiment.changeableVariables[j]["max"]
              - this.experiment.changeableVariables[j]["min"]) /
              this.experiment.changeableVariables[j]["step"]) + 1;
            stage_counts.push(stage_count);
          }

        }
      }
      if (stage_counts.length !== 0) {
        const sum = stage_counts.reduce(function(a, b) {return a * b; } );
        this.stages_count = sum;
      }
    } else if (this.experiment.executionStrategy.type === 'mlr_mbo'
      || this.experiment.executionStrategy.type === 'self_optimizer'
      || this.experiment.executionStrategy.type === 'uncorrelated_self_optimizer'
      || this.experiment.executionStrategy.type === 'random') {
      this.stages_count = this.experiment.executionStrategy.optimizer_iterations + this.experiment.executionStrategy.optimizer_iterations_in_design;
    }
  }

  removeChangeableVariable(index) {
    this.experiment.changeableVariables.splice(index, 1);
    this.calculateTotalNrOfStages();
  }

  removeAllVariables() {
    this.experiment.changeableVariables.splice(0);
    this.calculateTotalNrOfStages();
  }

  hasChanges(): boolean {
    return JSON.stringify(this.experiment) !== JSON.stringify(this.originalExperiment);
  }

  public is_data_type_selected(): boolean {
    for (let dataType of this.targetSystem.incomingDataTypes) {
      if (dataType["is_considered"] == true) {
        return true;
      }
    }
    return false;
  }

  /**
   * sets respective weights of data types when user clicks
   */
  public data_type_checkbox_clicked(data_type_index): void {
    let data_type = this.targetSystem.incomingDataTypes[data_type_index];
    // first click
    if (isNullOrUndefined(data_type["is_considered"])) {
      data_type["is_considered"] = true;
      data_type["weight"] = 100 / this.entityService.get_number_of_considered_data_types(this.targetSystem);
    }
    // subsequent clicks
    else {
      data_type["is_considered"] = !data_type["is_considered"];
    }

    // adjust weights of all data types
    for (let i = 0; i < this.targetSystem.incomingDataTypes.length; i++) {
      let data_type = this.targetSystem.incomingDataTypes[i];
      if(data_type["is_considered"] == true) {
        data_type["weight"] = 100 / this.entityService.get_number_of_considered_data_types(this.targetSystem);
      } else {
        data_type["weight"] = undefined;
      }
    }
  }

  /**
   * checks whether given data type is coming from primaryDataProvider of targetSystem
   */
  public is_data_type_coming_from_primary(data_type_index): boolean {
    let data_type_name = this.targetSystem.incomingDataTypes[data_type_index]["name"];
    for (let data_type of this.targetSystem.primaryDataProvider.incomingDataTypes) {
      if (data_type["name"] == data_type_name) {
        return true;
      }
    }
    return false;
  }

}
