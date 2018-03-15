import {Component, EventEmitter, Input, Output} from "@angular/core";
import {OedaCallbackEntity} from "../api/oeda-api.service";
import {isNullOrUndefined} from "util";

@Component({
  selector: 'experiment-stages-paginator',
  template: `
    <div class="col-md-12" [hidden]="hidden">
      <div class="panel panel-default chartJs">
        <div class="panel-heading">
          <div class="row">
            <div class="col-md-4">
              <div class="card-title">
                Incoming Data Type
                <select class="form-control" [(ngModel)]="incoming_data_type" (ngModelChange)="onIncomingDataTypeChange($event)">
                  <option *ngFor="let dataType of targetSystem.incomingDataTypes" [ngValue]="dataType">
                    {{dataType.name}}
                  </option>
                </select>
              </div>
            </div>
            
            <div class="col-md-4">
              <div class="card-title">
                Scale
                <select class="form-control" required [(ngModel)]="scale" (ngModelChange)="onScaleChange($event)">
                  <option selected>Normal</option>
                  <option>Log</option>
                </select>
              </div>
            </div>
          </div>
        </div>
        <div class="panel-body" style="padding-top: 20px; padding-left: 2%">
          <div class="table-responsive">
            <table style="margin-top: 20px" class="table table-bordered table-hover" [mfData]="available_stages" #mf="mfDataTable"
                   [mfRowsOnPage]="3">
              <thead>
              <tr>
                <th style="width:5%">
                  Stage
                </th>
                <!-- Default Knobs -->
                <th style="width: 3%" *ngFor="let knob of targetSystem.defaultVariables"> 
                  {{knob.name}}
                </th>
              </tr>
              </thead>
              <tbody class="bigTable">
                <tr *ngFor="let item of mf.data" (click)="onRowClick(item)" [class.active]="item.number == selected_row">
                  <td *ngIf="item.number === -1" data-toggle="tooltip" title="Default values of {{targetSystem.name}} are shown on this row">
                    All Stages 
                  </td>
                  <td *ngIf="item.number !== -1" data-toggle="tooltip" title="Click to draw plots">
                    {{item.number}}
                  </td>
                  <td *ngFor="let knob_key of get_keys(item.knobs)" data-toggle="tooltip" title="Click to draw plots">
                    {{item.knobs[knob_key]}}
                  </td>
                  
                </tr>
                </tbody>
                <tfoot *ngIf="available_stages.length > 3">
                <tr>
                  <td colspan="12">
                    <mfBootstrapPaginator [rowsOnPageSet]="[3,10,25,100]"></mfBootstrapPaginator>
                  </td>
                </tr>
                </tfoot>
              </table>
          </div>
        </div>
      </div>
    </div>
  `
})

export class ExperimentStagesPaginatorComponent {
  @Output() rowClicked: EventEmitter<any> = new EventEmitter<any>();
  @Output() scaleChanged: EventEmitter<any> = new EventEmitter<any>();
  @Output() incomingDataTypeChanged: EventEmitter<any> = new EventEmitter<any>();

  @Input() experiment: any;
  @Input() selected_stage: any;
  @Input() available_stages: any;
  @Input() targetSystem: any;
  @Input() incoming_data_type: object;
  @Input() scale: string;
  @Input() hidden: boolean;
  @Input() retrieved_data_length: number;
  @Input() for_successful_experiment: boolean;
  @Input() oedaCallback: OedaCallbackEntity;

  public selected_row: number = 0;

  @Input() onRowClick(stage) {
    this.selected_row = stage.number;
    this.rowClicked.emit(stage);
  }

  @Input() onScaleChange = (ev) => {
    this.scaleChanged.emit(ev);
  };

  @Input() onIncomingDataTypeChange = (ev) => {
    this.incomingDataTypeChanged.emit(ev);
  };

  /** returns keys of the given map */
  get_keys(object) : Array<string> {
    if (!isNullOrUndefined(object)) {
      return Object.keys(object);
    }
    return null;
  }
}
