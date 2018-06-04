import {Injectable} from '@angular/core';
import {Observable} from "rxjs/Observable";
import {HttpClient, HttpHeaders, HttpResponse} from "@angular/common/http";
import {LoggerService} from "../helper/logger.service";
import {Router} from "@angular/router";
import {Try, Option, None, Some} from "monapt";
import {environment} from "../../../../environments/environment";
import {NotificationsService} from "angular2-notifications/dist";
import { JwtHelperService } from '@auth0/angular-jwt';
import { of } from 'rxjs/observable/of'; // for static methods

@Injectable()
export class UserService {

  constructor(private http: HttpClient, private router: Router, private log: LoggerService, private notify: NotificationsService,
              public jwtHelper: JwtHelperService) {
  }

  /** store the URL so we can redirect after logging in */
  redirectUrl: string;

  /** true if the user is logged in */
  isLoggedIn(): boolean {
    return this.getAuthTokenRaw().map(token => {
        return Try(() => !this.jwtHelper.isTokenExpired(token)).getOrElse(() => false)
      }
    ).getOrElse(() => false)
  }

  /** true if db is configured properly */
  is_db_configured(): any {
    const user_token_value = this.getAuthToken()["value"].user.db_configuration;
    return user_token_value.hasOwnProperty("host") &&
      user_token_value.hasOwnProperty("port") &&
      user_token_value.hasOwnProperty("type");

  }

  tryTokenRenewal(): Observable<Object> {
    if (this.getAuthTokenRaw().isEmpty) {
      return of("user not logged in");
      // return new Observable("not logged in")
    }
    const authHeader = new HttpHeaders();
    authHeader.set('Authorization', 'Bearer ' + this.getAuthTokenRaw().get());
    return this.http.post(environment.backendURL + "/auth/renew", {},
      {headers: authHeader})
      .map(
        data => {
          this.log.debug("tryTokenRenewal successful");
          this.setAuthToken(data['body'].token);
          return true;
        }
      ).catch((error: any) => {
        let errorMsg: any = {};
        // server is not running
        if (typeof(error['_body']) == 'object') {
          errorMsg.message = "Server is not running";
        } else {
          // server is running and returned a json string
          errorMsg = JSON.parse(error['_body']);
        }
        this.notify.error("Error", errorMsg.error || errorMsg.message);
        return new Observable(error || 'Server error');
      });
  }

  handleError() {
    console.log("error occurred in userService");
  }

  userIsInGroup(groupName: string): boolean {
    return this.getAuthToken()
      .map(token => token.roles.indexOf(groupName) > -1)
      .getOrElse(() => false)
  }

  sessionExpiresDate(): Date {
    return this.getAuthTokenRaw().map(token => this.jwtHelper.getTokenExpirationDate(token))
      .getOrElse(() => new Date())
  }

  /** tries to log in the user and stores the token in localStorage (another option is to store it in sessionStorage) */
  login(request: LoginRequest): Observable<Object> {
    this.log.debug("UserService - starting LoginRequest");
    return this.http.post(environment.backendURL + "/auth/login", request)
      .map(res => {
        this.log.debug("UserService - request successful");
        this.setAuthToken(res['body'].token);
        return true;
      })
      .catch((error: any) => {
        let errorMsg: any = {};
        // server is not running
        if (typeof(error['_body']) == 'object') {
          errorMsg.message = "Server is not running";
        } else {
          // server is running and returned a json string
          errorMsg = JSON.parse(error['_body']);
        }
        this.notify.error("Error", errorMsg.error || errorMsg.message);
        return new Observable(error || 'Server error');
      })
  }

  /** returns the parsed token as JWTToken*/
  getAuthToken(): Option<JWTToken> {
    return this.getAuthTokenRaw().map(token => this.jwtHelper.decodeToken(token) as JWTToken)
  }

  /** stores the token*/
  setAuthToken(token: string): void {
    this.log.debug("UserService - storing token");
    localStorage.setItem('oeda_token', token)
  }

  /** returns the token stored in localStorage */
  getAuthTokenRaw(): Option<string> {
    const token = localStorage.getItem('oeda_token');
    if (token == null || token.split('.').length !== 3) {
      return None
    } else {
      return new Some(token)
    }
  }

  /** logs out the user */
  logout(): void {
    console.log("UserService - removing token");
    this.log.debug("UserService - removing token");
    localStorage.removeItem('oeda_token');
    console.log(localStorage.getItem('oeda_token'));
    this.router.navigate(['/'])
  }

  /** checks if a user has a given permission */
  hasPermission(permission: Permission): boolean {
    return true
  }

  forcePermission(permission: Permission): Promise<boolean> { // Permission
    if (!this.isLoggedIn()) {
      this.log.warn("UserService - user is not logged in - sending to login");
      return this.router.navigate(['/auth/login'])
    }
    // check if the token has the given permission allowed
    const permissionNumber = this.getAuthToken().map(f => f.permissions).getOrElse(() => 0);
    const toLessPermissions = (permissionNumber === 0);
    if (toLessPermissions) {
      this.log.warn("UserService - not enough access rights for this page");
      return this.router.navigate(['/'])
    }
    this.log.debug("UserService - user has all permissions for this page");
  }
}


/** a permission in the system */
export class Permission {

  /** allows access to the system status page */
  static FOUND_SYSINFO_READ = new Permission(0, "FOUND_SYSINFO_READ");

  constructor(index: number, name: string) {
    this.index = index;
    this.name = name;
  }

  index: number;
  name: string;
}

/** request for logging in */
export interface LoginRequest {
  username: string,
  password: string
}

/** the format of tokens we use for auth*/
export interface JWTToken {
  id: string,
  value: string,
  roles: string[],
  representsArtists: string[],
  monitorsArtists: string[],
  permissions: number,
  exp: number,
  nbf: number
}
