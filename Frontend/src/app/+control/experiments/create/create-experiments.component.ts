import {OnInit, Component} from "@angular/core";
import {NotificationsService} from "angular2-notifications";
import {Router} from "@angular/router";
import {LayoutService} from "../../../shared/modules/helper/layout.service";
import {OEDAApiService, Experiment, Target} from "../../../shared/modules/api/oeda-api.service";
import * as _ from "lodash.clonedeep";
import {isNullOrUndefined} from "util";
import {TempStorageService} from "../../../shared/modules/helper/temp-storage-service";
import {EntityService} from "../../../shared/util/entity-service";
import {UtilService} from "../../../shared/modules/util/util.service";

@Component({
  selector: 'control-experiments',
  templateUrl: './create-experiments.component.html',
})
export class CreateExperimentsComponent implements OnInit {
  experiment: Experiment;
  originalExperiment: Experiment;
  targetSystem: Target;
  originalTargetSystem: Target;
  availableTargetSystems: any;
  executionStrategy: any;
  variable: any;
  data_types_for_analysis: any;
  selectedTargetSystem: any;
  stages_count: any;
  is_collapsed: boolean;
  errorButtonLabel: string;
  errorButtonLabelChangeableVariables: string;
  defaultAlpha: number;

  constructor(private layout: LayoutService, private api: OEDAApiService,
              private router: Router, private notify: NotificationsService,
              private temp_storage: TempStorageService, private entityService: EntityService, private utilService: UtilService) {
    this.availableTargetSystems = [];
    this.data_types_for_analysis = [];

    // create experiment, target system, and execution strategy
    this.executionStrategy = this.entityService.create_execution_strategy();
    this.targetSystem = this.entityService.create_target_system();
    this.experiment = this.entityService.create_experiment(this.executionStrategy);
    this.originalExperiment = _(this.experiment);
    this.defaultAlpha = 0.05; // default value to be added when an analysis is selected
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

  saveExperiment() {
    if (!this.hasErrors()) {
      let experiment_type = this.experiment.executionStrategy.type;
      // push names & default values of target system to executionStrategy for forever strategy if there are no errors
      if (experiment_type === 'forever') {
        let all_knobs: any = {};
        for (let j = 0; j < this.targetSystem.defaultVariables.length; j++) {
          let default_knob  = this.targetSystem.defaultVariables[j];
          all_knobs[default_knob["name"]] = default_knob["default"];
        }
        this.experiment.executionStrategy.knobs = all_knobs;
      } else {
        this.experiment.executionStrategy.knobs = this.experiment.changeableVariables;
        // prepare other attributes
        if (experiment_type === "mlr_mbo" || experiment_type === "self_optimizer" || experiment_type === "uncorrelated_self_optimizer") {
          this.experiment.executionStrategy.optimizer_iterations = Number(this.experiment.executionStrategy.optimizer_iterations);
          this.experiment.executionStrategy.optimizer_iterations_in_design = Number(this.experiment.executionStrategy.optimizer_iterations_in_design);
        }
        this.experiment.executionStrategy.sample_size = Number(this.experiment.executionStrategy.sample_size);
        // this.calculateTotalNrOfStages();
        this.experiment.executionStrategy.stages_count = Number(this.stages_count);
      }
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

    // check data types to be considered for optimization
    if (this.experiment.analysis.type == 'no_analysis' || this.experiment.analysis.type == 'bayesian_opt') {
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
      // NEW: iterates min, max provided by the user and checks if they are within the range of default ones
      for (let i = 0; i < this.experiment.changeableVariables.length; i++) {
        let knobArr = this.experiment.changeableVariables[i];
        for (let idx = 0; idx < knobArr.length; idx++) {
          let knob = knobArr[idx];
          let originalKnob = this.targetSystem.defaultVariables.find(x => x.name == knob.name);
          if (knob.min < originalKnob.min || knob.max > originalKnob.max || knob.max <= knob.min || knob.min >= knob.max) {
            this.errorButtonLabel = "Value(s) of changeable variables should be within the range of original ones";
            return true;
          }

        }
      }
    }

    if (this.experiment.executionStrategy.type.length === 0) {
      this.errorButtonLabel = "Provide analysis type";
      return true;
    }
    else {
      let execution_strategy_type = this.experiment.executionStrategy.type;
      let analysis_type = this.experiment.analysis.type;

      if (execution_strategy_type === "step_explorer" || analysis_type === 'factorial_tests') {
        // check inputs for step strategy changeable variables
        for (let j = 0; j < this.experiment.changeableVariables.length; j++) {
          let knobArr = this.experiment.changeableVariables[j];
          for (let key in this.get_keys(knobArr)) {
            if (knobArr[key]["step"] <= 0 || knobArr[key]["min"] >= knobArr[key]["max"] || knobArr[key]["step"] > knobArr[key]["max"] - knobArr[key]["min"]) {
              this.errorButtonLabel = "Provide valid inputs for variable(s)";
              return true;
            }
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
      else if(execution_strategy_type === "sequential") {
        // check inputs for step strategy changeable variables
        for (let j = 0; j < this.experiment.changeableVariables.length; j++) {
          let knobArr = this.experiment.changeableVariables[j];
          for (let key in this.get_keys(knobArr)) {
            if (knobArr[key]["target"] < knobArr[key]["min"] || knobArr[key]["target"] > knobArr[key]["max"] || knobArr[key]["min"] > knobArr[key]["max"]) {
              this.errorButtonLabel = "Provide valid inputs for variable(s)";
              return true;
            }
          }
        }
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

    // if there's an error in analysis stage, propogate it to upper part of UI
    if (this.hasErrorsAnalysis()) {
      this.errorButtonLabel = this.errorButtonLabelChangeableVariables;
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

      this.targetSystem = this.selectedTargetSystem;
      // also make a copy of original ts for changes in analysis
      this.originalTargetSystem = _(this.targetSystem);

      // relate target system with experiment now
      this.experiment.targetSystemId = this.selectedTargetSystem.id;

      // prepare Data Types for Analysis TODO: this might be filtered/changed whether data is coming from primary or secondary
      for (let i = 0; i < this.originalTargetSystem.incomingDataTypes.length; i++) {
        let data_type = {};
        data_type["key"] = this.originalTargetSystem.incomingDataTypes[i]["name"];
        data_type["label"] = this.originalTargetSystem.incomingDataTypes[i]["name"];
        this.data_types_for_analysis.push(data_type);
      }
      console.log(this.originalTargetSystem.incomingDataTypes);

    } else {
      this.notify.error("Error", "Cannot fetch selected target system, please try again");
      return;
    }
  }

  addChangeableVariable(variable) {
    const ctrl = this;
    let knobArr = [];
    if (ctrl.experiment.analysis.type === 'two_sample_tests') {
      if (isNullOrUndefined(variable.target)) {
        ctrl.notify.error("Error", "Provide target value for changeable variable(s)");
      } else {
        // check number of already-added variables for different analysis options
        if (ctrl.experiment.analysis.method === 'one_factor_two_values') {
          if (ctrl.experiment.changeableVariables.length == 2) {
            ctrl.notify.error("Error", "2 factors have already been specified for T-test (One Variable Two Factors)");
            return;
          } else if (ctrl.experiment.changeableVariables.length == 1) {
            let existingKnob = ctrl.experiment.changeableVariables[0][0];
            if (existingKnob.name != variable.name) {
              ctrl.notify.error("Error", "You can't add two different variables for T-test (One Variable Two Factors)");
              return;
            }
          }
          // ch. var is empty or there's one variable. check boundaries
          if (!isNullOrUndefined(variable.target) && variable.target <= variable.max && variable.target >= variable.min) {
            // ch. var is empty, just push
            knobArr.push(_(variable));
            ctrl.experiment.changeableVariables.push(knobArr);
            return;
          } else {
            ctrl.notify.error("Error", "Provide valid value(s) for variable");
            return;
          }
        }
        // two_factors_one_value option & adding two or more variables for sequential str. are handled via addVariablesFor2FactorAndSeqTest() fcn
      }
    } else {
      // because factorial_tests (anova) is similar to step str., we handle it here
      // check N
      if (this.experiment.analysis.type == 'factorial_tests') {
        if (this.experiment.analysis.n > this.targetSystem.changeableVariables.length) {
          this.notify.error("Error", "Number of factors for factorial tests should be less than or equal to " + this.targetSystem.changeableVariables.length);
          return;
        }
        // also check previously-added variables if they match with N
        let number_of_desired_variables = this.experiment.analysis.n;
        if (this.experiment.changeableVariables.length >= number_of_desired_variables) {
          this.notify.error("Error", "You can't exceed " + number_of_desired_variables + " variable(s) for this test");
          return;
        }
        // check if provided step value(s) are valid or not
        for (let i = 0; i < this.targetSystem.changeableVariables.length; i++) {
          let variable = this.targetSystem.changeableVariables[i];
          if (variable.is_selected && (isNullOrUndefined(variable.step) || !variable.hasOwnProperty("step") || variable.step <= 0 )) {
            this.notify.error("Error", "Provide valid values for variable(s)");
            return;
          }
        }
        // everything is ok, push to experiment.changeableVariables array in next statements
      }
      // legacy part
      // first check single variables (they should not occur twice)
      // TODO: might be changed depending on the strategy & if we allow A/A testing
      for (let j = 0; j < ctrl.experiment.changeableVariables.length; j++) {
        let knobArr = ctrl.experiment.changeableVariables[j];
        if (knobArr.length == 1) {
          if (knobArr[0].name == variable.name) {
            ctrl.notify.error("Error", "This variable is already added");
            return;
          }
        }
      }

      let newKnobArr = [];
      // if user wants to add one variable & its target for seq. str. we handle it here
      if (this.experiment.executionStrategy.type == 'sequential') {
        if (isNullOrUndefined(variable.is_selected) ) {
          this.notify.error("Error", "Please select variable(s) first");
          return;
        } else {
          // check boundaries
          if ( (variable["step"] <= 0 || variable["min"] >= variable["max"] || variable["step"] > variable["max"] - variable["min"])
                || isNullOrUndefined(variable.target) || !variable.hasOwnProperty("target") ) {
            this.notify.error("Error", "Provide valid values for variable(s)");
            return;
          }
        }
      }

      newKnobArr.push(_(variable));
      ctrl.experiment.changeableVariables.push(newKnobArr);
      ctrl.preCalculateStepSize();
      ctrl.calculateTotalNrOfStages();
    }
  }

  // assuming that user has provided different configurations for variables and wants them to use for the selected analysis test
  addVariablesFor2FactorAndSeqTest() {
    let number_of_desired_variables: number;
    if (this.experiment.analysis.method === 'two_factors_one_value' || this.experiment.analysis.type == 'one_sample_tests') {

      if (this.experiment.analysis.method === 'two_factors_one_value')
        number_of_desired_variables = 2;
      else if (this.experiment.analysis.type === 'one_sample_tests')
        number_of_desired_variables = 1;

      if (this.experiment.changeableVariables.length >= number_of_desired_variables) {
        this.notify.error("Error", "You can't exceed " + number_of_desired_variables + " variable(s) for this test");
        return;
      }
    }

    // check boundaries of selected variables
    for (let j = 0; j < this.targetSystem.changeableVariables.length; j++) {
      let variable = this.targetSystem.changeableVariables[j];
      if (variable.is_selected) {
        if (isNullOrUndefined(variable.target)) {
          this.notify.error("Error", "Provide valid values for variable(s)");
          return;
        } else {
          if (variable.target < variable.min || variable.target > variable.max) {
            this.notify.error("Error", "Provide valid values for variable(s)");
            return;
          }
          // everything is ok for selected variables
        }
      }
    }

    // everything is ok, push to experiment.changeableVariables array
    let knobArr = [];
    for (let variable of this.targetSystem.changeableVariables) {
      if (variable["is_selected"] == true) {
        if (!isNullOrUndefined(variable.target) ) {
          // push an array of k-v pairs instead of pushing variables directly
          let knob: any = {};
          knob.name = variable.name;
          knob.min = variable.min;
          knob.max = variable.max;
          knob.default = variable.default;
          knob.target = variable.target;
          knobArr.push(knob);
        } else {
          this.notify.error("Error", "Please specify valid values for the selected changeable variables");
          return;
        }
      }
    }
    // do not push empty k-v pair
    if (knobArr.length == 0) {
      this.notify.error("Error", "Please specify valid values for the selected changeable variables");
    } else {
      this.experiment.changeableVariables.push(knobArr);
    }

  }

  // if one of the parameters in executionStrategy is not valid, sets stages_count to null, so that it will get hidden
  strategyParametesChanged(value) {
    if (isNullOrUndefined(value)) {
      this.stages_count = null;
    } else {
      this.calculateTotalNrOfStages();
    }
  }

  // User can select execution strategy while creating an experiment
  executionStrategyModelChanged(execution_strategy_key) {

    // refresh previously-selected variables of targetSystem & experiment
    this.experiment.changeableVariables = _(this.originalExperiment.changeableVariables);
    this.targetSystem.changeableVariables = _(this.originalTargetSystem.changeableVariables);

    this.experiment.executionStrategy.type = execution_strategy_key;
    if (execution_strategy_key === 'step_explorer') {
      this.preCalculateStepSize();
      this.calculateTotalNrOfStages();
    } else if (execution_strategy_key === 'mlr_mbo') {
      this.acquisitionMethodChanged("ei");
      this.calculateTotalNrOfStages();
    } else if (execution_strategy_key === 'self_optimizer' || execution_strategy_key === 'uncorrelated_self_optimizer') {
      this.acquisitionMethodChanged("gp_hedge");
      this.calculateTotalNrOfStages();
    }
  }

  // User can select analysis type while creating an experiment
  analysisTypeChanged(key) {
    this.experiment.analysis.type = key;
    // refresh previously-created tuples
    this.experiment.executionStrategy = this.entityService.create_execution_strategy();
    this.stages_count = null;
    this.experiment.changeableVariables = [];
    this.experiment.analysis.method = null;
    this.experiment.analysis.data_type = null;
    this.experiment.analysis.alpha = null;

    // also refresh targetSystem variables if user has selected some of them
    this.targetSystem.changeableVariables = _(this.originalTargetSystem.changeableVariables);
    this.targetSystem.incomingDataTypes = _(this.originalTargetSystem.incomingDataTypes);

    // set defaultAlpha for all analysis tests
    if (key !== 'no_analysis') {
      this.experiment.analysis.alpha = this.defaultAlpha;
    }

    // set executionStrategy
    if (key == 'two_sample_tests' || key == 'one_sample_tests' || key == 'n_sample_tests') {
      this.experiment.executionStrategy.type = "sequential"; // TODO: this might be removed depending on backend logic
    }
    else if (this.experiment.analysis.type == 'factorial_tests') {
      this.experiment.executionStrategy.type = "step_explorer";  // TODO: this might be removed depending on backend logic
      this.experiment.analysis.n = this.targetSystem.changeableVariables.length; // set default value of factors (n)
    }
  }

  // User can select specific method for the selected analysis type
  analysisMethodChanged(method){
    // refresh previously-added changeable variables (if there are any)
    this.experiment.changeableVariables = [];
    // also refresh original variables of target system (in case any changes have been made previously)
    this.targetSystem.changeableVariables = _(this.originalTargetSystem.changeableVariables);

    if (this.experiment.analysis.type == 'two_sample_tests') {
      // check if target system has enough factors for t-test with 2 factors
      if (this.targetSystem.changeableVariables.length < 2 && method == 'two_factors_one_value') {
        this.notify.error("Error", "This target system definition does not have two changeable variables");
        return;
      }
    } else if (this.experiment.analysis.type == 'bayesian_opt') {
      // same names are used for bayesian opt, so set executionStrategy like this
      this.executionStrategyModelChanged(method);
    }
    this.experiment.analysis.method = method;
  }

  // User can select acquisition function for respective strategies
  acquisitionMethodChanged(acquisition_method_key) {
    this.experiment.executionStrategy.acquisition_method = acquisition_method_key;
  }

  // calculates step size of all added variables if strategy is step_explorer
  preCalculateStepSize() {
    if (this.experiment.executionStrategy.type === 'step_explorer' || this.experiment.analysis.type == 'factorial_tests') {
      for (let j = 0; j < this.experiment.changeableVariables.length; j++) {
        let knobArr = this.experiment.changeableVariables[j];
        let knob = knobArr[0]; // for step str. we have only one knob in knobArr
        if (!knob["step"])
          knob[j]["step"] = (knob["max"] - knob["min"]) / 10;
      }
    }
  }

  // returns number of stages using min, max, step size if the selected strategy is step_explorer
  // or sets stage_counts to sum of optimizer_iterations and optimizer_iterations in design for bayesian opt. methods
  calculateTotalNrOfStages() {
    this.stages_count = null;
    if (this.experiment.executionStrategy.type === 'step_explorer' || this.experiment.analysis.type == 'factorial_tests') {
      const stage_counts = [];
      for (let j = 0; j < this.experiment.changeableVariables.length; j++) {
        let knob = this.experiment.changeableVariables[j][0]; // for step str. we have only one knob in knobArr
        let levels = []; // represent levels in an array-form for UI

        if (knob["step"] <= 0) {
          this.stages_count = null;
          break;
        } else {
          // first get decimals of provided step value
          let decimals = this.utilService.countDecimals(knob.step);

          if (knob.step > knob.max - knob.min) {
            stage_counts.push(1);
            let num = Number(knob.min).toFixed(decimals);
            levels.push({"key":num, "label": num}); // push an object of labeled-input-select options
          } else {
            const stage_count = Math.floor((knob["max"] - knob["min"]) / knob["step"]) + 1;
            stage_counts.push(stage_count);

            // so for each stage, push a step value to levels
            for (let lower = knob.min; lower <= knob.max;) {
              // knob.step = Number(knob.step).toFixed(decimals);
              let num = Number(lower).toFixed(decimals);
              levels.push({"key":num, "label": num}); // push an object of labeled-input-select options
              lower += knob.step;
            }
          }
        }
        console.log(levels);
        knob.levels = levels;
      }
      if (stage_counts.length !== 0) {
        this.stages_count = stage_counts.reduce(function(a, b) {return a * b; } );
      }
    }
    // prepare stages_count for other str.
    else if (this.experiment.executionStrategy.type === 'mlr_mbo'
      || this.experiment.executionStrategy.type === 'self_optimizer'
      || this.experiment.executionStrategy.type === 'uncorrelated_self_optimizer') {
      this.stages_count = this.experiment.executionStrategy.optimizer_iterations + this.experiment.executionStrategy.optimizer_iterations_in_design;
    }
  }

  removeChangeableVariable(index: number) {
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

  // i is the index of changeable variable to be added to experiment
  public is_changeable_variable_valid(i: number) {
    let variable = this.targetSystem.changeableVariables[i];
    if (this.experiment.executionStrategy.type == 'step_explorer') {
      let is_selected = variable.is_selected == true;
      let step_size_not_valid = variable["step"] <= 0 || variable["min"] >= variable["max"] || variable["step"] > variable["max"] - variable["min"];
      return (!isNullOrUndefined(variable.step) && !step_size_not_valid && is_selected);
    }
    if (this.experiment.executionStrategy.type == 'sequential') {
      return false; // we return false here by default because user should use "Add as Configuration" btn instead of "Add" btn for each variable
    }
    return true; // for other strategies returns true by default because we don't need those checks
  }

  public is_changeable_variable_selected(i): boolean {

    // checks if at least one variable is selected for proper visualization of tables
    if (isNullOrUndefined(i)) {
      for (let changeableVariable of this.targetSystem.changeableVariables) {
        if (changeableVariable["is_selected"] == true) {
          return true;
        }
      }
      return false;
    } else {
      // just checks if variable in given index is selected or not
      let variable = this.targetSystem.changeableVariables[i];
      return variable.is_selected;
    }
  }

  /**
   * sets is_selected flag of changeableVariables for analysis options
   */
  public changeable_variable_checkbox_clicked(changeableVariable_index): void {
    let changeableVariable = this.targetSystem.changeableVariables[changeableVariable_index];
    if (isNullOrUndefined(changeableVariable.is_selected)) {
      // first click
      changeableVariable.is_selected = true;
    } else {
      // subsequent clicks
      changeableVariable.is_selected = !changeableVariable.is_selected;
      changeableVariable.target = null;
    }
    // set step for factorial_tests automatically
    if (changeableVariable.is_selected && this.experiment.analysis.type == 'factorial_tests') {
      changeableVariable.step = changeableVariable.max - changeableVariable.min;
    }
  }


  // checks if user has added proper number of variables to the definition
  public hasErrorsAnalysis() {
    if (this.experiment.analysis.type !== 'bayesian_opt') {
      let chVarLen = this.experiment.changeableVariables.length;
      let analysis_method = this.experiment.analysis.method;
      let analysis_type = this.experiment.analysis.type;

      // regular check for all analysis types
      if (isNullOrUndefined(this.experiment.analysis.alpha) || this.experiment.analysis.alpha <= 0 || this.experiment.analysis.alpha >= 1) {
        this.errorButtonLabelChangeableVariables = "Provide valid alpha value for analysis";
        return true;
      }
      if (isNullOrUndefined(this.experiment.analysis.data_type)) {
        this.errorButtonLabelChangeableVariables = "Provide valid data type for analysis";
        return true;
      }

      // two_sample_tests checks
      if (chVarLen != 2) {
        if (analysis_method == 'two_factors_one_value') {
          this.errorButtonLabelChangeableVariables = "Select and provide 1 value for each of 2 factors";
          return true;
        } else if (analysis_method == 'one_factor_two_values') {
          this.errorButtonLabelChangeableVariables = "Select and provide 2 different values for a single variable";
          return true;
        }
      }

      // so n is used for both number of factors in factorial anova & sample size for n_sample_test
      if (analysis_type == 'factorial_tests') {
        let n = this.experiment.analysis.n;
        if (!isNullOrUndefined(n)) {
          if (n > this.targetSystem.changeableVariables.length) {
            this.errorButtonLabelChangeableVariables = "Number of factors can be maximum " + this.targetSystem.changeableVariables.length;
            return true;
          }
          if (n < 2) {
            this.errorButtonLabelChangeableVariables = "Factorial tests cannot be used with less than 2 factors";
            return true;
          }
          if (chVarLen != n) {
            // n is valid but not enough variables have been added to experiment yet
            this.errorButtonLabelChangeableVariables = "Select and provide values for " + n + " different variables of factorial test";
            return true;
          }
        } else {
          this.errorButtonLabelChangeableVariables = "Provide Number of factors for the factorial test";
          return true;
        }
      }
      else if (analysis_type == 'n_sample_tests') {
        let n = this.experiment.analysis.n;

        if (!isNullOrUndefined(n)) {
          if (chVarLen != n) {
            // n is valid but not enough variables have been added to experiment yet
            this.errorButtonLabelChangeableVariables = "Select and provide values for " + n + " different variables for N-Samples Tests";
            return true;
          }
        } else {
          this.errorButtonLabelChangeableVariables = "Provide Number of samples for N-Samples Tests";
          return true;
        }
      }
      return false;
    }
    return false;
  }

  // checks if user has selected proper number of variables for analysis tests
  // and checks if user selected at least one variable to be added to experiment.changeableVariables
  public hasErrors2FactorAndSequential() {
    if (this.experiment.analysis.method == 'two_factors_one_value') {
      let number_of_desired_variables = 2;
      let nr = 0;
      for (let chVar of this.targetSystem.changeableVariables) {
        if (chVar["is_selected"] == true && !isNullOrUndefined(chVar["target"]))
          nr += 1;
        // check boundaries
        if (chVar.target < chVar.min || chVar.target > chVar.max) {
          this.errorButtonLabelChangeableVariables = "Provide valid value(s)";
          return true;
        }

      }
      if (nr < number_of_desired_variables || nr > number_of_desired_variables) {
        this.errorButtonLabelChangeableVariables = "Select and provide values for " + number_of_desired_variables + " different variables";
        return true;
      }
      return false;
    }
    else if (this.experiment.executionStrategy.type == 'sequential') {
      let nr = 0;

      for (let chVar of this.targetSystem.changeableVariables) {
        if (chVar["is_selected"] == true && isNullOrUndefined(chVar["target"])) {
          this.errorButtonLabelChangeableVariables = "Provide target value(s)";
          return true;
        }

        // check boundaries
        if (chVar.target < chVar.min || chVar.target > chVar.max) {
          this.errorButtonLabelChangeableVariables = "Provide valid value(s)";
          return true;
        }

        if (chVar["is_selected"] == true && !isNullOrUndefined(chVar["target"]))
          nr += 1;
      }
      if (nr == 0 && (this.experiment.analysis.type == 'one_sample_tests' || this.experiment.analysis.type == 'n_sample_tests') ) {
        this.errorButtonLabelChangeableVariables = "Select and provide value(s) for at least one variable";
        return true;
      }
      return false;
    }
  }

  // allows user to see changeable variables once necessary fields have been selected for analysis options
  public showVariables() {
    // general for all types of analysis, exec. str.
    if (isNullOrUndefined(this.experiment.executionStrategy.sample_size) || this.experiment.executionStrategy.sample_size < 0)
      return false;

    // general for all types of analysis
    if (isNullOrUndefined(this.experiment.analysis.alpha) || this.experiment.analysis.alpha <= 0 || this.experiment.analysis.alpha >= 1)
      return false;

    // general for all types of analysis
    if (isNullOrUndefined(this.experiment.analysis.data_type))
      return false;

    let analysis_type = this.experiment.analysis.type;
    if (analysis_type == 'two_sample_tests') {
      return !isNullOrUndefined(this.experiment.analysis.method)
    }
    // else if (analysis_type == 'factorial_tests' || analysis_type == 'n_sample_tests') {
    //   return !isNullOrUndefined(this.experiment.analysis.n) && this.experiment.analysis.n > 0
    // }
    else if (analysis_type == 'bayesian_opt') {
      return !isNullOrUndefined(this.experiment.analysis.method)
        && !isNullOrUndefined(this.experiment.executionStrategy.optimizer_iterations_in_design)
        && this.experiment.executionStrategy.optimizer_iterations_in_design > 0
        && !isNullOrUndefined(this.experiment.executionStrategy.optimizer_iterations)
        && this.experiment.executionStrategy.optimizer_iterations > 0
        && !isNullOrUndefined(this.experiment.executionStrategy.type)
        && !isNullOrUndefined(this.experiment.executionStrategy.acquisition_method)
        && !isNullOrUndefined(this.experiment.executionStrategy.sample_size)
        && this.experiment.executionStrategy.sample_size > 0
    }
    // nothing is needed in addition to alpha (for other types of tests)
    return true;
  }

  // simple proxy
  public get_keys(obj) {
    return this.entityService.get_keys(obj);
  }

  public analysisDataTypeChanged(data_type) {
    this.experiment.analysis.data_type = data_type;
  }

}
