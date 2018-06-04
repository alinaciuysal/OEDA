import {NotificationsService} from "angular2-notifications";
import {LoggerService} from "../modules/helper/logger.service";
import {HttpClient} from "@angular/common/http";
import {Injectable} from "@angular/core";
import {Try} from "monapt";
import {environment} from "../../../environments/environment";
import {Observable} from "rxjs/Observable";

@Injectable()
/** an abstract class that can be used to write REST compatible client APIs */
export class RESTService {

  constructor(public http: HttpClient,
              public notify: NotificationsService,
              public log: LoggerService) {
  }

  baseURL = environment.backendURL;
  configBackendURL = environment.configBackendURL;


  /** creates a string out of a given object - also replaces empty strings "" with null */
  private createCleanJSON(object: any): string {
    return JSON
      .stringify(object)
      .replace(/:""/gi, ":null")
  }

  // /** does a authed http get request to the given URL and returns type T */
  // public doGETRequest(url: string): Observable<any> {
  //   return this.http.get(this.baseURL + url)
  //     .map((res: Response) => res.json())
  //     .catch((error: any) => {
  //       // @todo add reroute if login failed
  //       this.notify.error("Server Error", "Action did not work");
  //       this.log.error("GET@" + url, error);
  //       return Observable(error || 'Server error')
  //     })
  // }
  //
  // /** does a authed http post request to the given URL with payload and returns type T */
  // public doPOSTRequest(url: string, object: any): Observable<any> {
  //   return this.http.post(this.baseURL + url, this.createCleanJSON(object))
  //     .map((res: Response) => Try(() => res.json()).getOrElse(() => {
  //     }))
  //     .catch((error: any) => {
  //       this.notify.error("Server Error", "Action did not work");
  //       error.object = object; // add post object to error
  //       this.log.error("POST@" + url, error);
  //       return Observable(error || 'Server error')
  //     })
  // }
  //
  // public doPUTRequest(url: string, object: any): Observable<any> {
  //   return this.http.put(this.baseURL + url, this.createCleanJSON(object))
  //     .catch((error: any) => {
  //       this.notify.error("Server Error", "Action did not work");
  //       error.object = object; // add post object to error
  //       this.log.error("PUT@" + url, error);
  //       return Observable(error || 'Server error')
  //     })
  // }


  /** does a public http get request to the given URL and returns type T */
  public doGETPublicRequest(url: string): Observable<any> {
    return this.http.get(this.baseURL + url)
  }

  /** does a public http get request to the given URL and returns type T */
  public doGETPublicRequestForConfig(url: string): Observable<any> {
    return this.http.get(this.configBackendURL + url)
  }

  // /** does a public http get request to the given host and port for checking if db is configured properly or not */
  // public doGETPublicRequestForDatabaseConfigValidity(host: string, port: string): Observable<any> {
  //   return this.http.get("http://" + host + ":" + port)
  //     .map((res: Response) => res.json())
  //     .catch((error: any) => {
  //       const errorMsg = JSON.parse(error._body);
  //       this.notify.error("Error", errorMsg.error || errorMsg.message);
  //       return Observable(error || 'Server error');
  //     })
  // }

  /** does a authed http post request to the given URL with payload and returns type T */
  public doPOSTPublicRequest(url: string, object: any): Observable<any> {
    return this.http.post(this.baseURL + url, this.createCleanJSON(object));
  }

  public doPUTPublicRequest(url: string, object: any): Observable<any> {
    return this.http.put(this.baseURL + url, this.createCleanJSON(object));
  }
}
