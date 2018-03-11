import {Component, EventEmitter, Input, OnChanges, Output, SimpleChanges} from "@angular/core";

@Component({
  selector: 'experiment-details',
  template: `
    <div class="col-sm-12 col-xs-12">
      <div class="panel panel-default chartJs">
        <div class="panel-heading">
          <button type="button" class="btn btn-orange"
                  (click)="is_collapsed = !is_collapsed">
            <span *ngIf="is_collapsed">Show Experiment Details</span>
            <i *ngIf="is_collapsed" class="fa fa-angle-double-down" aria-hidden="true"></i>

            <span *ngIf="!is_collapsed">Hide Experiment Details</span>
            <i *ngIf="!is_collapsed" class="fa fa-angle-double-up" aria-hidden="true"></i>
          </button>
        </div>
        <div class="panel-body" [hidden]="is_collapsed">
          <div class="row">
            <labeled-input name="Experiment Name" [model]="experiment" key="name" [colSize]="6"
                           [disabled]="true"></labeled-input>
            <labeled-input name="Experiment Description" [model]="experiment" key="description" [colSize]="6"
                           [disabled]="true"></labeled-input>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Providers & Change Provider -->
    <div class="col-sm-12 col-xs-12" (ngModelChange)="onModelChange($event)" *ngIf="targetSystem.name !== ''"
         [hidden]="is_collapsed">

      <!-- Primary Data Provider & Secondary Data Provider(s)-->
      <div class="col-sm-6 col-xs-12" style="padding-left: 0">
        <div class="panel panel-default chartJs">
          <div class="panel-heading">
            <div class="card-title">
              <div class="title pull-left">Primary Data Provider</div>
            </div>
          </div>
          <div class="panel-body" style="padding-top: 20px">

            <div class="row" *ngIf="targetSystem.primaryDataProvider.type == 'http_request'">
              <div class="col-md-3">
                <div class="sub-title">Name</div>
                <span>{{targetSystem.primaryDataProvider.name}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">URL</div>
                <span>{{targetSystem.primaryDataProvider.url}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Port</div>
                <span>{{targetSystem.primaryDataProvider.port}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Serializer</div>
                <span>{{targetSystem.primaryDataProvider.serializer}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Ignore First N Samples</div>
                <span>{{targetSystem.primaryDataProvider.ignore_first_n_samples}}</span>
              </div>
            </div>

            <div class="row" *ngIf="targetSystem.primaryDataProvider.type == 'kafka_consumer'">
              <div class="col-md-3">
                <div class="sub-title">Name</div>
                <span>{{targetSystem.primaryDataProvider.name}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Kafka URI</div>
                <span>{{targetSystem.primaryDataProvider.kafka_uri}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Topic</div>
                <span>{{targetSystem.primaryDataProvider.topic}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Serializer</div>
                <span>{{targetSystem.primaryDataProvider.serializer}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Ignore First N Samples</div>
                <span>{{targetSystem.primaryDataProvider.ignore_first_n_samples}}</span>
              </div>
            </div>

            <div class="row" *ngIf="targetSystem.primaryDataProvider.type == 'mqtt_listener'">
              <div class="col-md-3">
                <div class="sub-title">Name</div>
                <span>{{targetSystem.primaryDataProvider.name}}</span>
              </div>
              <div class="col-md-3">
                <div class="sub-title">Host</div>
                <span>{{targetSystem.primaryDataProvider.host}}</span>
              </div>
              <div class="col-md-3">
                <div class="sub-title">Port</div>
                <span>{{targetSystem.primaryDataProvider.port}}</span>
              </div>
              <div class="col-md-3">
                <div class="sub-title">Topic</div>
                <span>{{targetSystem.primaryDataProvider.topic}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Serializer</div>
                <span>{{targetSystem.primaryDataProvider.serializer}}</span>
              </div>
              <div class="col-md-2">
                <div class="sub-title">Ignore First N Samples</div>
                <span>{{targetSystem.primaryDataProvider.ignore_first_n_samples}}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Secondary Data Provider(s) -->
        <div class="panel panel-default chartJs" *ngIf="targetSystem.secondaryDataProviders.length > 0">
          <div class="panel-heading">
            <div class="card-title">
              <div class="title pull-left" *ngIf="targetSystem.secondaryDataProviders.length > 1">Secondary Data
                Providers
              </div>
              <div class="title pull-left" *ngIf="targetSystem.secondaryDataProviders.length == 1">Secondary Data
                Provider
              </div>
            </div>
          </div>
          <div class="panel-body" style="padding-top: 20px">
            <div class="row" *ngFor="let secondaryDataProvider of targetSystem.secondaryDataProviders">
              <div *ngIf="secondaryDataProvider.type == 'http_request'">
                <div class="col-md-3">
                  <div class="sub-title">Name</div>
                  <span>{{secondaryDataProvider.name}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">URL</div>
                  <span>{{secondaryDataProvider.url}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Port</div>
                  <span>{{secondaryDataProvider.port}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Serializer</div>
                  <span>{{secondaryDataProvider.serializer}}</span>
                </div>
              </div>

              <div *ngIf="secondaryDataProvider.type == 'kafka_consumer'">
                <div class="col-md-3">
                  <div class="sub-title">Name</div>
                  <span>{{secondaryDataProvider.name}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Kafka URI</div>
                  <span>{{secondaryDataProvider.kafka_uri}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Topic</div>
                  <span>{{secondaryDataProvider.topic}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Serializer</div>
                  <span>{{secondaryDataProvider.serializer}}</span>
                </div>
              </div>

              <div *ngIf="secondaryDataProvider.type == 'mqtt_listener'">
                <div class="col-md-2">
                  <div class="sub-title">Name</div>
                  <span>{{secondaryDataProvider.name}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Host</div>
                  <span>{{secondaryDataProvider.host}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Port</div>
                  <span>{{secondaryDataProvider.port}}</span>
                </div>
                <div class="col-md-3">
                  <div class="sub-title">Topic</div>
                  <span>{{secondaryDataProvider.topic}}</span>
                </div>
                <div class="col-md-1">
                  <div class="sub-title">Serializer</div>
                  <span>{{secondaryDataProvider.serializer}}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Change Provider -->
      <div class="col-sm-6 col-xs-12" style="padding-right: 0">
        <div class="panel panel-default chartJs">
          <div class="panel-heading">
            <div class="card-title">
              <div class="title pull-left">Change Provider</div>
            </div>
          </div>
          <div class="panel-body" style="padding-top: 20px">

            <div class="row" *ngIf="targetSystem.changeProvider.type == 'http_request'">
              <div class="col-md-4">
                <div class="sub-title">URL</div>
                <span>{{targetSystem.changeProvider.url}}</span>
              </div>
              <div class="col-md-4">
                <div class="sub-title">Port</div>
                <span>{{targetSystem.changeProvider.port}}</span>
              </div>
              <div class="col-md-4">
                <div class="sub-title">Serializer</div>
                <span>{{targetSystem.changeProvider.serializer}}</span>
              </div>
            </div>

            <div class="row" *ngIf="targetSystem.changeProvider.type == 'kafka_producer'">
              <div class="col-md-4">
                <div class="sub-title">Kafka URI</div>
                <span>{{targetSystem.changeProvider.kafka_uri}}</span>
              </div>
              <div class="col-md-4">
                <div class="sub-title">Topic</div>
                <span>{{targetSystem.changeProvider.topic}}</span>
              </div>
              <div class="col-md-4">
                <div class="sub-title">Serializer</div>
                <span>{{targetSystem.changeProvider.serializer}}</span>
              </div>
            </div>

            <div class="row" *ngIf="targetSystem.changeProvider.type == 'mqtt_listener'">
              <div class="col-md-3">
                <div class="sub-title">Host</div>
                <span>{{targetSystem.changeProvider.host}}</span>
              </div>
              <div class="col-md-3">
                <div class="sub-title">Port</div>
                <span>{{targetSystem.changeProvider.port}}</span>
              </div>
              <div class="col-md-3">
                <div class="sub-title">Topic</div>
                <span>{{targetSystem.changeProvider.topic}}</span>
              </div>
              <div class="col-md-3">
                <div class="sub-title">Serializer</div>
                <span>{{targetSystem.changeProvider.serializer}}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Incoming Data Types, Execution strategy, Experiment Variables -->
    <div class="col-sm-12 col-xs-12" *ngIf="targetSystem.name !== ''" [hidden]="is_collapsed">
      <!-- Incoming Data Types -->
      <div class="col-sm-6 col-xs-12" style="padding-left: 0">
        <div class="panel panel-default chartJs">
          <div class="panel-heading">
            <div class="card-title">
              <div class="title pull-left">Incoming Data Types</div>
            </div>
          </div>
          <div class="panel-body" style="padding-top: 20px">
            <div class="table-responsive" style="padding-top: 20px">
              <table style="margin-top: 5px" class="table table-striped table-bordered table-hover">
                <thead>
                <th style="padding-left: 2%">Name</th>
                <th style="padding-left: 2%">Scale</th>
                <th style="padding-left: 2%">Description</th>
                <th style="padding-left: 2%">Data Provider Name</th>
                <th style="padding-left: 2%">Optimization Criteria</th>
                <th style="padding-left: 2%; padding-right: 2%">Consider</th>
                </thead>
                <tbody>
                <tr *ngFor="let dataType of targetSystem.incomingDataTypes" style="padding-top: 1%">
                  <td>{{dataType.name}}</td>
                  <td>{{dataType.scale}}</td>
                  <td>{{dataType.description}}</td>
                  <td>{{dataType.dataProviderName}}</td>
                  <td>{{dataType.criteria}}</td>
                  <td *ngIf="is_optimized(dataType.name)">Yes</td>
                  <td *ngIf="!is_optimized(dataType.name)">No</td>
                </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Execution Strategy & Experiment Variables -->
      <div class="col-sm-6 col-xs-12" style="padding-right: 0">
        <div class="panel panel-default chartJs">
          <div class="panel-heading">
            <div class="card-title">
              <div class="title pull-left">Execution Strategy</div>
            </div>
          </div>
          <div class="panel-body" style="padding-top: 20px">
            <div class="table-responsive" style="padding-top: 20px">
              <table>
                <thead>
                <th style="width: 5%">Type</th>
                <th style="width: 5%">Sample Size</th>
                <th style="width: 5%" *ngIf="experiment.executionStrategy.type == 'random' 
                  || experiment.executionStrategy.type == 'mlr_mbo' 
                  || experiment.executionStrategy.type == 'self_optimizer' 
                  || experiment.executionStrategy.type == 'uncorrelated_self_optimizer'">
                  Optimizer Iterations
                </th>
                <th style="width: 5%" *ngIf="experiment.executionStrategy.type == 'random' 
                  || experiment.executionStrategy.type == 'mlr_mbo' 
                  || experiment.executionStrategy.type == 'self_optimizer' 
                  || experiment.executionStrategy.type == 'uncorrelated_self_optimizer'">
                  Optimizer Iterations in Design
                </th>
                <th style="width: 5%" *ngIf="experiment.executionStrategy.type == 'self_optimizer'">Optimizer Method
                </th>
                </thead>
                <tbody>
                <td style="padding-top: 1%">{{experiment.executionStrategy.type}}</td>
                <td>{{experiment.executionStrategy.sample_size}}</td>
                <td *ngIf="experiment.executionStrategy.type == 'random'
                || experiment.executionStrategy.type == 'mlr_mbo'
                || experiment.executionStrategy.type == 'self_optimizer'
                || experiment.executionStrategy.type == 'uncorrelated_self_optimizer'">
                  {{experiment.executionStrategy.optimizer_iterations}}
                </td>
                <td *ngIf="experiment.executionStrategy.type == 'random' 
                  || experiment.executionStrategy.type == 'mlr_mbo' 
                  || experiment.executionStrategy.type == 'self_optimizer' 
                  || experiment.executionStrategy.type == 'uncorrelated_self_optimizer'">
                  {{experiment.executionStrategy.optimizer_iterations_in_design}}
                </td>
                <td *ngIf="experiment.executionStrategy.type == 'self_optimizer'">
                  {{experiment.executionStrategy.optimizer_method}}
                </td>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Experiment variables -->
        <div class="panel panel-default chartJs">
          <div class="panel-heading">
            <div class="card-title">
              <div class="title pull-left">Experiment Variables</div>
            </div>
          </div>
          <div class="panel-body" style="padding-top: 20px">
            <div class="table-responsive" style="padding-top: 20px">
              <table>
                <thead>
                <th style="width: 5%">Name</th>
                <th style="width: 5%">Min</th>
                <th style="width: 5%">Max</th>
                <th style="width: 5%">Default</th>
                <th *ngIf="experiment.executionStrategy.type == 'step_explorer'" style="width: 5%">Step Size</th>
                </thead>
                <tbody>
                <tr *ngFor="let input of experiment.changeableVariable" style="padding-top: 1%">
                  <td style="padding-top: 1%">{{input.name}}</td>
                  <td>{{input.min}}</td>
                  <td>{{input.max}}</td>
                  <td>{{input.default}}</td>
                  <td *ngIf="experiment.executionStrategy.type == 'step_explorer'">{{input.step}}</td>
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

export class ExperimentDetailsComponent implements OnChanges{
  @Output() modelChanged = new EventEmitter();
  @Input() targetSystem: any;
  @Input() experiment: any;
  @Input() is_collapsed: boolean;
  @Input() experiment_type: string;
  @Input() oedaCallback: any;

  @Input() onModelChange = (ev) => {
    this.modelChanged.emit(ev);
  };

  ngOnChanges(changes: SimpleChanges): void {
    this.modelChanged.emit(changes);
  }

  /** optimized_data_types are retrieved from experiment definition.
   * so, this function checks if given data type was selected for optimization or not
   */
  is_optimized(data_type_name) {
    for (let i = 0; i < this.experiment.optimized_data_types.length; i++) {
      if (this.experiment.optimized_data_types[i]["name"] === data_type_name) {
        return true;
      }
    }
    return false;
  }
}
