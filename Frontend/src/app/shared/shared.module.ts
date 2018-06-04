import {NgModule, ModuleWithProviders, ErrorHandler, Injector} from "@angular/core";
import {FormsModule} from '@angular/forms';
import {HttpClient, HttpClientModule} from "@angular/common/http";
import {CommonModule} from "@angular/common";
import {AccordionModule} from "ngx-bootstrap/accordion";
import {ProgressbarModule} from "ngx-bootstrap/progressbar";
import {ModalModule} from "ngx-bootstrap/modal";
import {NotificationsService} from "angular2-notifications";
import {CustomErrorHandler} from "./util/custom-error-handler";
import {LoggerService} from "./modules/helper/logger.service";
import {TempStorageService} from "./modules/helper/temp-storage-service";
import {UserService} from "./modules/auth/user.service";
import {LayoutService} from "./modules/helper/layout.service";
import {UserRouteGuard} from "./modules/auth/user-routeguard.service";
import {UtilModule} from "./modules/util/util.module";
import {DataTableModule} from "angular2-datatable";
import {UIModule} from "./modules/ui/ui.module";
import {OEDAApiService} from "./modules/api/oeda-api.service";
import {PlotService} from "./util/plot-service";
import {EntityService} from "./util/entity-service";
import { JwtModule, JWT_OPTIONS } from '@auth0/angular-jwt';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule,
    AccordionModule,
    ProgressbarModule,
    ModalModule,
    UtilModule,
    DataTableModule,
    UIModule,
    JwtModule.forRoot({
      jwtOptionsProvider: {
        provide: JWT_OPTIONS,
        useFactory: jwtOptionsFactory,
        deps: [UserService]
      }
    })
  ],
  exports: [
    CommonModule,
    FormsModule,
    HttpClientModule,
    ModalModule,
    AccordionModule,
    UtilModule,
    ProgressbarModule,
    DataTableModule,
    UIModule
  ],
  providers: [
    UserService,
    LoggerService,
    TempStorageService,
    UserRouteGuard,
    LayoutService,
    PlotService,
    EntityService,
    OEDAApiService
    // should always be empty
  ]
})
export class SharedModule {

  /** defines the behaviour of angular2-jwt */
  // static authHttpServiceFactory(http: HttpInterceptor) {
  //   return new AuthHttp(new AuthConfig({
  //     tokenName: 'oeda_token',
  //     globalHeaders: [{'Content-Type': 'application/json'}],
  //   }), http)
  // }

  static forRoot(): ModuleWithProviders {
    return {
      ngModule: SharedModule,
      // Here (and only here!) are all global shared services
      providers: [
        // {
        //   provide: HttpClient,
        //   useFactory: HttpInterceptor.httpInterceptorFactory,
        //   deps: [Injector]
        // },
        {
          provide: JWT_OPTIONS,
          useFactory: jwtOptionsFactory,
          deps: [UserService],
        },
        {
          provide: ErrorHandler,
          useClass: CustomErrorHandler
        },
        LoggerService,
        UserService,
        LayoutService,
        UserRouteGuard,
        NotificationsService
      ]
    };
  }
}

export function jwtOptionsFactory(userService) {
  return {
    tokenGetter: () => {
      return userService.getAuthToken();
    }
  }
}
