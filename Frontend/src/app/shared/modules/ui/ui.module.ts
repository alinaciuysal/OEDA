import {NgModule} from "@angular/core";
import {DebugElementComponent} from "./debug-element.component";
import {LabeledInputComponent} from "./labeled-input-component";
import {CommonModule} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {LabeledInputSelectComponent} from "./labeled-input-select-component";
import {ExperimentDetailsComponent} from "./experiment-details.component";
import {ExperimentStagesComponent} from "./experiment-stages.component";

const uiElements = [
  DebugElementComponent,
  LabeledInputComponent,
  LabeledInputSelectComponent,
  ExperimentDetailsComponent,
  ExperimentStagesComponent
];

@NgModule({

  imports: [
    CommonModule,
    FormsModule,
  ],
  exports: uiElements,
  providers: [],
  declarations: uiElements
})
export class UIModule {
}
