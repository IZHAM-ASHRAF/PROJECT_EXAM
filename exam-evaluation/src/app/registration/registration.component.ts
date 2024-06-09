import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-registration',
  templateUrl: './registration.component.html',
  styleUrls: ['./registration.component.scss']
})
export class RegistrationComponent {
  username: string = '';
  password: string = '';

  constructor(private readonly authService: AuthService, private router: Router) {}

  register() {
    this.authService.register(this.username, this.password).subscribe(() => {
      this.router.navigate(['/login']);
    });
  }
}
