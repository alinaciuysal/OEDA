// import {Injectable, Injector} from "@angular/core";
// import {Router} from "@angular/router";
// import {Observable} from "rxjs";
// import {HttpClient, HttpRequest, HttpResponse, HttpHeaders} from '@angular/common/http';
//
// @Injectable()
// export class HttpInterceptor{
//
//   // static httpInterceptorFactory(injector: Injector) {
//   //   return new HttpInterceptor(xhrBackend, requestOptions, injector)
//   // }
//
//   _router: any = null;
//
//   constructor( private injector: Injector) {
//     setTimeout(() => this._router = injector.get(Router))
//   }
//
//   request(url: string | Request, options?: RequestOptionsArgs): Observable<Response> {
//     return this.intercept(super.request(url, options));
//   }
//
//   get(url: string, options?: RequestOptionsArgs): Observable<Response> {
//     return this.intercept(super.get(url, options));
//   }
//
//   post(url: string, body: string, options?: RequestOptionsArgs): Observable<Response> {
//     return this.intercept(super.post(url, body, this.getRequestOptionArgs(options)));
//   }
//
//   put(url: string, body: string, options?: RequestOptionsArgs): Observable<Response> {
//     return this.intercept(super.put(url, body, this.getRequestOptionArgs(options)));
//   }
//
//   delete(url: string, options?: RequestOptionsArgs): Observable<Response> {
//     return this.intercept(super.delete(url, options));
//   }
//
//   getRequestOptionArgs(options?: RequestOptionsArgs): RequestOptionsArgs {
//     if (options == null) {
//       options = new RequestOptions();
//     }
//     if (options.headers == null) {
//       options.headers = new Headers();
//     }
//     options.headers.append('Content-Type', 'application/json');
//     return options;
//   }
//
//   intercept(observable: Observable<Response>): Observable<Response> {
//     return observable.catch((err, source) => {
//       if (err.status == 401) {
//         setTimeout(
//           () => this._router.navigate(['/auth/login'], {
//             queryParams: {returnUrl: this._router.currentRouterState.snapshot.url}
//           })
//         )
//         ;
//         return Observable.empty();
//       }
//       return Observable.throw(err);
//     });
//   }
// }
