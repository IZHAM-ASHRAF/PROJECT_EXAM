import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  username: string = '';
  password: string = '';

  constructor(private readonly authService: AuthService, private router: Router) {}

  login() {
    this.authService.login(this.username, this.password).subscribe(() => {
      this.router.navigate(['/home']);
    });
  }
}
