import {Component, Input} from "@angular/core";
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
            <div class="sub-title">Analysis Name</div>
            <div>
              <input type="text" name="analysis_name" value="{{analysis_name}}" disabled data-toggle="tooltip" title="Name of the Analysis performed after experimentation" ><br>
            </div>
          </div>

          <div class="col-md-3" *ngIf="experiment.analysis.type == 't_test'">
            <div class="sub-title">Analysis Method</div>
            <div>
              <input type="text" name="analysis_name" value="{{analysis_method}}" disabled data-toggle="tooltip" title="Method of the Analysis performed after experimentation" ><br>
            </div>
          </div>
        </div>
        
        <div class="panel-body" *ngIf="!analysis_is_collapsed">
          <div class="col-md-12">
            <div class="table-responsive">
              <table class="table table-striped table-bordered table-hover">
                <thead>
                <th *ngFor="let property of properties">{{property}}</th>
                </thead>
                <tbody>
                <!--Single row multiple values-->
                <tr>
                  <td *ngFor="let property of properties">{{values[property]}}</td>
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
  public analysis_name: string;
  public analysis_method: string;
  private originalAnalysisResult: any;

  constructor(private apiService: OEDAApiService, private notify: NotificationsService) {
    this.analysis_is_collapsed = true;
  }

  public btnClicked(): void {
    // first case with empty results
    if (this.analysis_is_collapsed && isNullOrUndefined(this.originalAnalysisResult)) {
      this.apiService.getAnalysis(this.experiment).subscribe(
        (result) => {
          let analysisResult = JSON.parse(result._body);
          this.originalAnalysisResult = _(analysisResult);
          this.analysis_name = analysisResult["name"];
          if(this.experiment.analysis.type == 't_test')
            this.analysis_method = this.experiment.analysis.method;
          // filter out unnecessary keys
          for(let property in analysisResult) {
            if (property == 'createdDate' || property == 'stage_ids')
              delete analysisResult[property];
            if (property == 'result' && this.experiment.analysis.type == 'anova') {
              delete analysisResult[property];
            }
            else if (property == 'anova_result' && this.experiment.analysis.type == 't_test') {
              delete analysisResult[property];
            }
          }


          if(this.experiment.analysis.type == 't_test') {
            this.properties = this.get_keys(analysisResult["result"]);
            this.values = analysisResult["result"];
          } else if(this.experiment.analysis.type == 'anova') {
            this.properties = this.get_keys(analysisResult["anova_result"]);
            this.values = analysisResult["result"];
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
