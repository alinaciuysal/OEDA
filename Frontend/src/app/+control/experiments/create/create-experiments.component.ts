import {OnInit, Component} from "@angular/core";
import {NotificationsService} from "angular2-notifications";
import {Router} from "@angular/router";
import {LayoutService} from "../../../shared/modules/helper/layout.service";
import {OEDAApiService, Experiment, Target, ExecutionStrategy} from "../../../shared/modules/api/oeda-api.service";
import * as _ from "lodash.clonedeep";
import {isNullOrUndefined} from "util";
import {TempStorageService} from "../../../shared/modules/helper/temp-storage-service";
import {EntityService} from "../../../shared/util/entity-service";
import {UtilService} from "../../../shared/modules/util/util.service";
import indexOf = require("core-js/library/fn/array/index-of");
import {hasOwnProperty} from "tslint/lib/utils";
import {isNumeric} from "rxjs/util/isNumeric";

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
  selectedTargetSystem: any;
  is_collapsed: boolean;
  errorButtonLabel: string;
  errorButtonLabelAnova: string;
  errorButtonLabelOptimization: string;
  errorButtonLabelTtest: string;
  defaultAlpha: number;
  defaultTTestEffectSize: number;
  maxNrOfImportantFactors: number;

  constructor(private layout: LayoutService, private api: OEDAApiService,
              private router: Router, private notify: NotificationsService,
              private temp_storage: TempStorageService, private entityService: EntityService, private utilService: UtilService) {
    this.availableTargetSystems = [];

    // create experiment, target system, and execution strategy
    this.executionStrategy = this.entityService.create_execution_strategy();
    this.targetSystem = this.entityService.create_target_system();
    this.experiment = this.entityService.create_experiment(this.executionStrategy);
    this.originalExperiment = _(this.experiment);
    this.defaultAlpha = 0.05; // default value to be added when an analysis is selected
    this.defaultTTestEffectSize = 0.7;
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

  public saveExperiment() {
    if (!this.hasErrors()) {
      // prepare other attributes
      this.experiment.executionStrategy.optimizer_iterations = Number(this.experiment.executionStrategy.optimizer_iterations);
      this.experiment.executionStrategy.sample_size = Number(this.experiment.executionStrategy.sample_size);
      this.experiment.analysis.sample_size = Number(this.experiment.analysis.sample_size);

      // take the incoming data type labeled as "is_considered" to perform stage result calculation in backend
      for (let item of this.targetSystem.incomingDataTypes) {
        if (item.is_considered === true) {
          this.experiment.considered_data_types.push(item);
        }
      }

      let knobs = {};
      for (let chVar of this.targetSystem.changeableVariables) {
        if (chVar.is_selected == true) {
          let knobArr = [];
          let factors = chVar.factorValues.split(",");
          for (let factor of factors) {
            knobArr.push(factor);
          }
          knobs[chVar.name] = knobArr;

        }
      }
      this.experiment.changeableVariables = knobs;
      this.experiment.executionStrategy.knobs = knobs; // also set executionStrategy knobs here
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

  public navigateToTargetSystemPage() {
    this.router.navigate(["control/targets/create"]).then(() => {
      console.log("navigated to target system creation page");
    });
  }

  public targetSystemChanged(targetSystemName: any) {
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
      // relate target system with experiment
      this.experiment.targetSystemId = this.targetSystem.id;

      // set default values
      this.experiment.analysis.type = "3_phase";
      this.experiment.analysis.sample_size = 15; // same with the one in entityService's ExecutionStrategy.sample_size
      this.experiment.analysis.n = this.targetSystem.changeableVariables.length; // set number of factor's default value
      this.experiment.analysis.nrOfImportantFactors = Math.round(Number(this.experiment.analysis.n / 3));
      this.experiment.analysis.anovaAlpha = this.defaultAlpha;
      this.experiment.analysis.tTestAlpha = this.defaultAlpha;
      this.experiment.analysis.tTestEffectSize = this.defaultTTestEffectSize;
      this.maxNrOfImportantFactors = Math.pow(2, this.targetSystem.changeableVariables.length);
      this.experiment.executionStrategy.type = "self_optimizer";
      this.acquisitionMethodChanged("gp_hedge");
      // set changeableVariable.min, changeableVariable.max as default value for factorValues for each chVar
      for (let chVar of this.targetSystem.changeableVariables) {
        chVar.factorValues = chVar.min + ", " + chVar.max;
        // also set is_selected flags of these variables
        chVar.is_selected = true;
      }

    } else {
      this.notify.error("Error", "Cannot fetch selected target system, please try again");
      return;
    }
  }

  // User can select execution strategy while creating an experiment
  public executionStrategyModelChanged(execution_strategy_key) {

    // refresh previously-selected variables of targetSystem & experiment
    this.experiment.changeableVariables = _(this.originalExperiment.changeableVariables);
    this.targetSystem.changeableVariables = _(this.originalTargetSystem.changeableVariables);

    this.experiment.executionStrategy.type = execution_strategy_key;
    if (execution_strategy_key === 'mlr_mbo') {
      this.acquisitionMethodChanged("ei");
    } else if (execution_strategy_key === 'self_optimizer') {
      this.acquisitionMethodChanged("gp_hedge");
    }
  }

  // User can select acquisition function for respective strategies
  public acquisitionMethodChanged(acquisition_method_key) {
    this.experiment.executionStrategy.acquisition_method = acquisition_method_key;
  }

  /**
   * sets is_selected flag of targetSystem.changeableVariables
   */
  public changeable_variable_checkbox_clicked(changeableVariable_index): void {
    let changeableVariable = this.targetSystem.changeableVariables[changeableVariable_index];
    if (isNullOrUndefined(changeableVariable.is_selected)) {
      changeableVariable.is_selected = true;
    }
    else if (changeableVariable.is_selected == true) {
      changeableVariable.is_selected = false;
      // also refresh factorValues
      changeableVariable.factorValues = null;
    }
    else if (changeableVariable.is_selected == false) {
      changeableVariable.is_selected = true;
    }
  }

  // called for every div that's bounded to *ngIf=!hasErrors() expression.
  public hasErrors(): boolean {
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

    // check data types for optimization
    for (let item of this.targetSystem.incomingDataTypes) {
      if (item.is_considered) {
        // check aggregate functions
        if (isNullOrUndefined(item["aggregateFunction"])) {
          this.errorButtonLabel = "Provide valid aggregate function(s)";
          return true;
        }
      }
    }

    if (this.entityService.get_number_of_considered_data_types(this.targetSystem) == 0) {
      this.errorButtonLabel = "Provide at least one incoming type to be optimized";
      return true;
    }

    // iterate min, max provided by the user and checks if they are within the range of default ones
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

    let nrOfSelectedVariables = 0;
    for (let i = 0; i < this.targetSystem.changeableVariables.length; i++) {
      if (this.targetSystem.changeableVariables[i].is_selected) {
        nrOfSelectedVariables += 1;
      }
    }
    if (nrOfSelectedVariables == 0) {
      this.errorButtonLabel = "Provide at least one changeable variable";
      return true;
    }

    // if there are errors in respective stages, propagate them to upper part of UI
    if (this.hasErrorsAnova()) {
      this.errorButtonLabel = this.errorButtonLabelAnova;
      return true;
    }

    if (this.hasErrorsOptimization()) {
      this.errorButtonLabel = this.errorButtonLabelOptimization;
      return true;
    }

    if (this.hasErrorsTtest()) {
      this.errorButtonLabel = this.errorButtonLabelTtest;
      return true;
    }
    return false;
  }

  public hasErrorsAnova() {

    // regular check
    if (isNullOrUndefined(this.experiment.analysis.anovaAlpha) || this.experiment.analysis.anovaAlpha <= 0 || this.experiment.analysis.anovaAlpha >= 1) {
      this.errorButtonLabelAnova = "Provide valid alpha for anova";
      return true;
    }

    if (isNullOrUndefined(this.experiment.analysis.sample_size) || this.experiment.analysis.sample_size <= 0 ) {
      this.errorButtonLabelAnova = "Provide valid sample size for anova";
      return true;
    }

    if (isNullOrUndefined(this.experiment.analysis.nrOfImportantFactors) || this.experiment.analysis.nrOfImportantFactors <= 0 ) {
      this.errorButtonLabelAnova = "Provide valid number of important factors";
      return true;
    }

    // n is used for number of factors in anova
    if (isNullOrUndefined(this.experiment.analysis.n) || this.experiment.analysis.n <= 0 ) {
      this.errorButtonLabelAnova = "Provide valid number of factors";
      return true;
    }

    let n = this.experiment.analysis.n;
    if (n > this.targetSystem.changeableVariables.length) {
      this.errorButtonLabelAnova = "Number of factors cannot exceed " + this.targetSystem.changeableVariables.length;
      return true;
    }
    if (n < 2) {
      this.errorButtonLabelAnova = "Factorial tests cannot be used with less than 2 factors";
      return true;
    }

    if (this.experiment.analysis.nrOfImportantFactors > this.maxNrOfImportantFactors) {
      this.errorButtonLabelAnova = "Number of important factors cannot exceed " + this.maxNrOfImportantFactors;
      return true;
    }

    // TODO: some corner cases:
    // TODO: 1) [0.3, 0.4; 0.5]
    // TODO: 2) [0.9, 0.3, 0.98] --> order is not checked
    // TODO: 3) [0, 0.6, 0.3, 0.6] --> duplicates are not checked
    // TODO: re-factor if-else statements
    // validate comma separated values of selected variables
    for (let chVar of this.targetSystem.changeableVariables) {
      if (chVar.is_selected) {
        if (hasOwnProperty(chVar, "factorValues")) {
          if (!isNullOrUndefined(chVar["factorValues"])) {
            let factors = chVar["factorValues"].split(",");
            if (factors.length != 0) {
              for (let factor of factors) {
                factor = factor.trim();
                if (!isNumeric(factor)){
                  this.errorButtonLabelAnova = "Provide numeric value(s) for factor values";
                  return true;
                }
                else {
                  // now check intervals
                  if (factor < chVar["min"] || factor > chVar["max"]) {
                    this.errorButtonLabelAnova = "Provide values within min & max values of changeable variable(s)";
                    return true;
                  }
                }
              }
            }
            else {
              this.errorButtonLabelAnova = "Provide valid value(s) for factor values";
              return true;
            }
          }
          else {
            this.errorButtonLabelAnova = "Provide valid value(s) for factor values";
            return true;
          }
        }
        else {
          this.errorButtonLabelAnova = "Provide valid value(s) for factor values";
          return true;
        }
      }
    }

    return false;
  }

  public hasErrorsOptimization() {

    let execution_strategy_type = this.experiment.executionStrategy.type;
    if (this.experiment.executionStrategy.optimizer_iterations === null || this.experiment.executionStrategy.optimizer_iterations <= 0
      || isNullOrUndefined(this.experiment.executionStrategy.acquisition_method) || isNullOrUndefined(execution_strategy_type)) {
      this.errorButtonLabelOptimization = "Provide valid inputs for " + execution_strategy_type;
      return true;
    }

    if (isNullOrUndefined(this.experiment.executionStrategy.sample_size) || this.experiment.executionStrategy.sample_size <= 0 ) {
      this.errorButtonLabelOptimization = "Provide valid sample size for optimization";
      return true;
    }

    // check if initial design of mlr mbo is large enough
    if (execution_strategy_type === "mlr_mbo") {
      let minimum_number_of_iterations = 0;
      for (let chVar of this.targetSystem.changeableVariables) {
        if (chVar.is_selected) {
          minimum_number_of_iterations += 4;
        }
      }
      if (this.experiment.executionStrategy.optimizer_iterations < minimum_number_of_iterations) {
        this.errorButtonLabelOptimization = "Number of optimizer iterations should be greater than " + minimum_number_of_iterations.toString() + " for " + execution_strategy_type;
        return true;
      }
    }
    else if (execution_strategy_type === "self_optimizer") {
      // check if number of iterations for skopt are enough
      let minimum_number_of_iterations = 5;
      if (this.experiment.executionStrategy.optimizer_iterations < minimum_number_of_iterations) {
        this.errorButtonLabelOptimization = "Number of optimizer iterations should be greater than " + minimum_number_of_iterations.toString() + " for " + execution_strategy_type;
        return true;
      }
    }

    return false;
  }

  public hasErrorsTtest() {

    // regular check
    if (isNullOrUndefined(this.experiment.analysis.tTestAlpha) || this.experiment.analysis.tTestAlpha <= 0 || this.experiment.analysis.tTestAlpha >= 1) {
      this.errorButtonLabelTtest = "Provide valid alpha for T-test";
      return true;
    }

    if (isNullOrUndefined(this.experiment.analysis.tTestEffectSize) || this.experiment.analysis.tTestEffectSize <= 0 || this.experiment.analysis.tTestEffectSize > 2) {
      this.errorButtonLabelTtest = "Provide valid effect size for T-test";
      return true;
    }
  }

  public incomingDataTypesChanged(incomingDataTypes) {
    this.targetSystem.incomingDataTypes = incomingDataTypes;
  }

  public hasChanges(): boolean {
    return JSON.stringify(this.experiment) !== JSON.stringify(this.originalExperiment);
  }
}
