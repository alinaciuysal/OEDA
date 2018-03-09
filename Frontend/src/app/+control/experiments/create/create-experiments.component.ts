import {OnInit, Component} from "@angular/core";
import {NotificationsService} from "angular2-notifications";
import {Router} from "@angular/router";
import {LayoutService} from "../../../shared/modules/helper/layout.service";
import {OEDAApiService, Experiment, Target, ExecutionStrategy} from "../../../shared/modules/api/oeda-api.service";
import * as _ from "lodash.clonedeep";
import {UUID} from "angular2-uuid";
import {isNullOrUndefined} from "util";
import {TempStorageService} from "../../../shared/modules/helper/temp-storage-service";


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

  constructor(private layout: LayoutService, private api: OEDAApiService,
              private router: Router, private notify: NotificationsService,
              private temp_storage: TempStorageService) {
    this.availableTargetSystems = [];
    this.initialVariables = [];

    this.targetSystem = this.createTargetSystem();
    // create an empty experiment and execution strategy
    this.executionStrategy = this.createExecutionStrategy();
    this.experiment = this.createExperiment();
    this.originalExperiment = _(this.experiment);
    this.stages_count = null;
    this.is_collapsed = true;
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

  navigateToTargetSystemPage() {
    this.router.navigate(["control/targets/create"]).then(() => {
      console.log("navigated to target system creation page");
    });
  }

  firstDropDownChanged(targetSystemName: any) {
    this.selectedTargetSystem = this.availableTargetSystems.find(item => item.name === targetSystemName);

    if (this.selectedTargetSystem !== undefined) {
      if (this.selectedTargetSystem.changeableVariable.length === 0) {
        this.notify.error("Error", "Target does not contain a changeable variable.");
        return;
      }

      // remove previously added variables if they exist
      if (this.experiment.changeableVariable.length > 0) {
        this.experiment.changeableVariable = this.experiment.changeableVariable.splice();
      }

      if (this.experiment.name != null) {
        this.experiment.name = "";
      }

      // also refresh variable model if anything is left from previous state
      if (this.variable != null) {
        this.variable = null;
      }

      // now copy all changeable variables to initialVariables array
      this.initialVariables = this.selectedTargetSystem.changeableVariable.slice(0);

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
      if (ctrl.experiment.changeableVariable.some(item => item.name === variable.name) ) {
        ctrl.notify.error("Error", "This variable is already added");
      } else {
        ctrl.experiment.changeableVariable.push(_(variable));
        this.preCalculateStepSize();
        this.calculateTotalNrOfStages();
      }
    }
  }

  addAllChangeableVariables() {
    const ctrl = this;
    for (var i = 0; i < ctrl.targetSystem.changeableVariable.length; i++) {
      if (ctrl.experiment.changeableVariable.filter(item => item.name === ctrl.targetSystem.changeableVariable[i].name).length === 0) {
        /* vendor does not contain the element we're looking for */
        ctrl.experiment.changeableVariable.push(_(ctrl.targetSystem.changeableVariable[i]));
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

  // if user selects step strategy at any moment of experiment creation, it
  executionStrategyModelChanged(execution_strategy_key) {
    this.experiment.executionStrategy.type = execution_strategy_key;
    if (execution_strategy_key === 'step_explorer') {
      this.preCalculateStepSize();
      this.calculateTotalNrOfStages();
    }
  }

  // pre-determines step size of all added variables if selected execution strategy is step_explorer
  preCalculateStepSize() {
    if (this.experiment.executionStrategy.type === 'step_explorer') {
      for (var j = 0; j < this.experiment["changeableVariable"].length; j++) {
        if (!this.experiment["changeableVariable"][j]["step"]) {
          this.experiment["changeableVariable"][j]["step"] =
            (this.experiment["changeableVariable"][j]["max"] - this.experiment["changeableVariable"][j]["min"]) / 10;
        }
      }
    }
  }

  // returns number of stages using min, max, step size if the selected strategy is step_explorer
  calculateTotalNrOfStages() {
    this.stages_count = null;
    if (this.experiment.executionStrategy.type === 'step_explorer') {
      const stage_counts = [];
      for (var j = 0; j < this.experiment.changeableVariable.length; j++) {
        if (this.experiment.changeableVariable[j]["step"] <= 0) {
          this.stages_count = null;
          break;
        } else {
          if (this.experiment.changeableVariable[j]["step"] > this.experiment.changeableVariable[j]["max"] - this.experiment.changeableVariable[j]["min"]) {
            stage_counts.push(1);
          } else {
            const stage_count = Math.floor((this.experiment.changeableVariable[j]["max"]
              - this.experiment.changeableVariable[j]["min"]) /
              this.experiment.changeableVariable[j]["step"]) + 1;
            stage_counts.push(stage_count);
          }

        }
      }
      if (stage_counts.length !== 0) {
        const sum = stage_counts.reduce(function(a, b) {return a * b; } );
        this.stages_count = sum;
      }
    }

  }

  removeChangeableVariable(index) {
    this.experiment.changeableVariable.splice(index, 1);
    this.calculateTotalNrOfStages();
  }

  removeAllVariables() {
    this.experiment.changeableVariable.splice(0);
    this.calculateTotalNrOfStages();
  }

  hasChanges(): boolean {
    return JSON.stringify(this.experiment) !== JSON.stringify(this.originalExperiment);
  }

  saveExperiment() {
    if (!this.hasErrors()) {
      const all_knobs = [];
      for (var j = 0; j < this.experiment.changeableVariable.length; j++) {
        const knob = [];
        knob.push(this.experiment.changeableVariable[j].name);
        knob.push(Number(this.experiment.changeableVariable[j].min));
        knob.push(Number(this.experiment.changeableVariable[j].max));
        if (this.experiment.executionStrategy.type === "step_explorer") {
          knob.push(Number(this.experiment.changeableVariable[j].step));
        }
        all_knobs.push(knob);
      }
      this.experiment.executionStrategy.knobs = all_knobs;

      this.experiment.executionStrategy.sample_size = Number(this.experiment.executionStrategy.sample_size);
      // save experiment stage to executionStrategy, so that it can be used in determining nr of remaining stages and estimated time
      this.experiment.executionStrategy.stages_count = Number(this.stages_count);

      let experiment_type = this.experiment.executionStrategy.type;
      if (experiment_type === "random" || experiment_type === "mlr_mbo" || experiment_type === "self_optimizer" || experiment_type === "uncorrelated_self_optimizer") {
        this.experiment.executionStrategy.optimizer_iterations = Number(this.experiment.executionStrategy.optimizer_iterations);
        this.experiment.executionStrategy.optimizer_iterations_in_design = Number(this.experiment.executionStrategy.optimizer_iterations_in_design);
      }

      // now take the incoming data type labeled as "optimize"
      for (var item of this.targetSystem.incomingDataTypes) {
        if (item.is_optimized === true) {
          this.experiment.optimized_data_types.push(item);
        }
      }
      console.log(this.experiment);
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

    // check data types to be optimized (minimize or maximize)
    let nr_of_incoming_data_types_to_be_optimized = 0;
    for (let item of this.targetSystem.incomingDataTypes) {
      if (item.is_optimized) {
        nr_of_incoming_data_types_to_be_optimized += 1;
      }
    }
    if (nr_of_incoming_data_types_to_be_optimized != 1) {
      this.errorButtonLabel = "Provide one incoming type to be optimized";
      return true;
    }

    const cond5 = this.experiment.changeableVariable == null;
    const cond6 = this.experiment.changeableVariable.length === 0;
    if (cond5 || cond6) {
      this.errorButtonLabel = "Provide at least one changeable variable";
      return true;
    }

    if (this.experiment.executionStrategy.type.length === 0) {
      this.errorButtonLabel = "Provide execution strategy";
      return true;
    } else {
      if (this.experiment.executionStrategy.type === "step_explorer") {
        for (var j = 0; j < this.experiment.changeableVariable.length; j++) {
          if (this.experiment.changeableVariable[j]["step"] <= 0
            || this.experiment.changeableVariable[j]["min"] >= this.experiment.changeableVariable[j]["max"]
            || this.experiment.changeableVariable[j]["step"] > this.experiment.changeableVariable[j]["max"] - this.experiment.changeableVariable[j]["min"]) {
            this.errorButtonLabel = "Provide valid inputs for changeable variable(s)";
            return true;
          }
        }
      }
      let execution_strategy_type = this.experiment.executionStrategy.type;
      if (execution_strategy_type === "random" || execution_strategy_type === "mlr_mbo" || execution_strategy_type === "self_optimizer" || execution_strategy_type === "uncorrelated_self_optimizer") {
        if (this.experiment.executionStrategy.optimizer_iterations === null || this.experiment.executionStrategy.optimizer_iterations_in_design === null
            || this.experiment.executionStrategy.optimizer_iterations <= 0 || this.experiment.executionStrategy.optimizer_iterations_in_design < 0) {
          this.errorButtonLabel = "Provide valid inputs for execution strategy";
          return true;
        }
      }
      // check if initial design is large enough
      if (execution_strategy_type === "mlr_mbo") {
        let minimum_number_of_iterations = this.experiment.changeableVariable.length * 4
        if (this.experiment.executionStrategy.optimizer_iterations_in_design < minimum_number_of_iterations) {
          this.errorButtonLabel = "Number of optimizer iterations should be greater than " + minimum_number_of_iterations.toString();
          return true;
        }
      }
      // we're not using self_optimizer method name for now
      if (execution_strategy_type === "self_optimizer") {
        if (this.experiment.executionStrategy.optimizer_method === null || this.experiment.executionStrategy.optimizer_method.length === 0) {
          this.errorButtonLabel = "Provide valid inputs for self-optimizer strategy";
          return true;
        }
      }
    }

    if (this.experiment.executionStrategy.sample_size <= 0) {
      this.errorButtonLabel = "Provide a valid sample size";
      return true;
    }
    return false;
  }

  createExperiment(): Experiment {
    return {
      "id": UUID.UUID(),
      "name": "",
      "description": "",
      "status": "",
      "targetSystemId": "",
      "executionStrategy": this.executionStrategy,
      "changeableVariable": [],
      "optimized_data_types": []
    }
  }

  createTargetSystem(): Target {
    return {
      "id": "",
      "dataProviders": [],
      "primaryDataProvider": {
        "type": "",
        "ignore_first_n_samples": null
      },
      "secondaryDataProviders": [],
      "changeProvider": {
        "type": "",
      },
      "name": "",
      "status": "",
      "description": "",
      "incomingDataTypes": [],
      "changeableVariable": []
    }
  }

  createExecutionStrategy(): ExecutionStrategy {
    return {
      type: "",
      sample_size: 40,
      knobs: [],
      stages_count: 0,
      optimizer_method: "",
      optimizer_iterations: 10,
      optimizer_iterations_in_design: 0
    }
  }

}
