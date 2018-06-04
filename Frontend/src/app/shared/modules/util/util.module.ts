import {NgModule} from "@angular/core";
import {HttpClientModule} from "@angular/common/http";
import {UtilService} from "./util.service";

@NgModule({
  imports: [
    HttpClientModule,
  ],
  exports: [
  ],
  providers: [
    UtilService
  ]
})
export class UtilModule {
}
