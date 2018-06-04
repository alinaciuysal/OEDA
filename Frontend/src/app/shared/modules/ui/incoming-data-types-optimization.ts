import {Component, Input} from "@angular/core";
import {isNullOrUndefined} from "util";
import {OEDAApiService} from "../api/oeda-api.service";
import {NotificationsService} from "angular2-notifications/dist";
import {EntityService} from "../../util/entity-service";

@Component({
  selector: 'incoming-data-types-optimization',
  template: `
    <div class="col-md-12" *ngIf="targetSystem.name !== ''">
      <div class="panel panel-default chartJs">
        <div class="panel-heading">
          <div class="card-title">
            <div class="title pull-left">Incoming Data Types</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="table-responsive">
            <table class="table table-striped table-bordered table-hover">
              <thead>
              <th>Name</th>
              <th>Scale</th>
              <th>Description</th>
              <th>Provider Name</th>
              <th>Provider Type</th>
              <th>Criteria</th>
              <th>Consider</th>
              <th *ngIf="is_data_type_selected()">Aggregation</th>
              <th *ngIf="is_data_type_selected()">Weight</th>
              </thead>
              <tbody>
              <tr *ngFor="let dataType of targetSystem.incomingDataTypes; let i = index">
                <td>{{dataType.name}}</td>
                <td>{{dataType.scale}}</td>
                <td>{{dataType.description}}</td>
                <td>{{dataType.dataProviderName}}</td>
                <td *ngIf="is_data_type_coming_from_primary(i)">Primary</td> <td *ngIf="!is_data_type_coming_from_primary(i)">Secondary</td>
                <td>{{dataType.criteria}}</td>
                <td *ngIf="is_data_type_coming_from_primary(i)">
                  <input type="checkbox" class="form-check-input"
                         (change)="data_type_checkbox_clicked(i)"
                         data-toggle="tooltip"
                         title="Select one incoming data type to be optimized. You cannot aggregate data coming from primary & secondary data providers at the same time">
                </td>
                <td *ngIf="dataType['is_considered'] && dataType.scale == 'Metric'">
                  <select [(ngModel)]="dataType['aggregateFunction']" required>
                    <option *ngFor="let fcn of aggregateFunctionsMetric" [ngValue]="fcn.key">{{fcn.label}}</option>
                  </select>
                </td>
                <td *ngIf="dataType['is_considered'] && dataType.scale == 'Boolean'">
                  <select [(ngModel)]="dataType['aggregateFunction']" required>
                    <option *ngFor="let fcn of aggregateFunctionsBoolean" [ngValue]="fcn.key">{{fcn.label}}</option>
                  </select>
                </td>
                <td *ngIf="dataType['is_considered']">
                  <input type="number" class="form-check-input"
                         data-toggle="tooltip"
                         title="Please provide weight of this data type within the final result"
                         [(ngModel)]="dataType['weight']"
                         [min]="1"
                         [max]="100"
                         required>
                  <span *ngIf="dataType['aggregateFunction'] !== 'percentiles'"><b>%</b></span>
                </td>
              </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `
})

export class IncomingDataTypesOptimizationComponent {
  @Input() targetSystem: any;
  @Input() experiment: any;

  public aggregateFunctionsMetric: any;
  public aggregateFunctionsBoolean: any;

  constructor(private apiService: OEDAApiService, private notify: NotificationsService, private entityService: EntityService) {
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

  public get_keys(object): Array<string> {
    if (!isNullOrUndefined(object)) {
      return Object.keys(object);
    }
    return null;
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

  /**
   * sets respective weights of data types when user clicks
   */
  public data_type_checkbox_clicked(data_type_index): void {
    let data_type = this.targetSystem.incomingDataTypes[data_type_index];

    if (!this.is_data_type_coming_from_primary(data_type_index) && !this.is_primary_dp_selected()) {

    }

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

  // check if user has selected a data coming from primary dp.
  public is_primary_dp_selected() {
    for (let data_type of this.targetSystem.primaryDataProvider.incomingDataTypes) {
      if (data_type["is_considered"] == true) {
        return true;
      }
    }
    return false;
  }
}
