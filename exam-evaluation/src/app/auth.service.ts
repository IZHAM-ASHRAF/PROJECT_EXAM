import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  constructor(private http: HttpClient) {}

  login(username: string, password: string): Observable<any> {
    return this.http.post<any>('/api/login', { username, password });
  }

  register(username: string, password: string): Observable<any> {
    return this.http.post<any>('/api/register', { username, password });
  }

  getScore(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>('/api/get_score', formData);
  }
}
