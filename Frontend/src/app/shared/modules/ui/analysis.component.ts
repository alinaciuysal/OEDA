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

          <div class="col-md-3">
            <div class="sub-title">Analysis Method</div>
            <div>
              <input type="text" name="analysis_name" value="{{analysis_name}}" disabled><br>
            </div>
          </div>
        </div>
        
        <div class="panel-body" *ngIf="!analysis_is_collapsed">
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
                <td *ngFor="let k of get_keys(results[tuple])">
                  {{results[tuple][k]|| "&nbsp;" }}
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
  public properties: any;
  public inner_keys: any;
  public results: any; // keeps track of keys & values in incoming obj
  public analysis_name: string;

  constructor(private apiService: OEDAApiService, private notify: NotificationsService) {
    this.analysis_is_collapsed = true;
  }

  public btnClicked(): void {
    // first case with empty results
    if (this.analysis_is_collapsed && isNullOrUndefined(this.results)) {
      this.apiService.getAnalysis(this.experiment).subscribe(
        (result) => {
          let analysis = JSON.parse(result._body);
          console.log("incoming", analysis);
          this.analysis_name = analysis["name"];

          delete analysis['createdDate'];
          delete analysis['result'];

          // naming convention with backend server
          this.results = analysis["anova_result"]; // {C(x): {F: 0.2, PR(>F): 0.4} ... }
          console.log("results", this.results);
          this.properties = this.get_keys(this.results); // C(x), C(x):C(y), Residual
          console.log("properties", this.properties);

          // concatenate inner keys of tuples
          let allKeys = [];
          for (let property of this.properties) {
            let tuple = this.results[property];
            for (let key of this.get_keys(tuple)) {
              if (!allKeys.includes(key)) {
                allKeys.push(key);
              }
            }
          }
          this.inner_keys = allKeys;
          console.log("inner_keys", this.inner_keys);

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
