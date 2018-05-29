import {Component, Input, PipeTransform, Pipe} from "@angular/core";
import {isNullOrUndefined} from "util";
import {OEDAApiService} from "../api/oeda-api.service";
import {NotificationsService} from "angular2-notifications/dist";
import * as _ from "lodash.clonedeep";

@Component({
  selector: 'analysis',
  template: `
    <!-- Show/Hide Button & Additional Buttons for Running experiments -->
    <div class="col-md-12">
      <div class="panel panel-default chartJs">
        <div class="panel-heading">
          <button type="button" class="btn btn-success"
                  (click)="btnClicked()">
            <span *ngIf="analysis_is_collapsed">Show Analysis Details</span>
            <i *ngIf="analysis_is_collapsed" class="fa fa-angle-double-down" aria-hidden="true"></i>

            <span *ngIf="!analysis_is_collapsed">Hide Analysis Details</span>
            <i *ngIf="!analysis_is_collapsed" class="fa fa-angle-double-up" aria-hidden="true"></i>
          </button>
        </div>

        <div class="panel-body" *ngIf="!analysis_is_collapsed">
          <div class="col-md-3">
            <div class="sub-title">Analysis Type</div>
            <div>
              <input type="text" name="analysis_type" value="{{experiment.analysis.type}}" disabled><br>
            </div>
          </div>

          <div class="col-md-3" *ngIf="experiment.analysis.type == 'two_sample_tests'">
            <div class="sub-title">Analysis Method</div>
            <div>
              <input type="text" name="analysis_name" value="{{experiment.analysis.method}}" disabled><br>
            </div>
          </div>
        </div>
        
        <div class="panel-body" *ngIf="!analysis_is_collapsed && experiment.analysis.type != 'factorial_tests'">
          <div class="col-md-12">
            <div class="table-responsive">
              <table class="table table-striped table-bordered table-hover">
                <thead>
                    <th>Test Name</th>
                    <th *ngFor="let property of properties">
                      {{property}}
                    </th>
                </thead>
                <tbody>
                <!-- Multiple row multiple values -->
                <tr *ngFor="let analysis_name of get_keys(analysisResults)">
                  <td>
                    {{analysis_name}}  
                  </td>
                  <td *ngFor="let k of properties">
                    <span *ngIf="analysisResults[analysis_name]['result'][k] == null">&nbsp;</span>
                    <span *ngIf="analysisResults[analysis_name]['result'][k] != null">{{analysisResults[analysis_name]['result'][k]}}</span>
                  </td>
                </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="panel-body" *ngIf="!analysis_is_collapsed && experiment.analysis.type == 'factorial_tests'">
          <div class="col-md-12">
            <div class="table-responsive">
              
              <table class="table table-striped table-bordered table-hover">
                <thead>
                    <th>Attribute</th>
                    <th *ngFor="let key of inner_keys">{{key}}</th>
                </thead>
                
                <tbody>
                   <!-- Multiple row multiple values for anova -->
                  <tr *ngFor="let tuple of properties" style="width: 5%">
                    {{tuple}}
                    <td *ngFor="let k of get_keys(values[tuple])">
                      {{values[tuple][k]|| "&nbsp;" }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})

export class AnalysisComponent {
  @Input() targetSystem: any;
  @Input() experiment: any;

  public analysis_is_collapsed: boolean;
  public properties: any; // keeps track of keys in incoming obj
  public values: any; // keeps track of values in incoming obj
  public inner_keys: any;
  public analysisResults: any;

  constructor(private apiService: OEDAApiService, private notify: NotificationsService) {
    this.analysis_is_collapsed = true;
  }

  public btnClicked(): void {
    // first case with empty results
    if (this.analysis_is_collapsed && isNullOrUndefined(this.analysisResults)) {
      this.apiService.getAnalysis(this.experiment).subscribe(
        (result) => {
          let analysisResults = JSON.parse(result._body);
          for (let analysis_name in analysisResults) {
            if (analysisResults.hasOwnProperty(analysis_name)) {
              let analysisResult = analysisResults[analysis_name];
              // filter out unnecessary keys
              for (let property in analysisResult) {
                if (property == 'createdDate')
                  delete analysisResult[property];
                if (property == 'result' && this.experiment.analysis.type == 'factorial_tests') {
                  delete analysisResult[property];
                }
                else if (property == 'anova_result' && this.experiment.analysis.type != 'factorial_tests') {
                  delete analysisResult[property];
                }
              }
            }
          }
          this.analysisResults = analysisResults;

          if (this.experiment.analysis.type == 'factorial_tests') {
            this.analysisResults = this.analysisResults["two-way-anova"]; // naming convention with backend server
            this.values = this.analysisResults["anova_result"]; // {C(x): {F: 0.2, PR(>F): 0.4} ... }
            this.properties = this.get_keys(this.values); // C(x), C(x):C(y), Residual

            // concatenate inner keys of tuples of the result dict
            let allKeys = [];
            for (let property of this.properties) {
              let tuple = this.values[property];
              for (let key of this.get_keys(tuple)) {
                if (!allKeys.includes(key)) {
                  allKeys.push(key);
                }
              }
            }
            this.inner_keys = allKeys;
          }
          else {
            // create a concatenated tuple of attributes to support different outputs of different tests
            let allProperties = [];
            for (let analysis_name in this.analysisResults) {
              if (this.analysisResults.hasOwnProperty(analysis_name)) {
                let res = this.analysisResults[analysis_name]["result"];
                let analysisProperties = this.get_keys(res);
                for (let property of analysisProperties) {
                  if (!allProperties.includes(property)) {
                    allProperties.push(property);
                  }
                }
              }
            }
            this.properties = allProperties
          }
          this.notify.success("Success", "Analysis results are retrieved");
        }, error1 => {
          this.notify.error("Error", "Cannot retrieve analysis results");
        }
      )
    }
    this.analysis_is_collapsed = !this.analysis_is_collapsed;
  }

  public get_keys(object): Array<string> {
      if (!isNullOrUndefined(object)) {
      return Object.keys(object);
    }
    return null;
  }
}
